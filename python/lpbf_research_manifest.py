"""P8 phase C manifests and source records, ported from the Amendment 4 sketches.
No fixture, branch blob or target data is read at runtime. Research only.
"""
from __future__ import annotations
import copy
import math
from collections import OrderedDict
import four_alloy_materials as registry
import lpbf_research_codes as codes

# Contract 13.3 and 13.15, including the Revision 4 provenance split.
FIXTURE_TO_RUNTIME = dict(zip(
    ('cavity P v d T0 Tl K cp rho alpha A Tv Lv M kl cpl rhol slope mu deltaT L Lm Tref '
     'onsetMethod accommodation recoil lineFraction meltDepthRefinementRelative peakTemperatureProxy_K '
     'recoilPressure_Pa energyResidualRelative R fieldShapeShare atOnsetGaussianDepth_um '
     'aboveOnsetPointLimitDepth_um fieldShapeStep_um independentPointLimitDepth_um '
     'pointLimitIndependentDifference_m').split(),
    ('keyholeCavity power_W speed_m_s beamDiameter_m preheat_K liquidus_K conductivity_W_mK '
     'specificHeat_J_kgK density_kg_m3 diffusivity_m2_s wallAbsorptanceProxy vapourTemperature_K '
     'vapourLatentHeat_J_kg vapourMolarMass_kg_mol liquidConductivity_W_mK liquidSpecificHeat_J_kgK '
     'liquidDensity_kg_m3 surfaceTensionSlope_N_mK viscosity_Pa_s deltaTemperature_K length_m '
     'latentHeatFusion_J_kg referenceTemperature_K onsetEvent evaporationAccommodation recoilFraction '
     'cavityPowerFraction relativeConvergenceDifference beamCenterBalanceTemperature_K '
     'beamCenterRecoilPressure_Pa relativeFluxResidual aspectRatio_e_over_d fieldShapeShareOfExcess '
     'gaussianDepthAtOnset_um pointDepthAtOnset_um pointMinusGaussian_um pointDepthIndependentCheck_um '
     'pointDepthIndependentDifference_m').split()))
INPUT_NAMES = dict((k, FIXTURE_TO_RUNTIME.get(k, k)) for k in
                   'P v d T0 Tl K cp rho alpha A Tv Lv M kl cpl rhol slope mu deltaT L Lm Tref onsetMethod accommodation effectiveNetFactor recoil emissivity'.split())
OPTION_TO_INPUT = {v: k for k, v in INPUT_NAMES.items()}
OPTION_TO_INPUT.update(evaporationConvention='evaporationConvention', netEvaporationFactor='effectiveNetFactor',
                       slopeMode='slopeMode', solubleSulfur_ppm='solubleSulfur_ppm', solubleOxygen_ppm='solubleOxygen_ppm')
PROVENANCE_KEYS = tuple('kind label sourceId sourceLocator declarationLocator source scope status sourceEvidenceKind defaultValue defaultKind followsInput followState dependsOn phase referenceTemperature_K sourceRange_K'.split())
DERIVATION_KEYS = ('weakestInputs', 'derivationInputs', 'sourceLawProvenance')
KIND_LABELS = dict(sourceDefault='sourced default', sourceModelAssumption='source model assumption',
                   sourcedAlternative='sourced alternative', alloyTransfer='transferred',
                   modelConvention='alternative convention', declaredAssumption='declared assumption (no source)',
                   legacyEstimate='legacy estimate (no located source)', userInput='user input',
                   followsInput='follows', derived='derived')


def map_fixture_values(value, module=None):
    if isinstance(value, dict):
        return {FIXTURE_TO_RUNTIME.get(k, k): map_fixture_values(v, module) for k, v in value.items()}
    if isinstance(value, list):
        return [map_fixture_values(v, module) for v in value]
    return value


def map_field_shape_step(record):
    names = ('onsetPower_W', 'relativeBracket', 'atOnsetGaussianDepth_um', 'aboveOnsetPointLimitDepth_um',
             'fieldShapeStep_um', 'pointToGaussianRatio', 'independentPointLimitDepth_um',
             'pointLimitIndependentDifference_m', 'aboveOnsetFieldChanged', 'cause')
    result = {FIXTURE_TO_RUNTIME.get(k, k): record[k] for k in names}
    result['onsetSideRecords'] = [dict(side=r['side'], powerFactor=r['powerFactor'],
                                     values=map_fixture_values(r['values'])) for r in record['records']]
    result['linkedDepthJustBelowOnset_um'] = record['records'][0]['values']['linkedMeltDepth_um']
    result['linkedDepthJustAboveOnset_um'] = record['records'][2]['values']['linkedMeltDepth_um']
    return result


def input_entry(record):
    """Rev. 4: reject unknown keys, including inside the two nonrecursive records."""
    unknown = set(record) - set(PROVENANCE_KEYS) - set(DERIVATION_KEYS)
    if unknown:
        raise ValueError('unknown input provenance keys: ' + repr(sorted(unknown)))
    base = {k: copy.deepcopy(record[k]) for k in PROVENANCE_KEYS}
    base['label'] = KIND_LABELS[base['kind']]
    base['dependsOn'] = [INPUT_NAMES.get(k, k) for k in base['dependsOn']]
    derivation = {k: copy.deepcopy(record.get(k, [] if k == 'weakestInputs' else None)) for k in DERIVATION_KEYS}
    derivation['weakestInputs'] = [INPUT_NAMES.get(k, k) for k in derivation['weakestInputs']]
    if derivation['derivationInputs']:
        for row in derivation['derivationInputs'].values():
            if set(row['provenance']) != set(PROVENANCE_KEYS):
                raise ValueError('nested provenance must have exactly 17 keys')
            row['provenance'] = input_entry(row['provenance'])['provenance']
    if derivation['sourceLawProvenance']:
        nested = derivation['sourceLawProvenance']
        if set(nested) != set(PROVENANCE_KEYS):
            raise ValueError('source law must have exactly 17 keys')
        derivation['sourceLawProvenance'] = input_entry(nested)['provenance']
    return dict(provenance=base, derivation=derivation if any(derivation.values()) else None)


CONTROL_LIMITS = {
    'surfaceTensionSlope_N_mK': (-.003, .003), 'length_m': (1e-6, .01),
    'deltaTemperature_K': (0., 10000.), 'referenceTemperature_K': (300., 10000.),
    'viscosity_Pa_s': (1e-5, .1), 'solubleSulfur_ppm': (0., 1000.), 'solubleOxygen_ppm': (0., 1000.),
    'vapourTemperature_K': (1000., 6000.), 'vapourLatentHeat_J_kg': (1e5, 3e7),
    'vapourMolarMass_kg_mol': (.001, .2), 'evaporationAccommodation': (0., 1.),
    'netEvaporationFactor': (0., 1.), 'recoilFraction': (0., 1.), 'emissivity': (0., 1.),
}
PRESETS = {'gan-ti64': ('ti6al4v', (3560., 9.255e6, .048)),
           'pure-al-proxy': ('alsi10mg', (2743., 284000/.0269815384, .0269815384)),
           'o8-mg-inclusive': ('alsi10mg', (2477.605213217703, 6823019.62479557, .024889589126757754)),
           'melt-in625-raoult': ('in625', (3001., 6479525.6, .0559725))}


def nominal_state(context):
    """Read the shared property authority; never copy common alloy constants."""
    p = context.property_dict(); c = context.conduction; aid = context.alloyId
    ti = aid == 'ti6al4v'; al = aid == 'alsi10mg'
    tl = c.liquidus_K
    return dict(P=context.power_W, v=context.speed_m_s, d=context.beamDiameter_m, T0=context.preheat_K,
                Tl=tl, K=c.conductivity_W_mK, cp=c.specificHeat_J_kgK, rho=c.density_kg_m3,
                alpha=c.diffusivity_m2_s, A=c.wallAbsorptance,
                Tv=3560. if ti else 2743. if al else None,
                Lv=9.255e6 if ti else 284000/.0269815384 if al else None,
                M=.048 if ti else .0269815384 if al else None,
                kl=p.get('thermal_conductivity_liquid_W_mK'), cpl=p.get('specific_heat_liquid_J_kgK'),
                rhol=p.get('density_liquid_kg_m3'), slope=-.00019 if ti else p.get('d_gamma_dT_N_mK'),
                mu=.005 if ti else 10**(-.8022+658.34/(tl+250))*1e-3 if al else None,
                deltaT=500., L=context.beamDiameter_m, Lm=p.get('latent_heat_fusion_J_kg'),
                onsetMethod='dwell', accommodation=1., effectiveNetFactor=.8, recoil=.6,
                emissivity=.3 if ti else .35)


def _user_record(key, value, default):
    result = _record('userInput', 'p8:user:' + key, scope='Explicit research coefficient; source range not established')
    result.update(defaultValue=default.get(key), followState='user-fixed')
    return result


def apply_options(state, provenance, module, options, *, arm_id='nominal'):
    """Options are local; sourced alternatives retain their explicitly named changes."""
    out = copy.deepcopy(state); records = copy.deepcopy(provenance)
    local = options.get(module, {})
    if module == 'surfaceBalance':
        preset = local.get('vapourPreset')
        if preset == 'custom':
            for key in ('Tv', 'Lv', 'M'):
                out[key] = None
                records[key] = _user_record(key, None, state)
        elif preset in PRESETS and not arm_id.startswith('vapour_'):
            for key, value in zip(('Tv', 'Lv', 'M'), PRESETS[preset][1]):
                out[key] = value
            if preset == 'o8-mg-inclusive':
                located = input_provenance('alsi10mg', 'vapour_o8', out, state)
                for key in ('Tv', 'Lv', 'M'): records[key] = located[key]
            elif preset == 'melt-in625-raoult':
                for key in ('Tv', 'Lv', 'M'):
                    records[key] = _record('derived', 'melt:in625:raoult:' + key,
                        SPEC + ' A3', scope='Explicit all-CC/table-weighted IN625 alternative', phase='vapour')
    for key, value in local.items():
        target = OPTION_TO_INPUT.get(key)
        if target is None or key in ('slopeMode', 'evaporationConvention'):
            continue
        # Named source arms override their family while other custom controls persist.
        if arm_id.startswith('vapour_') and target in ('Tv', 'Lv', 'M'):
            continue
        if (arm_id.startswith('slope_') and target == 'slope' or
            arm_id == 'slope_viscosity_gan' and target == 'mu' or
            arm_id.startswith('viscosity_') and target == 'mu' or
            arm_id.startswith('deltaT_') and target == 'deltaT' or
            arm_id.startswith('length_') and target == 'L' or
            arm_id.startswith('accommodation_') and target == 'effectiveNetFactor'):
            continue
        out[target] = value
        if (value is None or state.get(target) is None or float(value).hex() != float(state[target]).hex()
                or records.get(target,{}).get('sourceEvidenceKind')=='Unresolved'):
            records[target] = _user_record(target, value, state)
    if module == 'marangoni':
        out['Tref'] = local.get('referenceTemperature_K', out.get('Tl') + out['deltaT']/2 if out.get('Tl') is not None else None)
        if 'referenceTemperature_K' not in local:
            records['Tref'] = _assumption('Tref', 'Diagnostic reference follows liquidus and assumed contrast')
            records['Tref'].update(kind='followsInput', followsInput='deltaTemperature_K',
                                    followState='following', defaultKind='declaredAssumption', dependsOn=['Tl', 'deltaT'])
        if 'viscosity_Pa_s' not in local and out['Tref'] is not None:
            if records.get('mu', {}).get('kind') == 'followsInput':
                aid = records['mu']['sourceId']
                if 'alsi10mg' in aid:
                    out['mu'] = 10**(-.8022+658.34/out['Tref'])*1e-3
                    records['mu']['sourceEvidenceKind'], records['mu']['weakestInputs'] = evidence_kind(records, ('Tl', 'deltaT'))
                elif 'in718' in aid:
                    out['mu'] = .196*math.exp(5848/out['Tref'])*1e-3
        mode = local.get('slopeMode', 'direct')
        if mode != 'direct':
            solute = 'solubleSulfur_ppm' if mode == 'fe-s-belton' else 'solubleOxygen_ppm'
            out[solute]=local.get(solute)
            records.setdefault(solute,_user_record(solute,out[solute],state))
            from lpbf_research_arm import belton_slope
            out['slope'] = None if local.get(solute) is None or out['Tref'] is None else belton_slope(mode, local[solute], out['Tref'])
            records['slope'] = _user_record('slope', out['slope'], state)
            records['slope'].update(kind='derived', dependsOn=[solute, 'Tref'], sourceLocator=SPEC + ' A2 / B8')
            records['slope']['sourceEvidenceKind'], records['slope']['weakestInputs'] = evidence_kind(records,(solute,'Tref'))
    return out, records


def _exact_input(value):
    return float(value).hex() if type(value) in (int, float) else value


def target_reference(scenario_id, cavity_arms):
    for row in cavity_arms:
        if scenario_id == row['armId'] or scenario_id in row['descriptor']['aliasArmIds']:
            return row['armId'], False
    return cavity_arms[0]['armId'], True


def build_manifest(module, context, options, declared_rows=None):
    aid = context.alloyId; s = nominal_state(context)
    secondary_aliases = {}
    if module in ('alSi10MgIndexDisclosure','unavailablePhysics','alSi10MgVapourMgAware'):
        candidates = [('nominal', s, input_provenance(aid or context.material, 'nominal', s, s))]
    elif aid in ('ti6al4v', 'alsi10mg'):
        candidates = []
        for name, state in arms(registry, aid, s):
            local_m = name.startswith(('slope_', 'viscosity_', 'deltaT_', 'length_'))
            local_s = name.startswith('accommodation_')
            if module in ('keyholeCavity', 'meltDepthLink') and (local_m or local_s): continue
            if module == 'surfaceBalance' and (local_m or name.startswith('onset_')): continue
            if module == 'marangoni' and local_s: continue
            if module == 'marangoni' and options.get(module, {}).get('slopeMode', 'direct') != 'direct' and name.startswith('slope_'): continue
            candidates.append((name, state, input_provenance(aid, name, state, s)))
    elif aid in ('in625', 'in718', 'ss316l') and module in ('marangoni', 'surfaceBalance'):
        rows = secondary_manifests(registry)[aid][module]['manifest']
        candidates = []
        for row in rows:
            secondary_aliases[row['armId']] = list(row['aliasArmIds'])
            state = copy.deepcopy(row['inputs'])
            # Secondary source-only missing tuples stay missing, with request processes applied.
            state.update(P=context.power_W*(.95 if row['armId']=='power_0.95' else 1.05 if row['armId']=='power_1.05' else 1.),
                         v=context.speed_m_s, d=context.beamDiameter_m*(.95 if row['armId']=='beam_0.95' else 1.05 if row['armId']=='beam_1.05' else 1.), T0=context.preheat_K)
            if row['armId'].startswith('beam_'):state['L']=state['d']
            elif row['armId'].startswith('length_'):state['L']=context.beamDiameter_m*float(row['armId'][7:])
            else:state['L']=context.beamDiameter_m
            candidates.append((row['armId'], state, copy.deepcopy(row['inputProvenance'])))
        s = candidates[0][1]
    else:
        candidates = [('nominal', s, input_provenance(aid or context.material, 'nominal', s, s))]
    if declared_rows is not None:
        candidates = declared_rows
    # User endpoints follow declared order and preserve the full local nominal.
    if module in ('marangoni', 'surfaceBalance'):
        baseline, baseprov = apply_options(candidates[0][1], candidates[0][2], module, options)
        for key in sorted(options.get('ranges', {}).get(module, {})):
            if key == 'surfaceTensionSlope_N_mK' and options.get(module, {}).get('slopeMode', 'direct') != 'direct':continue
            for end, name in (('min', 'low'), ('max', 'high')):
                endpoint = options['ranges'][module][key][end]
                target = OPTION_TO_INPUT[key]
                row = copy.deepcopy(baseline); row[target] = endpoint
                prov = copy.deepcopy(baseprov); prov[target] = _user_record(target, endpoint, baseline)
                if target == 'deltaT' and 'referenceTemperature_K' not in options[module]:
                    row['Tref'] = row['Tl'] + endpoint/2 if row['Tl'] is not None else None
                if target in ('deltaT', 'Tref') and 'viscosity_Pa_s' not in options[module] and aid == 'alsi10mg' and row['Tref'] is not None:
                    row['mu'] = 10**(-.8022+658.34/row['Tref'])*1e-3
                if target in ('deltaT','Tref') and 'viscosity_Pa_s' not in options[module] and aid=='in718' and row['Tref'] is not None:
                    row['mu']=.196*math.exp(5848/row['Tref'])*1e-3
                mode=options[module].get('slopeMode','direct')
                if module=='marangoni' and mode!='direct':
                    from lpbf_research_arm import belton_slope
                    solute='solubleSulfur_ppm' if mode=='fe-s-belton' else 'solubleOxygen_ppm'
                    if row.get(solute) is not None and row.get('Tref') is not None:
                        row['slope']=belton_slope(mode,row[solute],row['Tref'])
                        prov['slope']['sourceEvidenceKind'],prov['slope']['weakestInputs']=evidence_kind(prov,(solute,'Tref'))
                candidates.append((f'user:{module}:{key}:{name}', row, prov))
    active = (tuple(s) if module in ('keyholeCavity', 'meltDepthLink') else ACTIVE_INPUTS.get(module, tuple(s)))
    if module in ('keyholeCavity', 'meltDepthLink'):
        active = tuple(k for k in s if k not in ('kl','cpl','rhol','slope','mu','deltaT','L','accommodation','effectiveNetFactor','recoil','emissivity'))
        # Lm and cpl do not enter onset or cavity except the separate O2 diagnostic.
        active = tuple(k for k in active if k != 'Lm')
    if module == 'marangoni' and 'Tref' not in s and not options.get(module) and not options.get('ranges',{}).get(module):
        active=tuple(k for k in active if k != 'Tref')
    if module=='marangoni' and options.get(module,{}).get('slopeMode','direct')!='direct':
        active=tuple(active)+('solubleSulfur_ppm' if options[module]['slopeMode']=='fe-s-belton' else 'solubleOxygen_ppm',)
    retained = []; seen = {}
    local_nominal = None
    for name, state, prov in candidates:
        raw = copy.deepcopy(prov)
        if module in ('marangoni','surfaceBalance') and not name.startswith('user:'):
            state, prov = apply_options(state, prov, module, options, arm_id=name)
        if name == 'nominal': local_nominal = copy.deepcopy(state)
        # Default fixture tuples remain exact (Tref is an implicit followed value there).
        if module == 'marangoni' and aid in ('ti6al4v','alsi10mg') and not options.get(module) and not options.get('ranges',{}).get(module):
            state.pop('Tref', None); prov.pop('Tref', None)
        inputs = tuple((INPUT_NAMES.get(k,k), _exact_input(state.get(k)), prov[k]['sourceId']) for k in active)
        if module in ('marangoni','surfaceBalance'):
            local=options.get(module,{})
            conventions=({ 'slopeMode':local.get('slopeMode','direct')} if module=='marangoni' else
                         {'evaporationConvention':'net-factor' if name.startswith('accommodation_') else local.get('evaporationConvention','accommodation-and-beta'),
                          'vapourPreset':local.get('vapourPreset','gan-ti64' if aid=='ti6al4v' else 'pure-al-proxy' if aid=='alsi10mg' else 'custom')})
            inputs += (('@conventions',codes.canonical_json(conventions),'p8:conventions'),)
        if inputs in seen:
            retained[seen[inputs]]['descriptor']['aliasArmIds'].append(name)
            continue
        changes = [k for k in state if state[k] != local_nominal.get(k)]
        rank = lambda k: (0 if prov[k]['sourceEvidenceKind']=='Unresolved' else 1 if prov[k]['sourceEvidenceKind']=='User input' else
                           2 if prov[k]['kind']=='alloyTransfer' or prov[k]['kind']=='derived' and prov[k]['status']=='extrapolated' else
                           3 if prov[k]['kind'] in ('sourcedAlternative','modelConvention','derived') else 4)
        weakest = min(changes,key=rank) if changes else None
        summary = prov[weakest] if weakest else arm_provenance(aid or context.material, name)
        summary = {k: summary[k] for k in PROVENANCE_KEYS}
        label = name.replace('_',' ') + ': ' + KIND_LABELS[summary['kind']] + (f' (+{len(changes)-1} more)' if len(changes)>1 else '')
        family = ('user-endpoint' if name.startswith('user:') else 'nominal' if name=='nominal' else
                  'absorptance' if name.startswith('absorptance') else 'onset-criterion' if name.startswith('onset_') else
                  'vapour-source' if name.startswith('vapour_') else 'process' if name.startswith(('power_','beam_')) else
                  'flow-assumption' if name.startswith(('length_','deltaT_','accommodation_')) else 'property-tuple')
        descriptor = dict(armId=name,family=family,label=label,onsetEvent=state.get('onsetMethod'),armProvenance=input_entry(summary)['provenance'],
                          changes=[dict(input=INPUT_NAMES.get(k,k),value=state[k],nominalAnchor=local_nominal.get(k), **input_entry(prov[k])) for k in changes],aliasArmIds=secondary_aliases.get(name,[]))
        seen[inputs] = len(retained)
        retained.append(dict(armId=name, inputs=inputs, descriptor=descriptor, state=state,
                             provenance=prov, rawProvenance=raw, dependsOn=[]))
    if module in ('meltDepthLink','marangoni','surfaceBalance') and aid in ('ti6al4v','alsi10mg'):
        cavity = build_manifest('keyholeCavity', context, options)['arms']
        for row in retained:
            target, fallback = target_reference(row['armId'], cavity)
            row['reference'] = dict(requestedArmId=row['armId'], comparedArmId=target, fallback=fallback)
            # A comparison may match a cavity tuple under another retained id.
            match = next((c for c in cavity if comparison_tuple(c['state']) == comparison_tuple(row['state'])), None)
            row['comparisonArmId'] = match['armId'] if match else None
            row['dependsOn'] = [['keyholeCavity', target]]
            if match and match['armId'] != target:row['dependsOn'].append(['keyholeCavity',match['armId']])
    return dict(banded=module not in ('alSi10MgIndexDisclosure','unavailablePhysics'),
                declared=aid in ('ti6al4v','alsi10mg') or aid in ('in625','in718','ss316l') and module in ('marangoni','surfaceBalance'),arms=retained)


def comparison_tuple(state):
    return tuple(_exact_input(state.get(k)) for k in ('P','v','d','T0','K','cp','rho','alpha','A','Tv','Lv','M','onsetMethod'))
SPEC = "docs/research/SPEC_p8_research_arm_2026-10-14.md"
LEDGER = "835466fa:python/four_alloy_materials.py"
O8 = "docs/research/scripts/alsi10mg_vapour_o8.py"
KINDS = {"sourceDefault", "sourceModelAssumption", "alloyTransfer",
         "sourcedAlternative", "modelConvention", "declaredAssumption",
         "legacyEstimate", "userInput", "followsInput", "derived"}
PHYSICAL_INPUTS = {
    "cavity": ("K", "cp", "rho", "A", "Tl", "Tv", "Lv", "M"),
    "meltDepthLink": ("K", "cp", "rho", "A", "Tl", "Tv", "Lv", "M"),
    "marangoni": ("kl", "cpl", "rhol", "slope", "mu", "L", "deltaT"),
    "surfaceBalance": ("K", "cp", "rho", "A", "Tv", "Lv", "M",
                       "accommodation", "effectiveNetFactor", "recoil", "emissivity"),
}
# Exact active tuples for local dedup; cavity references are a separate ledger.
ACTIVE_INPUTS = {
    "marangoni": ("kl", "cpl", "rhol", "slope", "mu", "L", "deltaT", "Tref"),
    "surfaceBalance": ("P", "v", "d", "T0", "K", "cp", "rho", "alpha", "A",
                       "Tv", "Lv", "M", "accommodation", "effectiveNetFactor", "recoil", "emissivity"),
}


def _record(kind, source_id, locator=None, *, source=None, phase=None,
            reference=None, source_range=None, evidence=None, scope="",
            follows=None, dependencies=(), status="extrapolated"):
    if evidence is None:
        evidence = ("Unresolved" if kind in {"declaredAssumption", "legacyEstimate"}
                    else "User input" if kind == "userInput" else "Literature estimate")
    return dict(kind=kind, label=kind, sourceId=source_id, source=source,
                sourceLocator=locator, declarationLocator=None, phase=phase,
                referenceTemperature_K=reference, sourceRange_K=source_range,
                sourceEvidenceKind=evidence, scope=scope, status=status,
                defaultValue=None, defaultKind=None, followsInput=follows,
                followState="following" if follows else None,
                dependsOn=list(dependencies))


def _assumption(key, scope, phase=None, reference=None):
    record = _record("declaredAssumption", "p8:assumption:" + key,
                     phase=phase, reference=reference,
                     source=None, scope=scope)
    record["declarationLocator"] = SPEC + " Amendment 2 B3 / A4"
    return record


def arm_provenance(alloy, name):
    """Compatibility summary; authoritative detail is input_provenance()."""
    if name == "srv":
        return _record("legacyEstimate", "p8:former-served-blend:" + alloy,
                       LEDGER + " pre-P7 served blend", source="Former served blend",
                       scope="No independently located source; descriptive diagnostic only")
    if name == "absorptance_0.14":
        return _record("alloyTransfer", "trapp2017:al1100:A0.14", "Trapp 2017 Table 2 / Fig.7",
                       source="Trapp 2017", scope="Al1100 ground to AlSi10Mg constant molten-wall proxy")
    if name == "vapour_o8":
        return _record("derived", "p8:o8:hybrid-local-slope:Mg1383", O8 + " vapour_constants; " + SPEC + " section 6 / B7",
                       source="O8 Mondal/CIAAW/feedstock Raoult calculation", phase="vapour",
                       reference=2477.605213217703, source_range=[600., 1730.],
                       scope="Mg constant-H CC exceeds Mg fit 600-1730 K and 10 atm synthesis ceiling; feedstock transfer, hybrid/local-slope enthalpy, no depletion")
    if name in {"vapour_3360", "vapour_3760"}:
        return _assumption(name, "Ti Gan nominal Tv3560 K plus or minus 200 K; not a literature boiling value", "vapour")
    if name.startswith("onset_"):
        method = name[6:]
        return _record("modelConvention", "p8:onset:" + method,
                       SPEC + " section 4 / Amendment 2 B1-B2; P3 PREDECLARED section 2.5 c4470b01",
                       source={"O1": "Trapp 2017 Eq.3", "O2": "Fabbro 2018 Eq.2", "O3": "P8 steady Gaussian derivation"}[method],
                       scope="O2 piston event differs from recoil inception" if method == "O2" else "Alternate onset diagnostic event")
    if name.startswith(("power_", "beam_", "deltaT_", "length_")):
        return _assumption(name, "One-at-a-time deterministic sensitivity; no measurement distribution")
    if name == "nominal":
        return _record("sourceDefault", "p8:nominal:" + alloy, SPEC + " sections 3 / A2 / A3",
                       source="P8 located presets; inspect each input for transfers and assumptions")
    return _record("sourcedAlternative", "p8:alternative:" + alloy + ":" + name,
                   SPEC + " Amendment 2 B3; " + LEDGER + " PROPERTY_LEDGER",
                   source="Explicit named source/property/convention alternative; inspect each input")


def input_provenance(alloy, name, arm, nominal):
    """Return metadata for every supplied fixture input without changing values.

    Phase and reference temperature belong to each property, independently of
    the solid-kernel temperature interval and diagnostic liquid Tref. Source
    ranges are null when the inspected source record gives no closed range.
    """
    ti = alloy == "ti6al4v"
    tref = arm.get("Tref")
    if tref is None and arm.get("Tl") is not None and arm.get("deltaT") is not None:
        tref = arm["Tl"] + arm["deltaT"] / 2
    t0, tl = arm.get("T0"), arm.get("Tl")
    mean = (t0 + tl) / 2 if t0 is not None and tl is not None else None
    out = {}
    for key in arm:
        out[key] = _record("legacyEstimate", "p8:unlocated:" + alloy + ":" + key,
                           scope="No located source for this input; never fill from another alloy")
    for key in ("P", "v", "d", "T0"):
        if key in arm:
            out[key] = _record("userInput", "p8:request:" + key, phase="process",
                               scope="Process request echo; excluded from physical-coefficient evidence rule")
    for key in ("K", "cp"):
        if key not in arm:
            continue
        if ti:
            out[key] = _record("derived", "gan2021:solid-fit:kirchhoff:" + key,
                               "Gan 2021 SI Table 1 PDF p.20; " + LEDGER + " PROPERTY_LEDGER.ti6al4v.numeric",
                               source="Gan 2021 fit of Mills data", phase="solid", reference=mean,
                               source_range=[293.15, 1933.15], scope="Kirchhoff mean over [T0,Tl]; constant diffusivity approximation")
        elif alloy == "alsi10mg":
            state = name.removeprefix("state_") if name.startswith("state_") else "AB"
            upper = 373.15 if key == "K" and state == "AB_unrelaxed" else 800.15 if key == "K" and state not in {"HT", "HT_low"} else 773.15
            out[key] = _record("derived", "p7b:alsi10mg:" + state + ":kirchhoff:" + key,
                               ("Yang 2018 Figs.1/5; Akwaboa 2023 Fig.2f / Conclusion(3); Fetni 2024 Fig.4a; " + LEDGER + " PROPERTY_LEDGER.alsi10mg"),
                               source="Recorded solid node tables", phase="solid", reference=mean,
                               source_range=[298.15, upper], scope="Piecewise-linear node integral; endpoint holds extend below/above measured nodes; state " + state)
    if "rho" in out and ti:
        out["rho"] = _record("sourceModelAssumption", "nbs61-v:4430:room-density", "NBS61-V Table 4(S1); " + SPEC + " section 3",
                             source="NBS room-density compilation", phase="solid", reference=293.15,
                             scope="Room density held constant through the solid-kernel interval; not molten density")
    elif "rho" in out and alloy == "alsi10mg":
        out["rho"] = _record("sourceDefault", "akwaboa2023:density:sample100-0.2", "Akwaboa 2023 Table 3 PDF p.5",
                             source="Helium pycnometer density", phase="solid", reference=293.15,
                             scope="Sample100-0.2 transferred to current solid; constant density")
    if "Tl" in out:
        out["Tl"] = (_record("sourceModelAssumption", "gan2021:ti64:liquidus", "Gan 2021 SI Table 1 PDF p.20",
                             phase="solid-liquid-mean", reference=tl, source="P8 source-model liquidus") if ti else
                             _assumption(alloy + ":liquidus", "Supplier/binary proxy convention; not specimen DSC" if alloy == "alsi10mg" else
                                 "Registry liquidus preset without independently located source; missing stays null", "solid-liquid-mean", tl))
    if "A" in out:
        source = ("Simonds 2021 Sec.3.2 Fig.3a PDF p.4; NIST mds2-2525" if ti else
                  "Leis, Weber, Graf 2020 Sec.3 Figs.4-6 pp.175-176" if alloy == "alsi10mg" else
                  LEDGER + " ABSORPTIVITY_AUTHORITY." + alloy)
        out["A"] = _record("alloyTransfer", "p7b:optical-wall-proxy:" + alloy, source,
                           source="Conduction surface absorptance authority", phase="liquid",
                           scope="Located conduction absorptance transferred to constant molten-wall A0; not measured wall optics")
    for key in ("Tv", "Lv", "M"):
        if key not in out:
            continue
        if ti:
            out[key] = _record("sourceModelAssumption", "gan2021:ti64:vapour:" + key, "Gan 2021 SI Table 1 PDF p.20",
                               source="Gan model-input tuple", phase="vapour", reference=arm.get("Tv"),
                               scope="Effective model species; not measured alloy vapour")
        elif alloy == "alsi10mg":
            out[key] = _record("alloyTransfer", "mondal2023:ciaaw:pure-Al:" + key,
                               "Mondal 2023 Table 1 PDF p.3; CIAAW aluminium atomic weight",
                               source="Pure Al Tb/H and elemental molar mass", phase="vapour", reference=arm.get("Tv"),
                               scope="Mg-depleted Al-dominated surface hypothesis; Lv=284000/M; not measured AlSi10Mg")
    liquid = {
        "kl": ("Mohr 2020 p.7 Wiedemann-Franz EML resistivity", 1933.15, None),
        "cpl": ("Mohr 2020 Sec.5 p.8 Fig.4a", 1933.15, [1760., 1890.]),
        "rhol": ("Mohr 2020 Eq.21 p.5", 1933.15, None),
        "slope": ("Mohr 2020 Eq.23 p.6", tref, [1700., 1950.]),
        "mu": ("Rai 2007 Table 6 p.5757", None, None),
    } if ti else {
        "kl": ("Sun 2019 Fig.7, binary Al-Si10 mass percent", tl, [1023.15, 1123.15]),
        "cpl": ("Registry liquid cp1180; pure-Al/Al6061 proxy, ledger1170 discrepancy retained", tl, None),
        "rhol": ("Assael 2012 Table 2 Al-Si12 mass percent", tl, [858., 1700.]),
        "slope": ("Seimiya 2026 Table 1 PDF p.16, oxide-free Al-Si10 at.percent", tref, [1476., 1981.]),
        "mu": ("Assael 2012 Eq.2 / Table 5 PDF p.7, binary Al-Si12 mass percent", tref, [860., 1275.]),
    }
    if alloy in {"ti6al4v", "alsi10mg"}:
        for key, (locator, ref, limits) in liquid.items():
            if key not in out:
                continue
            kind = "sourceDefault" if ti and key != "mu" else "sourceModelAssumption" if ti else "alloyTransfer"
            evidence = "Unresolved" if not ti and key == "cpl" else None
            out[key] = _record(kind, "p8:liquid:" + alloy + ":" + key, locator,
                               source=locator, phase="liquid", reference=ref, source_range=limits,
                               evidence=evidence, scope="Constant liquid tuple at stated reference; evaluate source range separately at diagnostic Tref")
    for key in ("L", "deltaT", "Tref"):
        if key in out:
            out[key] = _assumption(key, "Assumed liquid length/hot-rim contrast/reference; no measured field", "liquid", tref)
    if "L" in out and arm.get("L") == arm.get("d") and not name.startswith("length_"):
        out["L"].update(kind="followsInput", followsInput="beamDiameter_m", followState="following", defaultKind="declaredAssumption", dependsOn=["d"])
    if "Tref" in out:
        out["Tref"].update(kind="followsInput", followsInput="deltaTemperature_K", followState="following", defaultKind="declaredAssumption", dependsOn=["Tl", "deltaT"])
    if alloy == "alsi10mg" and "mu" in out:
        out["mu"]["sourceLawProvenance"] = copy.deepcopy(out["mu"])
        out["mu"].update(kind="followsInput", followsInput="referenceTemperature_K", followState="following", defaultKind="alloyTransfer", dependsOn=["Tl", "deltaT"])
        # The sourced binary law and its evaluated value are different objects.
        # Assumed Tl/deltaT determine the evaluation temperature; preserve the
        # literature-law label while propagating their uncertainty to mu.
        out["mu"]["sourceEvidenceKind"] = evidence_kind(out, ("Tl", "deltaT"))[0]
    for key in ("accommodation", "effectiveNetFactor", "recoil"):
        if key in out:
            out[key] = _record("sourceModelAssumption", "fabbro2020:A10-A12:" + key,
                               "Fabbro 2020 Appendix A A10-A12 PDF pp.19-20; P6 section 4.1",
                               source="Paired source-model assumption", phase="vapour",
                               scope="Accommodation1, beta.2/net.8, recoil.6; independent controls can decouple this pair")
    if "emissivity" in out:
        out["emissivity"] = (_record("sourceModelAssumption", "gan2021:ti64:emissivity", "Gan 2021 SI Table 1 PDF p.20", phase="process") if ti else
                             _assumption("emissivity0.35", "P6 synthetic assumption; no grade-specific wall measurement", "process"))
    if "Lm" in out:
        out["Lm"] = (_record("sourceDefault", "boivineau2006:ti64:Lf290000", "Boivineau 2006 p.520 Sec.5.2 Fig.8", phase="solid-liquid-mean", reference=tl) if ti else
                     _record("alloyTransfer", "p8:pure-Al:fusion397000", LEDGER + " PROPERTY_LEDGER.alsi10mg latent_heat_fusion disclosure", phase="solid-liquid-mean", reference=tl, evidence="Unresolved", scope="Pure-Al fusion proxy; specimen latent heat not established"))
    if "onsetMethod" in out:
        out["onsetMethod"] = _record("modelConvention", "p8:onset:dwell", SPEC + " section 4 / B1", scope="Recoil inception; finite-Gaussian dwell a/v")
    # Named changes must not inherit a generic nominal source record.
    summary = arm_provenance(alloy, name)
    if name == "srv":
        for key in ("K", "cp", "rho"):
            if key in out:
                out[key] = {**summary, "phase": "solid-liquid-mean", "referenceTemperature_K": None}
    elif name in {"vapour_3360", "vapour_3760"}:
        out["Tv"] = {**summary, "referenceTemperature_K": arm["Tv"]}
    elif name == "vapour_o8":
        for key in ("Tv", "Lv", "M"):
            out[key] = {**summary, "dependsOn": ["O8.feedstockComposition", "O8.hybridPressureRoute", "O8.MgTb1383", "O8.localSlopeEnthalpy"]}
    elif name.startswith("absorptance_"):
        locators = {
            ("ti6al4v", .26): "Ye 2019 Table 1 Ti64 Am0.26",
            ("ti6al4v", .33): "Simonds 2021 Sec.3.2 Fig.3a PDF p.4 first2.4ms absorption33percent",
            ("alsi10mg", .28): "Leis, Weber, Graf 2020 Sec.3 Figs.4-6 pp.175-176 areaII200um minimum28percent",
            ("alsi10mg", .4): "Leis, Weber, Graf 2020 Sec.3 Figs.4-6 pp.175-176 conduction35um30-40percent",
            ("in625", .28): "Ye 2019 Table 1 IN625 Am0.28",
            ("in625", .4): "Deisenroth 2020 Sec.3.4 Fig.7 PDF p.10 IN62580W coupling0.40",
            ("in718", .28): "Ye 2019 Table 1 IN625 Am0.28 transferred toIN718",
            ("in718", .38): "Deisenroth 2026 IN718 laser reflections Introduction ground-solid coupling0.38",
            ("ss316l", .28): "Ye 2019 Table 1 316L Am0.28",
            ("ss316l", .31): "Trapp 2017 Sec.3.1 Fig.3a regimeI upper0.31",
        }
        locator = "Trapp 2017 Table 2 / Fig.7 Al1100 ground0.14" if name == "absorptance_0.14" else locators[(alloy, arm["A"])]
        transfer = name == "absorptance_0.14" or alloy == "in718" and arm["A"] == .28
        out["A"] = _record("alloyTransfer" if transfer else "sourcedAlternative",
            summary["sourceId"] if name == "absorptance_0.14" else "p7b:optical-alternative:" + alloy + ":" + name,
            locator, source=locator, phase="liquid", scope=out["A"]["scope"] + "; named source absorptance endpoint")
    elif name.startswith("onset_"):
        out["onsetMethod"] = summary
    elif name.startswith(("power_", "beam_", "deltaT_", "length_")):
        key = next(k for prefix, k in (("power_", "P"), ("beam_", "d"), ("deltaT_", "deltaT"), ("length_", "L")) if name.startswith(prefix))
        out[key] = {**summary, "phase": "process" if key in {"P", "d"} else "liquid", "referenceTemperature_K": tref if key in {"L", "deltaT"} else None}
    elif name.startswith("slope_") or name == "viscosity_mohr":
        keys = ("slope", "mu") if name == "slope_viscosity_gan" else ("mu",) if name == "viscosity_mohr" else ("slope",)
        locator = ("Gan 2021 SI Table 1 PDF p.20" if name == "slope_viscosity_gan" else "Mohr 2020 Eq.23/Fig.3b p.6" if ti else
                   "Fukuyama 2023 ADC12 slope (PROPERTY_LEDGER locator only)" if arm.get("slope") == -.0786e-3 else "Gheribi pure-Al slope (PROPERTY_LEDGER locator only)")
        for key in keys:
            out[key] = _record("sourcedAlternative" if ti else "alloyTransfer", "p8:liquid-alternative:" + alloy + ":" + name + ":" + key,
                               locator, source=locator, phase="liquid", reference=1933.15 if name == "viscosity_mohr" else tref,
                               source_range=[1700., 1950.] if ti and key == "slope" and name != "slope_viscosity_gan" else None,
                               scope="Explicit located source-model alternative; range null where no inspected range exists")
    elif name.startswith("accommodation_"):
        out["effectiveNetFactor"] = _record("sourcedAlternative", "anisimov:effective-net0.82", "P8 Amendment 2 B3 / P6 source note: Anisimov effective0.82",
                                            source="Anisimov effective net-evaporation convention", phase="vapour",
                                            scope="Net0.82 with accommodation1; recoil.6 held independently as a decoupled diagnostic")
    if name.startswith("melt_front"):
        for key in ("K", "cp", "rho"):
            out[key].update(kind="derived", phase="solid-liquid-mean", referenceTemperature_K=tl,
                            sourceId="p8:melt-front:" + alloy + ":" + name + ":" + key,
                            sourceLocator=SPEC + " Amendment 2 B3", sourceRange_K=None,
                            dependsOn=[{"K": "ks(Ts)", "cp": "cps(Ts)", "rho": "rho_s"}[key], {"K": "kl", "cp": "cpl", "rho": "rhol"}[key]],
                            scope="Equal solid-at-solidus/liquid mean; explicit model convention, not a liquid property")
        if "adc12" in name:
            out["rhol"] = _record("alloyTransfer", "fukuyama2023:ADC12:density", "Fukuyama 2023 ADC12 density law; " + LEDGER + " PROPERTY_LEDGER",
                                  phase="liquid", reference=tl, scope="ADC12 composition transfer; inspected closed source range unavailable")
        for key in ("kl", "cpl", "rhol"):
            if arm.get(key) != nominal.get(key) and not (key == "rhol" and "adc12" in name):
                alternatives = {
                    ("kl", 28.7): ("Boivineau 2006 Eq.20; PROPERTY_LEDGER.ti6al4v.text.k_l", 1933.15),
                    ("kl", 33.4): ("Mills liquid k33.4 via Gan2021 SI Table1 PDF p.20", 1933.15),
                    ("cpl", 831.): ("Mills liquid cp831 via Gan2021 SI Table1 PDF p.20", 1933.15),
                    ("cpl", 1126.): ("Boivineau 2006 Eq.17; PROPERTY_LEDGER.ti6al4v.text.cp_l", 1933.15),
                    ("rhol", 3920.): ("Mills liquid density3920; PROPERTY_LEDGER.ti6al4v.text.rho_l", 1933.15),
                    ("rhol", 4123.): ("Li, Johnson, Rhim 2006 density4123 at1943K; PROPERTY_LEDGER.ti6al4v.text.rho_l", 1943.),
                }
                locator, reference = alternatives[(key, arm[key])] if ti else (out[key]["sourceLocator"], out[key]["referenceTemperature_K"])
                out[key].update(kind="sourcedAlternative" if ti else "alloyTransfer",
                                sourceId="p8:melt-front-liquid:" + alloy + ":" + name + ":" + key,
                                source=locator, sourceLocator=locator, referenceTemperature_K=reference,
                                sourceRange_K=None if ti else out[key]["sourceRange_K"])
        for derived_key, liquid_key in (("K", "kl"), ("cp", "cpl"), ("rho", "rhol")):
            if out[liquid_key]["sourceEvidenceKind"] == "Unresolved":
                out[derived_key]["sourceEvidenceKind"] = "Unresolved"
    if name.startswith("enthalpy_cp"):
        cpbar = dict(value=nominal["cp"], provenance=copy.deepcopy(out["cp"]))
        applied_latent = 290000. if ti else float(name.removeprefix("enthalpy_cp_"))
        latent_provenance = (copy.deepcopy(out["Lm"]) if applied_latent == arm.get("Lm") else
                            _assumption(name + ":appliedFusionLatentHeat", "Declared500kJ/kg fusion proxy alternative; not current tuple Lm or measured specimen heat", "solid-liquid-mean", tl))
        latent_provenance["defaultValue"] = nominal.get("Lm")
        out["cp"].update(kind="derived", sourceId="p8:enthalpy-convention:" + alloy + ":" + name,
                         sourceLocator=SPEC + " Amendment 2 B3",
                         phase="solid-liquid-mean", dependsOn=["Tl", "T0"],
                         derivationInputs={"nominalSpecificHeat_J_kgK": cpbar,
                             "appliedFusionLatentHeat_J_kg": {"value": applied_latent, "provenance": latent_provenance}},
                         scope="cpbar+Lf/(Tl-T0); descriptive enthalpy convention, not independently validated kernel")
        out["cp"]["sourceEvidenceKind"] = evidence_kind(
            {"cpbar": cpbar["provenance"], "appliedLatent": latent_provenance, "Tl": out["Tl"]},
            ("cpbar", "appliedLatent", "Tl"))[0]
    if name.startswith("liquidus_"):
        out["Tl"] = _assumption(name, "Declared liquidus proxy bracket with K/cp reintegration; not measured DSC", "solid-liquid-mean", tl)
    if name.startswith("rho_s_"):
        out["rho"].update(kind="sourcedAlternative", sourceId="akwaboa2023:density-endpoint:" + name,
                          scope="Akwaboa sample range endpoint; deterministic transfer, not statistical bound")
    if name in {"linear_last_100K", "cp_fetni_end"}:
        for key in ("K", "cp") if name == "linear_last_100K" else ("cp",):
            out[key].update(sourceId="p8:solid-alternative:" + name + ":" + key,
                            sourceLocator=SPEC + " Amendment 2 B3; Fetni 2024 Fig.4c",
                            scope="Explicit last100K linear extrapolation" if name == "linear_last_100K" else "Fetni endpoint addition at800.15 K then held; source alternative")
        if name == "cp_fetni_end":
            out["cp"]["sourceRange_K"] = [298.15, 800.15]
    if "alpha" in out:
        evidence, weak = evidence_kind(out, ("K", "cp", "rho"))
        out["alpha"] = _record("derived", "p8:alpha:" + "|".join(out[k]["sourceId"] for k in ("K", "cp", "rho")),
                               SPEC + " A4 alpha=K/(rho cp)", phase=out["K"]["phase"], reference=mean,
                               evidence=evidence, dependencies=("K", "rho", "cp"), scope="Derived kernel diffusivity, not measured diffusivity")
        out["alpha"]["weakestInputs"] = weak
    for key, record in out.items():
        record["defaultValue"] = nominal.get(key)
        if record["defaultKind"] is None and record["kind"] not in {"legacyEstimate", "userInput", "modelConvention", "derived"}:
            record["defaultKind"] = record["kind"]
    return out


def evidence_kind(provenance, physical_keys):
    """Per-value source labels; software/request/convention leaves stay excluded."""
    weak = [key for key in physical_keys if key not in provenance or provenance[key]["sourceEvidenceKind"] == "Unresolved"]
    if weak:
        return "Unresolved", weak
    if any(provenance[key]["sourceEvidenceKind"] == "User input" for key in physical_keys):
        return "User input", []
    return "Literature estimate", []


def source_evidence_kind(provenance, physical_keys):
    """Convenience label API for the integration owner."""
    return evidence_kind(provenance, physical_keys)[0]


def changed_input_provenance(alloy, name, arm, nominal, records):
    """Arm display support follows its weakest changed input, not its name.

    This scenario label is separate from each output's dependency support.
    Nominal has no changed inputs and retains its explicit preset summary.
    """
    changed = [key for key in arm if arm[key] != nominal.get(key)]
    if not changed:
        return arm_provenance(alloy, name)
    order = {kind: index for index, kind in enumerate((
        "legacyEstimate", "declaredAssumption", "userInput", "alloyTransfer",
        "derived", "followsInput", "sourceModelAssumption", "sourcedAlternative",
        "sourceDefault", "modelConvention"))}
    def rank(key):
        record = records[key]
        return ({"Unresolved": 0, "User input": 1, "Literature estimate": 2}[record["sourceEvidenceKind"]],
                order[record["kind"]])
    weakest = min(changed, key=rank)
    result = copy.deepcopy(records[weakest])
    result.update(label="Unresolved" if result["sourceEvidenceKind"] == "Unresolved" else result["kind"],
                  changedInputs=changed, weakestInputs=[key for key in changed if rank(key) == rank(weakest)])
    return result


def _exact(value):
    return float(value).hex() if type(value) in (int, float) else value


def deduplicate(records, module):
    """First ID wins; same numbers with different source IDs remain distinct."""
    seen, result = {}, []
    for row in records:
        identity = tuple((k, _exact(row["inputs"].get(k)), row["inputProvenance"][k]["sourceId"])
                         for k in ACTIVE_INPUTS[module])
        if identity in seen:
            result[seen[identity]]["aliasArmIds"].append(row["armId"])
        else:
            seen[identity] = len(result)
            result.append(copy.deepcopy(row))
    return result


def secondary_manifests(registry):
    """Closed IN625/IN718/316L default declarations, without physical fills.

    These are metadata manifests, not successful numerical outputs. Optional
    explicit IN625 vapour selection is a named source arm; it never changes
    the empty nominal nor admits that alloy to the cavity model.
    """
    result = {}
    for alloy, optics in (("in625", [.28, .40]), ("in718", [.28, .38]), ("ss316l", [.28, .31])):
        props = (registry.thermal_props(alloy) or {}) if alloy != "in625" else {}
        kp = (registry.kernel_properties(alloy, 293.15) or {}) if alloy != "in625" else {}
        tl = kp.get("T_liq_K", props.get("liquidus_C") + 273.15 if props.get("liquidus_C") is not None else None)
        k = kp.get("kernel_conductivity_W_mK", props.get("thermal_conductivity_melt_W_mK"))
        cp = kp.get("kernel_specific_heat_J_kgK", props.get("specific_heat_melt_J_kgK"))
        rho = kp.get("kernel_density_kg_m3", props.get("density_kg_m3"))
        alpha = k / (cp * rho) if all(value is not None for value in (k, cp, rho)) else None
        tref = tl + 250 if tl is not None else None
        s = dict(P=200., v=.8, d=80e-6, T0=293.15, Tl=tl,
                 K=k, cp=cp, rho=rho, alpha=alpha,
                 A=props.get("absorptivity_IR"), Tv=None, Lv=None, M=None,
                 kl=props.get("thermal_conductivity_liquid_W_mK"), cpl=props.get("specific_heat_liquid_J_kgK"),
                 rhol=props.get("density_liquid_kg_m3"), slope=-.00089 if alloy == "ss316l" else -.0004,
                 mu=.196 * math.exp(5848 / tref) * 1e-3 if alloy == "in718" and tref else .007 if alloy == "ss316l" else None,
                 L=80e-6, deltaT=500., Tref=tref, accommodation=1., effectiveNetFactor=.8, recoil=.6, emissivity=.35)
        rows = []
        def add(name, family, patch=None):
            state = {**s, **(patch or {})}
            if patch and "d" in patch:
                state["L"] = state["d"]
            if patch and "deltaT" in patch and tl is not None:
                state["Tref"] = tl + state["deltaT"] / 2
                if alloy == "in718":
                    state["mu"] = .196 * math.exp(5848 / state["Tref"]) * 1e-3
            provenance = input_provenance(alloy, name, state, s)
            melt_entries = getattr(registry, "MELT_POINT_PROPERTIES", {})
            melt = melt_entries.get(alloy)
            if melt is not None:
                for key in ("K", "cp"):
                    provenance[key] = _record("sourceDefault" if alloy == "in718" else "alloyTransfer",
                        "p7b:melting-point:" + alloy + ":" + key, melt["source"] + "; " + melt["locator"],
                        source=melt["source"], phase="liquid", reference=melt["evaluationTemperature_C"] + 273.15,
                        scope="Melting-point conduction constant with room density; SS316 to316L transfer, source/repo liquidus differ" if alloy == "ss316l" else "Source melting-point conduction constant with room density")
            provenance["slope"] = _record("sourceModelAssumption", "p8:secondary-slope:" + alloy,
                "Khairallah 2016 p.38 Sec.2.2 sigma=3.282-.00089T" if alloy == "ss316l" else "Mills 2006 p.630 Eq.24",
                phase="liquid", reference=state["Tref"], scope="Source-model assignment" if alloy == "ss316l" else "Clean Ni-alloy zero-O/S assumption; not specimen measurement")
            if alloy == "in718":
                provenance["mu"] = _record("followsInput", "mills2002:in718:viscosity:Eq6", "Mills 2002 p.186 Eq.6",
                    phase="liquid", reference=state["Tref"], follows="referenceTemperature_K", dependencies=("Tref",),
                    scope="Temperature extrapolation; source range not established in inspected record")
                provenance["mu"]["defaultKind"] = "sourceDefault"
            elif alloy == "ss316l":
                provenance["mu"] = _record("alloyTransfer", "mills2002:316:viscosity0.007", "Mills 2002 p.142 Table 1",
                    phase="liquid", reference=1773.15, scope="Estimated 316 value transferred to316L; about30 percent uncertainty, not a viscosity law")
            if name == "slope_commercial_mills":
                provenance["slope"] = _record("sourcedAlternative", "mills2002:in718:commercial-slope", "Mills 2002 p.187 Eq.8; P8 A2",
                    phase="liquid", reference=state["Tref"], scope="Sample preset approximately10ppm totalS, source above1993K; no soluble chemistry inferred")
            if name == "vapour_melt_in625_raoult":
                for key in ("Tv", "Lv", "M"):
                    provenance[key] = _record("derived", "melt:in625:raoult:table-weighted:" + key,
                        "MELT section2.5 source preset; " + SPEC + " A3", phase="vapour", reference=3001.,
                        scope="Explicit IN625 Raoult all-CC/table-weighted research alternative; cavity chain not admitted")
            missing = [key for key in ACTIVE_INPUTS["surfaceBalance"] if state.get(key) is None]
            rows.append(dict(armId=name, family=family, label=name, onsetEvent=None,
                provenance=changed_input_provenance(alloy, name, state, s, provenance),
                changes=[dict(input=k, value=state[k], nominalAnchor=s[k], provenance=provenance[k])
                         for k in state if state[k] != s[k]], aliasArmIds=[], inputs=state,
                inputProvenance=provenance, prerequisiteNulls=missing))
        add("nominal", "nominal")
        for a in optics:
            add(f"absorptance_{a:g}", "absorptance", {"A": a})
        for factor in [.95, 1.05]:
            add(f"power_{factor:g}", "process", {"P": s["P"] * factor})
            add(f"beam_{factor:g}", "process", {"d": s["d"] * factor})
        for delta in [250., 1000.]:
            add(f"deltaT_{delta:g}", "flow-assumption", {"deltaT": delta})
        for factor in [.5, 2.]:
            add(f"length_{factor:g}", "flow-assumption", {"L": s["d"] * factor})
        if alloy == "in718":
            add("slope_commercial_mills", "property-tuple", {"slope": -.00011})
        add("accommodation_effective_0.82", "flow-assumption", {"effectiveNetFactor": .82})
        if alloy == "in625":
            add("vapour_melt_in625_raoult", "vapour-source", {"Tv": 3001., "Lv": 6479525.6, "M": .0559725})
        marangoni = deduplicate([r for r in rows if r["family"] != "vapour-source"], "marangoni")
        surface = deduplicate([r for r in rows if not r["armId"].startswith(("deltaT_", "length_", "slope_"))], "surfaceBalance")
        for module, entries in (("marangoni", marangoni), ("surfaceBalance", surface)):
            for row in entries:
                row["prerequisiteNulls"] = [k for k in ACTIVE_INPUTS[module] if row["inputs"].get(k) is None]
                row["availability"] = "unavailable" if row["prerequisiteNulls"] else "available"
                row["reasonCode"] = ("MARANGONI_VISCOSITY_INPUT_REQUIRED" if module == "marangoni" and row["inputs"]["mu"] is None else
                    "SURFACE_VAPOUR_INPUT_REQUIRED" if module == "surfaceBalance" and any(row["inputs"][k] is None for k in ("Tv", "Lv", "M")) else
                    "RESEARCH_INPUT_REQUIRED" if row["prerequisiteNulls"] else None)
        result[alloy] = {"marangoni": {"n": len(marangoni), "manifest": marangoni},
                         "surfaceBalance": {"n": len(surface), "manifest": surface},
                         "cavityAdmission": "ALLOY_CONSTANT_CHAIN_NOT_ADMITTED"}
    return result



def mean_nodes(nodes, t0, tl, linear=False):
    def value(t):
        if linear and t > nodes[-1][0]:
            last = nodes[-1][0]
            slope = (nodes[-1][1] - value(last - 100)) / 100
            return nodes[-1][1] + slope * (t - last)
        if t <= nodes[0][0]:
            return nodes[0][1]
        for (a, fa), (b, fb) in zip(nodes, nodes[1:]):
            if t <= b:
                return fa + (fb-fa) * (t-a) / (b-a)
        return nodes[-1][1]
    knots = sorted({t0, tl, *[t for t, _ in nodes if t0 < t < tl]})
    return sum((b-a)*(value(a)+value(b))/2 for a, b in zip(knots, knots[1:]))/(tl-t0)


def arms(registry, alloy, s):
    result = [("nominal", s)]
    def add(name, **patch):
        arm = {**s, **patch}
        arm["alpha"] = arm["K"]/(arm["rho"]*arm["cp"])
        if "d" in patch and "L" not in patch:
            arm["L"]=arm["d"]
        if not ti and "mu" not in patch:
            arm["mu"] = 10**(-.8022+658.34/(arm["Tl"]+arm["deltaT"]/2))*1e-3
        result.append((name, arm))
    ti = alloy == "ti6al4v"
    for a in ([.26, .33] if ti else [.28, .4, .14]):
        add(f"absorptance_{a:g}", A=a)
    num = registry.PROPERTY_LEDGER[alloy]["numeric"]
    if ti:
        def front(name, **liquid):
            kl=liquid.get("kl",s["kl"]); cp=liquid.get("cpl",s["cpl"]); rho=liquid.get("rhol",s["rhol"])
            ts=num["T_sol_K"]
            add(name, K=(.0136*ts+1.3097+kl)/2, cp=(.1734*ts+452.72+cp)/2,
                rho=(s["rho"]+rho)/2, **liquid)
        front("melt_front_means")
        for field, values in (("kl",[28.7,33.4]),("cpl",[831.,1126.]),("rhol",[3920.,4123.])):
            for value in values:
                front(f"melt_front_{field}_{value:g}", **{field:value})
        add("enthalpy_cp", cp=s["cp"]+290000/(s["Tl"]-s["T0"]))
        add("srv", K=18.25, cp=728., rho=4430.)
        for tv in [3360.,3760.]:
            add(f"vapour_{tv:g}", Tv=tv)
    else:
        for state in ["HT_low","HT","AB_unrelaxed"]:
            kp=registry.kernel_properties(alloy,s["T0"],state=state)
            add(f"state_{state}", K=kp["kernel_conductivity_W_mK"],cp=kp["kernel_specific_heat_J_kgK"])
        kn=num["k_s_nodes_W_mK"]["AB"]; cn=num["cp_s_nodes_J_kgK"]["AB"]
        add("linear_last_100K",K=mean_nodes(kn,s["T0"],s["Tl"],True),cp=mean_nodes(cn,s["T0"],s["Tl"],True))
        add("cp_fetni_end",cp=mean_nodes(cn+[[800.15,1230.]],s["T0"],s["Tl"]))
        for tl in [863.15,872.15]:
            kp=registry.kernel_properties(alloy,s["T0"],T_liq_K=tl)
            add(f"liquidus_{tl:g}",Tl=tl,K=kp["kernel_conductivity_W_mK"],cp=kp["kernel_specific_heat_J_kgK"])
        for rho in [2620.,2715.]:
            add(f"rho_s_{rho:g}",rho=rho)
        for tag,rhol in [("assael",2603-.241*s["Tl"]),("adc12",2492-.2652*(s["Tl"]-865))]:
            add(f"melt_front_{tag}",K=(kn[-1][1]+64)/2,cp=(cn[-1][1]+1180)/2,rho=(2696+rhol)/2,rhol=rhol,cpl=1180.)
        for lf in [397000.,500000.]:
            add(f"enthalpy_cp_{lf:g}",cp=s["cp"]+lf/(s["Tl"]-s["T0"]))
        add("srv",K=107.5,cp=1045.,rho=2680.)
        add("vapour_o8",Tv=2477.605213217703,Lv=6823019.62479557,M=.024889589126757754)
    for factor in [.95,1.05]:
        add(f"power_{factor:g}",P=s["P"]*factor)
        add(f"beam_{factor:g}",d=s["d"]*factor)
    for method in ["O1","O3"]:
        add(f"onset_{method}",onsetMethod=method)
    for slope in ([-.00014,-.00024] if ti else [-.0786e-3,-.244e-3]):
        add(f"slope_{slope:g}",slope=slope)
    if ti:
        add("viscosity_mohr",mu=.004)
        add("slope_viscosity_gan",slope=-2.6e-4,mu=.00266)
    for delta in [250.,1000.]:
        add(f"deltaT_{delta:g}",deltaT=delta)
    for factor in [.5,2.]:
        add(f"length_{factor:g}",L=s["d"]*factor)
    add("accommodation_effective_0.82",effectiveNetFactor=.82)
    return result


FIELD_LIST = {'keyholeCavity': ('alloy',
                   'power_W',
                   'speed_m_s',
                   'beamDiameter_m',
                   'preheat_K',
                   'liquidus_K',
                   'conductivity_W_mK',
                   'specificHeat_J_kgK',
                   'density_kg_m3',
                   'diffusivity_m2_s',
                   'wallAbsorptanceProxy',
                   'vapourTemperature_K',
                   'vapourLatentHeat_J_kg',
                   'vapourMolarMass_kg_mol',
                   'propertyConvention',
                   'propertySource',
                   'vapourSource',
                   'onsetEvent',
                   'peclet',
                   'thermalResponse_g',
                   'thresholdTemperature_K',
                   'onsetPower_W',
                   'powerOverOnset',
                   'modeledAboveOnset',
                   'cavityDepth_um',
                   'aspectRatio_e_over_d',
                   'cavityAbsorptance',
                   'totalAbsorptance',
                   'energyResidual_W',
                   'rootCount',
                   'rootTopologyStatus',
                   'selectedBranch',
                   'roots',
                   'rootScanRelativeDifference',
                   'cylinderHarmonicDifference'),
 'meltDepthLink': ('cavityDepth_um',
                   'conductionDepth_um',
                   'conditionalMeltDepth_um',
                   'linkedMeltDepth_um',
                   'controllingLeg',
                   'linkDispatch',
                   'conductionStatus',
                   'surfacePower_W',
                   'cavityPower_W',
                   'absorbedPower_W',
                   'depositedThermalPower_W',
                   'unresolvedPower_W',
                   'cavityPowerFraction',
                   'wallConductionPower_W',
                   'cavityLedgerRatio',
                   'lossMultiplier',
                   'photonResidual_W',
                   'relativeConvergenceDifference',
                   'meltDepthCoarse_m',
                   'meltDepthRefined_m',
                   'conductionRefinement_m',
                   'conductionPeakX_m',
                   'conductionRearBound_m',
                   'quadratureOrder',
                   'xSamples',
                   'observable',
                   'floorFieldModelId',
                   'floorExtractorId'),
 'marangoni': ('surfaceTensionSlope_N_mK',
               'slopeMode',
               'slopeBaseline',
               'length_m',
               'deltaTemperature_K',
               'referenceTemperature_K',
               'viscosity_Pa_s',
               'liquidConductivity_W_mK',
               'liquidSpecificHeat_J_kgK',
               'liquidDensity_kg_m3',
               'liquidDiffusivity_m2_s',
               'marangoniNumber',
               'marangoniMagnitude',
               'surfaceVelocityScale_m_s',
               'liquidPecletScale',
               'liquidReynoldsScale',
               'liquidPrandtl',
               'flowDirection',
               'solubleSulfur_ppm',
               'solubleOxygen_ppm',
               'source'),
 'surfaceBalance': ('beamCenterBalanceTemperature_K',
                    'lossFreeCenterTemperature_K',
                    'absorbedCenterFlux_W_m2',
                    'conductiveAdmittance_W_m2K',
                    'monotonicDerivative_W_m2K',
                    'evaporationMassFlux_kg_m2_s',
                    'evaporationEnergyFlux_W_m2',
                    'beamCenterRecoilPressure_Pa',
                    'saturationPressure_Pa',
                    'conductionFlux_W_m2',
                    'radiationFlux_W_m2',
                    'relativeFluxResidual',
                    'surfaceGainRefinementRelative',
                    'iterations',
                    'evaluationLocation',
                    'vapourPreset',
                    'vapourTemperature_K',
                    'vapourLatentHeat_J_kg',
                    'vapourMolarMass_kg_mol',
                    'evaporationConvention',
                    'evaporationAccommodation',
                    'effectiveAccommodation',
                    'netEvaporationFactor',
                    'effectiveNetFactor',
                    'recoilFraction',
                    'emissivity',
                    'source'),
 'alSi10MgIndexDisclosure': ('physicalAbsorptance',
                             'indexAbsorptance',
                             'physicalToIndexRatio',
                             'decision',
                             'classificationChanged',
                             'basis'),
 'unavailablePhysics': ('marangoniWidthDepthCorrection',
                        'physicalWallPeakTemperature_K',
                        'physicalWallRecoilPressure_Pa',
                        'powderAbsorptance',
                        'physicalKeyholeGradient_K_m',
                        'physicalKeyholeCoolingRate_K_s'),
 'alSi10MgVapourMgAware': ('scenarioTemperature_K',
                           'scenarioMolarMass_kg_mol',
                           'scenarioLatentHeatLocalSlope_J_kg',
                           'scenarioLatentHeatTableWeighted_J_kg',
                           'pureMgPressure_atm',
                           'composition_wt_pct',
                           'pressureRoute',
                           'calculationStatus',
                           'source',
                           'dynamicVapourTemperature_K')}
