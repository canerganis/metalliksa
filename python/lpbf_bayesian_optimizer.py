#!/usr/bin/env python3
from __future__ import annotations
import math, time
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from scipy.optimize import minimize
from scipy.stats import norm as scipy_norm

_DEFAULT_BOUNDS = dict(
    laserPower_W=(100.0,500.0),
    scanSpeed_mms=(200.0,2000.0),
    hatch_um=(60.0,200.0),
    layer_um=(20.0,80.0),
)
_PARAM_KEYS = list(_DEFAULT_BOUNDS)

def _norm(x, bounds): return (x-bounds[:,0])/(bounds[:,1]-bounds[:,0]+1e-15)
def _denorm(X, bounds): return X*(bounds[:,1]-bounds[:,0])+bounds[:,0]

class GaussianProcessSurrogate:
    def __init__(self, n_dims, noise_sigma=1e-3):
        self.n_dims=n_dims; self.noise_sigma=noise_sigma
        self._log_theta=np.zeros(1+n_dims)
        self.X_train=self.y_train=self._L=self._alpha=None
        self._y_mean=0.0; self._y_std=1.0

    def _kernel(self, X1, X2, lt):
        sf=math.exp(lt[0]); ls=np.exp(lt[1:])
        d=(X1[:,None,:]-X2[None,:,:])/ls
        return sf**2*np.exp(-0.5*np.sum(d**2,axis=-1))

    def _lml(self, lt):
        if self.X_train is None: return 0.0
        K=self._kernel(self.X_train,self.X_train,lt)
        K+=(self.noise_sigma**2+1e-8)*np.eye(len(self.X_train))
        try: L=np.linalg.cholesky(K)
        except np.linalg.LinAlgError: return -1e10
        a=np.linalg.solve(L.T,np.linalg.solve(L,self.y_train))
        return float(-0.5*self.y_train@a-np.sum(np.log(np.diag(L)))-0.5*len(self.y_train)*math.log(2*math.pi))

    def fit(self, X, y):
        self.X_train=X.copy()
        self._y_mean,self._y_std=float(y.mean()),float(y.std()+1e-10)
        self.y_train=(y-self._y_mean)/self._y_std
        res=minimize(lambda lt:-self._lml(lt),self._log_theta,method='L-BFGS-B',
                     bounds=[(-3,3)]*(1+self.n_dims),options={'maxiter':50})
        self._log_theta=res.x
        K=self._kernel(self.X_train,self.X_train,self._log_theta)
        K+=(self.noise_sigma**2+1e-8)*np.eye(len(self.X_train))
        self._L=np.linalg.cholesky(K)
        self._alpha=np.linalg.solve(self._L.T,np.linalg.solve(self._L,self.y_train))
        return self

    def predict(self, X_star):
        if self.X_train is None:
            return np.zeros(len(X_star))*self._y_std+self._y_mean, np.ones(len(X_star))*self._y_std
        Ks=self._kernel(X_star,self.X_train,self._log_theta)
        mu_n=Ks@self._alpha
        v=np.linalg.solve(self._L,Ks.T)
        Kss=np.diag(self._kernel(X_star,X_star,self._log_theta))
        var_n=np.maximum(Kss-np.sum(v**2,axis=0),0.0)
        return mu_n*self._y_std+self._y_mean, np.sqrt(var_n)*self._y_std

def expected_improvement(Xc, gp, best, xi=0.01):
    mu,sigma=gp.predict(Xc)
    sigma=np.maximum(sigma,1e-10)
    z=(mu-best-xi)/sigma
    ei=sigma*(z*scipy_norm.cdf(z)+scipy_norm.pdf(z))
    ei[sigma<1e-10]=0.0
    return ei

class BayesianProcessOptimizer:
    def __init__(self, alloy_id, objective_fn, param_bounds=None, n_warmup=5, seed=42):
        self.alloy_id=alloy_id; self.objective_fn=objective_fn; self.n_warmup=n_warmup
        self.rng=np.random.default_rng(seed)
        merged={**_DEFAULT_BOUNDS, **(param_bounds or {})}
        self.bounds=np.array([merged[k] for k in _PARAM_KEYS])
        self.gp=GaussianProcessSurrogate(n_dims=4)
        self._X_obs=[];self._y_obs=[];self._history=[];self._n=0

    def _pack(self, p): return _norm(np.array([p[k] for k in _PARAM_KEYS]),self.bounds)
    def _unpack(self, x): return {k:float(v) for k,v in zip(_PARAM_KEYS,_denorm(x,self.bounds))}

    def suggest_next(self):
        if len(self._X_obs)<self.n_warmup: return self._unpack(self.rng.random(4))
        X,y=np.array(self._X_obs),np.array(self._y_obs)
        self.gp.fit(X,y); best=float(np.max(y))
        Xc=self.rng.random((6000,4))
        ei=expected_improvement(Xc,self.gp,best)
        x0=Xc[int(np.argmax(ei))]
        res=minimize(lambda x:-float(np.asarray(expected_improvement(x[None,:],self.gp,best)).ravel()[0]),
                     x0,method='L-BFGS-B',bounds=[(0,1)]*4,options={'maxiter':30})
        return self._unpack(np.clip(res.x,0.0,1.0))

    def observe(self, params, score):
        self._X_obs.append(self._pack(params)); self._y_obs.append(score); self._n+=1
        self._history.append({'iteration':self._n,'params':{k:round(params[k],2) for k in _PARAM_KEYS},'score':round(score,4)})

    def best_params(self):
        if not self._y_obs: return None
        return self._history[int(np.argmax(self._y_obs))]

    @property
    def history(self): return list(self._history)

MAX_ITERATIONS = 30
DEFAULT_BEAM_DIAMETER_UM = 80.0
DEFAULT_PREHEAT_TEMP_C = 80.0


def _refuse(kind, message):
    return {'success': False, 'errorKind': kind, 'error': message}


OBJECTIVE_DESCRIPTION = (
    'verdict score (printable 1, risky 0.5, do-not-print 0, inconclusive/geometry-unresolved 0) '
    'x normalised v*h (v*h / (v_max*h_max))'
)


KEYHOLE_GATE_NOTE = (
    'The keyhole gate is the served regime classifier of the frozen thermal solver (python/lpbf_thermal_solver.py, '
    'keyhole mode at normalised enthalpy dH/h_s >= 20, 13.6 for Inconel 625): keyhole mode scores risky (0.5) and '
    'never do-not-print since P7a (2026-10-11); the former porosity level 30 is an advisory (unsourced screening '
    'threshold) and the do-not-print edge 35 is removed. The cut is not relaxed or re-derived here; the regime threshold '
    'moved to 20 in the keyhole-regime bump. Keyhole mode is a mode onset, not a porosity boundary.'
)


def _iteration_diagnostics(vd, th):
    """Per-candidate gate diagnostics: which gates drove the verdict and the raw screening numbers."""
    th = th if isinstance(th, dict) else {}
    pp = th.get('processParameters') or {}
    geo = th.get('meltPoolGeometry') or {}
    dd = th.get('defectDiagnostics') or {}
    kh = dd.get('keyholePorosityRisk')
    bs = dd.get('ballingScreen') if isinstance(dd.get('ballingScreen'), dict) else {}
    return {
        'blockingGates': list(vd.get('blockingGates') or []),
        'riskGates': list(vd.get('riskGates') or []),
        'advisoryGates': list(vd.get('advisoryGates') or []),
        'reasons': list(vd.get('reasons') or []),
        'extentStatus': geo.get('extentStatus', vd.get('extentStatus')),
        'normalizedEnthalpy': pp.get('normalizedEnthalpy'),
        'aspectRatio_L_over_W': geo.get('aspectRatio_L_over_W'),
        # P7a: keyholeHigh is the legacy level-30 advisory flag (never a verdict input); the verdict reads the regime.
        'keyholeRisk': kh,
        'keyholeHigh': None if kh is None else str(kh).startswith('High'),
        'keyholeMode': str(geo.get('regime') or '').startswith('Keyhole Mode') if geo.get('regime') is not None else None,
        # Balling screen (Eagar-Tsai L/W): 'high' (316L only since P7a) and 'moderate' are advisories (scored as
        # the verdict, i.e. not penalised), None -> Eagar-Tsai extent not computed.
        'ballingBand': bs.get('band'),
        'ballingLengthToWidthEagarTsai': bs.get('lengthToWidth'),
    }


def _gate_summary(iters):
    """Counts of the gates that held candidates back (fail -> do-not-print, unresolved extent -> inconclusive)."""
    blocking, risk, advisory, inconclusive = {}, {}, {}, {}
    for it in iters:
        d = it.get('diagnostics') or {}
        for g in d.get('blockingGates') or []:
            blocking[g] = blocking.get(g, 0) + 1
        for g in d.get('riskGates') or []:
            risk[g] = risk.get(g, 0) + 1
        for g in d.get('advisoryGates') or []:
            advisory[g] = advisory.get(g, 0) + 1
        if it.get('verdict') == 'inconclusive':
            k = str(d.get('extentStatus') or 'not-reported')
            inconclusive[k] = inconclusive.get(k, 0) + 1
    order = lambda m: dict(sorted(m.items(), key=lambda kv: (-kv[1], kv[0])))
    return {'blockingGateCounts': order(blocking), 'riskGateCounts': order(risk),
            'advisoryGateCounts': order(advisory),
            'inconclusiveExtentStatusCounts': order(inconclusive)}


class _SolverError(Exception):
    """Wraps a thermal-solver/verdict exception so it is reported as errorKind 'solver'."""


def _as_int(value, name):
    """Strict integer: booleans, non-integral floats and non-numbers are rejected, never truncated."""
    if isinstance(value, bool):
        raise ValueError(f'{name} must be an integer, not a boolean.')
    if isinstance(value, int):
        return value
    if isinstance(value, float) and math.isfinite(value) and value == int(value):
        return int(value)
    raise ValueError(f'{name} must be an integer (got {value!r}); it is not truncated.')


def _as_number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f'{name} must be a number (got {value!r}).')
    return float(value)


def run_bayesian_optimization(alloy_id, param_bounds=None, n_iter=20, n_warmup=5, seed=42,
                              beam_diameter_um=DEFAULT_BEAM_DIAMETER_UM,
                              preheat_temp_C=DEFAULT_PREHEAT_TEMP_C):
    """Expected-improvement search over (P, v, h, t).

    Objective (unchanged): verdict score (compose_verdict -> _verdict_score: printable 1, risky 0.5,
    do-not-print 0, inconclusive/geometry-unresolved 0) multiplied by the normalised volumetric-rate proxy
    v*h/(v_max*h_max). Unknown alloys, invalid inputs and solver errors are returned as explicit failures
    (errorKind 'validation', 'solver' or 'optimizer'); nothing is silently substituted or coerced.
    """
    from four_alloy_materials import resolve_alloy_id, thermal_props
    from lpbf_thermal_solver import calculate_meltpool_physics
    from lpbf_build_job_solver import compose_verdict
    from lpbf_screening_uq import _verdict_score as verdict_score
    if alloy_id is None or str(alloy_id).strip() == '':
        return _refuse('validation', 'alloyId is required; no default alloy is assumed.')
    resolved = resolve_alloy_id(alloy_id)
    if resolved is None:
        return _refuse('validation', f"Unknown alloy '{alloy_id}': not resolvable by four_alloy_materials; no fallback alloy is used.")
    try:
        n_iter = _as_int(n_iter, 'nIterations'); n_warmup = _as_int(n_warmup, 'nWarmup')
        seed = _as_int(seed, 'seed')
        beam = _as_number(beam_diameter_um, 'beamDiameter_um'); preheat = _as_number(preheat_temp_C, 'preheatTemp_C')
    except ValueError as e:
        return _refuse('validation', str(e))
    if not (1 <= n_iter <= MAX_ITERATIONS):
        return _refuse('validation', f'nIterations must be between 1 and {MAX_ITERATIONS} (got {n_iter}); it is not silently clamped.')
    if n_warmup < 1:
        return _refuse('validation', 'nWarmup must be at least 1.')
    if not (math.isfinite(beam) and beam > 0):
        return _refuse('validation', 'beamDiameter_um must be a positive finite number.')
    solidus = float(thermal_props(resolved)['solidus_C'])
    if not (math.isfinite(preheat) and 0 <= preheat < solidus):
        return _refuse('validation', f'preheatTemp_C must be finite, >= 0 and below the {resolved} solidus ({solidus:g} C).')
    if param_bounds is not None and not isinstance(param_bounds, dict):
        return _refuse('validation', 'paramBounds must be an object keyed by parameter name.')
    unknown = sorted(set(param_bounds or {}) - set(_PARAM_KEYS))
    if unknown:
        return _refuse('validation', f'Unknown paramBounds keys {unknown}; allowed: {_PARAM_KEYS}.')
    merged = {**_DEFAULT_BOUNDS, **(param_bounds or {})}
    try:
        for k in _PARAM_KEYS:
            lo, hi = _as_number(merged[k][0], k), _as_number(merged[k][1], k)
            if not (math.isfinite(lo) and math.isfinite(hi) and 0 < lo < hi):
                raise ValueError(k)
            merged[k] = (lo, hi)
    except (TypeError, ValueError, KeyError, IndexError) as e:
        return _refuse('validation', f'Invalid bounds for {e}: each needs finite 0 < min < max.')
    v_max, h_max = merged['scanSpeed_mms'][1], merged['hatch_um'][1]

    def _obj(params):
        try:
            th = calculate_meltpool_physics(
                material_name=resolved,
                laser_power_W=float(params['laserPower_W']),
                scan_speed_mm_s=float(params['scanSpeed_mms']),
                beam_diameter_um=beam,
                preheat_temp_C=preheat,
                layer_thickness_um=float(params['layer_um']),
                hatch_spacing_um=float(params['hatch_um']),
                laser_wavelength='IR_1064nm')
            vd = compose_verdict(th, resolved)
        except Exception as e:
            raise _SolverError(str(e)) from e
        vs = verdict_score(vd['verdict'])
        prod = (float(params['scanSpeed_mms']) * float(params['hatch_um'])) / (v_max * h_max)
        return float(vs) * float(prod), vd['verdict'], _iteration_diagnostics(vd, th)

    opt = BayesianProcessOptimizer(resolved, None, param_bounds=merged, n_warmup=n_warmup, seed=seed)
    t0 = time.time(); iters = []
    try:
        for i in range(n_iter):
            sug = opt.suggest_next(); sc, verd, diag = _obj(sug); opt.observe(sug, sc)
            iters.append({'iteration': i + 1, 'params': {k: round(sug[k], 2) for k in _PARAM_KEYS},
                          'score': round(sc, 4), 'verdict': verd, 'diagnostics': diag})
    except _SolverError as e:
        cause = e.__cause__
        return _refuse('solver', f'Thermal solver failed at iteration {len(iters) + 1}: {type(cause).__name__}: {cause}')
    except Exception as e:
        return _refuse('optimizer', f'Surrogate/acquisition step failed at iteration {len(iters) + 1}: {type(e).__name__}: {e}')
    elapsed = round((time.time() - t0) * 1000.0, 1)
    best_idx = max(range(len(iters)), key=lambda j: iters[j]['score'])
    best_score = iters[best_idx]['score']
    counts = {}
    for it in iters:
        counts[it['verdict']] = counts.get(it['verdict'], 0) + 1
    no_positive = best_score <= 0
    recent = [it['score'] for it in iters[-5:]]
    converged = len(recent) >= 5 and (max(recent) - min(recent)) < 1e-3
    return {'success': True, 'alloyId': resolved,
            'bestParams': None if no_positive else iters[best_idx]['params'],
            'bestVerdict': None if no_positive else iters[best_idx]['verdict'],
            'noPositiveScore': no_positive,
            'bestScore': best_score,
            'verdictCounts': counts, 'nInconclusive': counts.get('inconclusive', 0),
            'iterations': iters, 'converged': converged, 'elapsedMs': elapsed, 'nIterations': n_iter,
            'nWarmup': n_warmup, 'surrogateSteps': max(0, n_iter - n_warmup),
            'beamDiameter_um': beam, 'preheatTemp_C': preheat,
            'objective': OBJECTIVE_DESCRIPTION,
            'gateSummary': _gate_summary(iters), 'keyholeGateNote': KEYHOLE_GATE_NOTE}


def optimize_process_window(alloy_id, bounds=None, param_bounds=None, n_iterations=20, n_iter=None, n_initial=5,
                            n_warmup=None, seed=42, beam_diameter_um=DEFAULT_BEAM_DIAMETER_UM,
                            preheat_temp_C=DEFAULT_PREHEAT_TEMP_C):
    """Convenience alias supporting both naming conventions; alloy_id is required (no default alloy)."""
    b = bounds if bounds is not None else param_bounds
    ni = n_iter if n_iter is not None else n_iterations
    nw = n_warmup if n_warmup is not None else n_initial
    return run_bayesian_optimization(alloy_id=alloy_id, param_bounds=b, n_iter=ni, n_warmup=nw, seed=seed,
                                     beam_diameter_um=beam_diameter_um, preheat_temp_C=preheat_temp_C)


def main():
    import json, sys
    raw = sys.stdin.read().strip()
    if not raw:
        print(json.dumps({'error': 'Empty payload.'}))
        sys.exit(1)
    try:
        data = json.loads(raw)
    except Exception as e:
        print(json.dumps({'error': f'Invalid JSON: {e}'}))
        sys.exit(1)
    # Solver imports (e.g. NVIDIA Warp) print banners to stdout; keep stdout for the one JSON document only.
    import contextlib
    with contextlib.redirect_stdout(sys.stderr):
        result = _run_from_payload(data)
    print(json.dumps(result, allow_nan=False))


def _run_from_payload(data):
    return run_bayesian_optimization(
        alloy_id=data.get('alloyId'),
        param_bounds=data.get('paramBounds'),
        n_iter=data.get('nIterations', 20),
        n_warmup=data.get('nWarmup', 5),
        seed=data.get('seed', 42),
        beam_diameter_um=data.get('beamDiameter_um', DEFAULT_BEAM_DIAMETER_UM),
        preheat_temp_C=data.get('preheatTemp_C', DEFAULT_PREHEAT_TEMP_C),
    )


if __name__ == '__main__':
    main()
