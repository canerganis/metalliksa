"""P8 phase C: synthetic software replay, never experimental validation."""
import json
import math
from pathlib import Path

from test_lpbf_research_harness import ResearchTestCase
import lpbf_research_context as context
import lpbf_research_models as models
import lpbf_research_arm as arm
import lpbf_research_manifest as manifest

FIXTURE = Path(__file__).resolve().parents[1] / 'docs/research/scripts/p8_amendment1_synthetic.json'


def request(alloy='ti6al4v', power=200., stage='band', options=None):
    result = dict(schemaVersion=models.REQUEST_SCHEMA_VERSION, supersedeKey='p8-research:melt-pool',
                  clientRequestId='phase-c', stage=stage, timeBudgetMs=None,
                  process=dict(material=alloy, laserPower_W=power, scanSpeed_mm_s=800.,
                               beamDiameter_um=80., preheatTemp_C=20., laserWavelength='IR_1064nm',
                               absorptionModel='flat-plate'), propertyContext={'kind': 'nominal'})
    if options is not None:
        result['researchOptions'] = options
    return result


def resolved(alloy='ti6al4v', power=200.):
    name='Inconel 625' if alloy=='in625' else alloy
    return context.resolve(request(name, power), context.served_property_provider())


def options(value=None):
    return models.normalized_options({'researchOptions': value or {}})


class PhysicsReplay(ResearchTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.fixture = json.loads(FIXTURE.read_text(encoding='utf-8'))
        cls.engine = arm.Engine()

    def close(self, actual, expected, path=''):
        if type(expected) in (float, int):
            self.assertIsNotNone(actual, path)
            self.assertTrue(math.isclose(actual, expected, rel_tol=2e-6, abs_tol=1e-7),
                            (path, actual, expected))
        elif isinstance(expected, list):
            self.assertEqual(len(actual), len(expected), path)
            for a, b in zip(actual, expected):
                self.close(a, b, path)
        elif isinstance(expected, dict):
            for key, value in expected.items():
                self.close(actual[key], value, path + '.' + key)
        else:
            self.assertEqual(actual, expected, path)

    def test_six_points_and_all_declared_arm_numeric_records(self):
        for point in self.fixture['points']:
            self.close(arm.evaluate_reference(manifest.nominal_state(resolved(point['alloy'], point['power_W']))),
                       point['values'], point['alloy'])
        for item in self.fixture['bands']:
            ctx = resolved(item['alloy'])
            upstream = {}
            for fixture_module, expected in item['modules'].items():
                module = manifest.FIXTURE_TO_RUNTIME.get(fixture_module, fixture_module)
                plan = self.engine.manifest(module, ctx, options())
                self.assertEqual([a['armId'] for a in plan['arms']], expected['armIds'])
                records={}
                for spec, row in zip(plan['arms'], expected['armResults']):
                    self.assertEqual(spec['state'], row['inputs'])
                    self.assertEqual(spec['rawProvenance'], row['inputProvenance'])
                    record = self.engine.evaluate_arm(module, ctx, options(), spec, upstream)
                    self.assertNotIn('armFailure', record, (module, spec['armId'], record))
                    self.close(record['values'], manifest.map_fixture_values(row['values'], module),
                               module + '/' + spec['armId'])
                    upstream[module + '/' + spec['armId']] = record
                    records[spec['armId']]=record
                envelopes=models.band_envelopes('computed',list(records),records)
                result=self.engine.aggregate(module,ctx,options(),plan,records,envelopes)
                for key,band in expected['fields'].items():
                    runtime=manifest.FIXTURE_TO_RUNTIME.get(key,key)
                    actual=result['fields'][runtime]['band']
                    for position in ('min','nominal','max'):self.close(actual[position]['value'],band[position],module+'/'+key+'/'+position)
                    for position in ('minArmId','maxArmId'):self.assertEqual(actual[position],band[position])
                statuses={r['status']:r['count']['value'] for r in result['band']['statusSupport']}
                self.assertEqual(statuses,expected['statusSupport'])

    def test_both_sides_of_onset_and_field_shape_policy(self):
        for record in self.fixture['fieldShapeStepChecks']:
            state = manifest.nominal_state(resolved(record['alloy']))
            self.close(arm.field_shape_step(state), manifest.map_field_shape_step(record))
        for case in self.fixture['fieldShapeWarningChecks']:
            if 'gaussianFloor_um' in case:
                self.close(arm.field_shape_policy(case['powerOverOnset'],case['gaussianFloor_um'],case['conditionalExcess_um'],case['pointExcess_um']),case['diagnostics'])
        for case in self.fixture['statusSemanticsChecks']:
            self.assertEqual(arm.consistency_status('cavity',**case['parameters']),case['status'])

    def test_root_topology_and_independent_normalization(self):
        for case in self.fixture['syntheticRootTopology']:
            roots=arm._scan_roots(case['S'],case['absorptance'],'specular_cone',2049)
            self.close([dict(R=float(r.R),scalarRelaxation=r.stability) for r in roots],case['roots'])
        from eagar_tsai_solver import EagarTsaiField
        for alloy in ('ti6al4v','alsi10mg'):
            s=manifest.nominal_state(resolved(alloy));a=s['d']/2
            transient=s['A']*4*math.sqrt(s['alpha'])/(math.pi**1.5*s['K'])*arm.quad(
                lambda u:1/(a*a+8*s['alpha']*u*u),0,math.sqrt(a/s['v']),epsabs=1e-8,epsrel=1e-12)[0]
            self.assertAlmostEqual((arm.threshold_temperature(arm.material(s))-s['T0'])/arm.onset_power(s),transient,places=9)
            field=EagarTsaiField(s['T0']-273.15,s['A']*s['P'],s['K'],s['alpha'],a).bind_speed(s['v'])
            for x,z in ((0.,0.),(-a,a/2),(-2*a,a)):
                independent=s['A']*s['P']*arm.gaussian_gain(s['v'],s['d'],s['K'],s['alpha'],x=x,z=z)
                self.assertTrue(math.isclose(independent,field.temperature_C(x,0.,z)-(s['T0']-273.15),rel_tol=1e-5))

    def test_comparison_identity_coefficient_recompute_and_status(self):
        engine=self.engine;ctx=resolved('alsi10mg');opts=options();upstream={}
        cp=engine.manifest('keyholeCavity',ctx,opts)
        for spec in cp['arms']:
            upstream['keyholeCavity/'+spec['armId']]=engine.evaluate_arm('keyholeCavity',ctx,opts,spec,{})
        for module in ('keyholeCavity','meltDepthLink','surfaceBalance'):
            plan=engine.manifest(module,ctx,opts);spec=plan['arms'][0]
            row=engine.evaluate_arm(module,ctx,opts,spec,upstream)
            mismatch=row['onsetMismatch']
            expected=next(r for r in self.fixture['onsetSurfaceContradictions'] if r['alloy']=='alsi10mg')
            for key in ('onsetPower_W','thresholdTemperature_K','surfaceThresholdPower_W','surfaceToCavityOnsetRatio'):
                self.close(mismatch['values'][key],expected[key])
            note=engine._note(module,row)
            self.assertEqual(note['onsetMismatch']['surfaceThresholdPower_W']['sourceEvidenceKind'],'Unresolved')
            self.assertEqual(note['onsetMismatch']['surfaceThresholdPower_W']['validationStatus'],arm.SURFACE_VALIDATION)
            self.assertEqual(note['onsetMismatch']['thresholdTemperature_K']['validationStatus'],arm.NON_SURFACE_VALIDATION)
        surface=engine.manifest('surfaceBalance',ctx,opts)
        spec=next(r for r in surface['arms'] if r['armId']=='accommodation_effective_0.82')
        changed=engine.evaluate_arm('surfaceBalance',ctx,opts,spec,upstream)['onsetMismatch']
        base=engine.evaluate_arm('surfaceBalance',ctx,opts,surface['arms'][0],upstream)['onsetMismatch']
        self.assertNotEqual(changed['values']['surfaceThresholdPower_W'],base['values']['surfaceThresholdPower_W'])
        custom=options({'surfaceBalance':{'vapourPreset':'custom','vapourTemperature_K':3000.,'vapourLatentHeat_J_kg':1e7,'vapourMolarMass_kg_mol':.03}})
        p=engine.manifest('surfaceBalance',ctx,custom)
        row=engine.evaluate_arm('surfaceBalance',ctx,custom,p['arms'][0],upstream)
        self.assertEqual(row['onsetMismatch']['comparison'],'tuple-mismatch')
        event=next(r for r in cp['arms'] if r['armId']=='onset_O1')
        self.assertEqual(engine.evaluate_arm('keyholeCavity',ctx,opts,event,{})['onsetMismatch']['comparison'],'event-mismatch')

    def test_software_scope_and_independent_leg_failures(self):
        from dataclasses import replace
        from unittest import mock
        ctx=resolved();s=manifest.nominal_state(ctx)
        self.assertEqual(arm.admission(replace(ctx,preheat_C=19.,preheat_K=292.15),{**s,'T0':292.15},'keyholeCavity'),'PREHEAT_OUTSIDE_PROPERTY_SCOPE')
        for pe in (.01,10.):
            test={**s,'P':0.,'v':2*s['alpha']*pe/s['d']}
            self.assertIsNone(arm.admission(ctx,test,'keyholeCavity'))
        for pe in (.009999,10.00001):
            test={**s,'v':2*s['alpha']*pe/s['d']}
            self.assertEqual(arm.admission(ctx,test,'keyholeCavity'),'PECLET_OUTSIDE_NUMERICAL_SCOPE')
        self.assertEqual(arm.admission(replace(ctx,tupleEqualsNominal=False),s,'keyholeCavity'),'UNSOURCED_PROPERTY_OVERRIDE')
        cavity=arm.cavity_values(s)
        with mock.patch.object(arm,'gaussian_floor',side_effect=ValueError('CONDUCTION_EXTENT_UNRESOLVED')):
            values,failures=arm.link_values(s,cavity)
        self.assertGreater(values['conditionalMeltDepth_um'],0.)
        self.assertIsNone(values['linkedMeltDepth_um']);self.assertIn('conductionDepth_um',failures)
        with mock.patch.object(arm,'melt_depth_from_e',side_effect=ValueError('TIP_SHELL_UNRESOLVED')):
            values,failures=arm.link_values(s,cavity)
        self.assertGreater(values['conductionDepth_um'],0.)
        self.assertIsNone(values['linkedMeltDepth_um']);self.assertEqual(failures['conditionalMeltDepth_um'],'TIP_SHELL_UNRESOLVED')

    def test_o8_runtime_replays_the_eight_named_source_scenarios(self):
        fixture=json.loads(FIXTURE.with_name('alsi10mg_vapour_o8.json').read_text(encoding='utf-8'))
        ctx=resolved('alsi10mg');engine=self.engine;opts=options()
        plan=engine.manifest('alSi10MgVapourMgAware',ctx,opts)
        self.assertEqual([r['armId'] for r in plan['arms']],fixture['band']['orderedArmIds'])
        for spec,expected in zip(plan['arms'],fixture['band']['scenarios']):
            result=engine.evaluate_arm('alSi10MgVapourMgAware',ctx,opts,spec,{})['values'];reference=expected['values']
            for actual,key in [('scenarioTemperature_K','T_v_K'),('scenarioMolarMass_kg_mol','M_vapour_kg_mol'),
                               ('scenarioLatentHeatLocalSlope_J_kg','L_local_slope_J_kg'),('scenarioLatentHeatTableWeighted_J_kg','L_table_weighted_J_kg'),('pureMgPressure_atm','mg_pure_pressure_atm')]:
                self.assertTrue(math.isclose(result[actual],reference[key],rel_tol=1e-11,abs_tol=1e-9),(spec['armId'],actual))
            self.assertEqual(result['composition_wt_pct'],reference['composition_wt_pct'])
            self.assertIsNone(result['dynamicVapourTemperature_K'])

    def test_zero_flow_and_belton_derivative(self):
        state = manifest.nominal_state(resolved())
        for patch in ({'slope': 0.}, {'deltaT': 0.}):
            values = arm.marangoni({**state, **patch})
            self.assertEqual(values['marangoniNumber'], 0.)
            self.assertEqual(values['surfaceVelocityScale_m_s'], 0.)
        for mode, constants in [('fe-s-belton', (.00318, -166200., 1.30e-5)),
                                ('fe-o-belton', (.0138, -146300., 2.03e-5))]:
            t, ppm = 1900., 12.
            k, dh, gamma = constants
            def sigma(temp):
                return -.00043*temp - arm.GAS_CONSTANT*temp*gamma*math.log1p(
                    k*ppm/10000*math.exp(-dh/(arm.GAS_CONSTANT*temp)))
            derivative = (sigma(t+.01)-sigma(t-.01))/.02
            self.assertAlmostEqual(arm.belton_slope(mode, ppm, t), derivative, places=10)

    def test_low_power_gaussian_zero_is_not_missing(self):
        for power, depth in [(0., 0.), (5., 0.), (10., 0.), (20., 4.637173704115992)]:
            value = arm.evaluate_reference(manifest.nominal_state(resolved(power=power)))
            self.assertAlmostEqual(value['linkedMeltDepth_um'], depth, places=6)
            self.assertEqual(value['cavityDepth_um'], 0.)


if __name__ == '__main__':
    import unittest
    unittest.main()
