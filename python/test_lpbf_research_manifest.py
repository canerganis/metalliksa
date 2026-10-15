"""R-MAN and R-MAP-1: source-distinct, module-local deterministic manifests."""
import copy
import json
from unittest import mock
from test_lpbf_research_harness import ResearchTestCase
from test_lpbf_research_arm import resolved, options, FIXTURE
import lpbf_research_manifest as manifest
import lpbf_research_arm as arm
import lpbf_research_models as models


class ManifestContract(ResearchTestCase):
    def test_default_counts_secondary_aliases_and_provenance_split(self):
        fixture=json.loads(FIXTURE.read_text(encoding='utf-8'))
        engine=arm.Engine()
        for alloy,counts in [('ti6al4v',(20,20,17,19)),('alsi10mg',(25,25,13,24)),
                             ('in625',(1,1,7,9)),('in718',(1,1,8,8)),('ss316l',(1,1,7,8))]:
            ctx=resolved(alloy)
            for module,n in zip(('keyholeCavity','meltDepthLink','marangoni','surfaceBalance'),counts):
                plan=engine.manifest(module,ctx,options())
                self.assertEqual(len(plan['arms']),n,(alloy,module))
                if module=='marangoni':
                    self.assertIn('power_0.95',plan['arms'][0]['descriptor']['aliasArmIds'])
                for row in plan['arms']:
                    for p in row['provenance'].values():
                        entry=manifest.input_entry(p)
                        self.assertEqual(set(entry['provenance']),set(manifest.PROVENANCE_KEYS))
            if alloy in fixture['secondaryAlloyManifests']:
                original=fixture['secondaryAlloyManifests'][alloy]
                for module in ('marangoni','surfaceBalance'):
                    plan=engine.manifest(module,ctx,options())
                    self.assertEqual([r['armId'] for r in plan['arms']], [r['armId'] for r in original[module]['manifest']])

    def test_source_id_distinctness_and_user_endpoint_order(self):
        ctx=resolved();s=manifest.nominal_state(ctx);p=manifest.input_provenance('ti6al4v','nominal',s,s)
        other=copy.deepcopy(p);other['A']['sourceId']='different-source-same-value'
        plan=manifest.build_manifest('keyholeCavity',ctx,options(), [('nominal',s,p),('second',s,other),('alias',s,p)])
        self.assertEqual([r['armId'] for r in plan['arms']],['nominal','second'])
        self.assertEqual(plan['arms'][0]['descriptor']['aliasArmIds'],['alias'])
        opts=options({'surfaceBalance':{'emissivity':.4},'ranges':{'surfaceBalance':{'emissivity':{'min':.2,'max':.6}}}})
        a=manifest.build_manifest('surfaceBalance',ctx,opts)
        self.assertEqual([r['armId'] for r in a['arms']][-2:],['user:surfaceBalance:emissivity:low','user:surfaceBalance:emissivity:high'])
        self.assertEqual(manifest.build_manifest('keyholeCavity',ctx,opts),manifest.build_manifest('keyholeCavity',ctx,options()))

    def test_target_module_alias_lookup_not_reading_aliases(self):
        cavity=[dict(armId='nominal',descriptor={'aliasArmIds':['same']}),dict(armId='power',descriptor={'aliasArmIds':['original']})]
        self.assertEqual(manifest.target_reference('original',cavity),('power',False))
        self.assertEqual(manifest.target_reference('missing',cavity),('nominal',True))

    def test_cap_and_min_ties_use_declared_order(self):
        ctx=resolved();s=manifest.nominal_state(ctx);p=manifest.input_provenance('ti6al4v','nominal',s,s)
        injected=[('nominal' if i==0 else 'injected:'+str(i),{**s,'P':s['P']+i},p) for i in range(81)]
        engine=arm.Engine()
        with mock.patch.object(engine,'manifest',side_effect=lambda m,c,o:manifest.build_manifest(m,c,o,injected)):
            deps=models.default_dependencies()
            protocol=models._Protocol(deps=__import__('dataclasses').replace(deps,engine=engine),context=ctx,options=options(),identity=deps.identity.identity(),t0=deps.clock(),sender='research-panel')
            plan=protocol._plan_module('keyholeCavity')
            self.assertEqual(plan.code,'RESEARCH_ARM_LIMIT_EXCEEDED')
        envelope=models.numeric_envelope('x',['first','second'],{'first':{'values':{'x':2.}},'second':{'values':{'x':2.}}})
        self.assertEqual((envelope['minArmId'],envelope['minArmTies']),('first',2))

    def test_mapping_is_closed_and_revision_four_rejects_unknown_records(self):
        fixture=json.loads(FIXTURE.read_text(encoding='utf-8'))
        mapped_inputs=set(manifest.INPUT_NAMES.values())
        for item in fixture['bands']:
            for old,module in item['modules'].items():
                self.assertLessEqual(set(module),set('fields categoricalSupport armIds successfulArms failedArms armResults statusSupport validationStatus experimentalValidation moduleEvidenceCeiling modeledOnsetSupport bandCrossesOnset'.split()))
                name=manifest.FIXTURE_TO_RUNTIME.get(old,old)
                for row in module['armResults']:
                    self.assertLessEqual(set(row),set('armId provenance inputProvenance inputs values consistencyStatus validationStatus experimentalValidation moduleEvidenceCeiling valueProvenance inputScopeReasons fieldShapeDiagnostics'.split()))
                    self.assertLessEqual(set(manifest.map_fixture_values(row['values'],name)),set(manifest.FIELD_LIST[name]))
                    self.assertLessEqual(set(manifest.map_fixture_values(row['inputs'])),mapped_inputs)
                    for record in row['inputProvenance'].values():
                        entry=manifest.input_entry(record)
                        self.assertEqual(len(entry['provenance']),17)
                        with self.assertRaises(ValueError):manifest.input_entry({**record,'unmappedLaterKey':1})

    def test_belton_endpoints_recompute_and_custom_options_stay_local(self):
        ctx=resolved();engine=arm.Engine()
        opts=options({'marangoni':{'slopeMode':'fe-s-belton','solubleSulfur_ppm':20.},
                      'ranges':{'marangoni':{'solubleSulfur_ppm':{'min':0.,'max':50.}}}})
        rows=engine.manifest('marangoni',ctx,opts)['arms'];lookup={r['armId']:r for r in rows}
        for end,value in [('low',0.),('high',50.)]:
            row=lookup['user:marangoni:solubleSulfur_ppm:'+end]
            self.assertAlmostEqual(row['state']['slope'],arm.belton_slope('fe-s-belton',value,row['state']['Tref']))
        custom=options({'marangoni':{'surfaceTensionSlope_N_mK':-.0003,'viscosity_Pa_s':.006}})
        lookup={r['armId']:r['state'] for r in engine.manifest('marangoni',ctx,custom)['arms']}
        self.assertEqual(lookup['slope_-0.00014']['mu'],.006)
        self.assertEqual(lookup['viscosity_mohr']['slope'],-.0003)
        baseline=engine.manifest('surfaceBalance',ctx,options())['arms'][0]
        net=engine.manifest('surfaceBalance',ctx,options({'surfaceBalance':{'evaporationConvention':'net-factor','netEvaporationFactor':.8}}))['arms'][0]
        self.assertNotEqual(baseline['inputs'],net['inputs'])
        ctx=resolved('in718');opts=options({'ranges':{'marangoni':{'referenceTemperature_K':{'min':1700.,'max':2500.}}}})
        rows=engine.manifest('marangoni',ctx,opts)['arms']
        import math
        for row in rows[-2:]:
            self.assertAlmostEqual(row['state']['mu'],.196*math.exp(5848/row['state']['Tref'])*1e-3)

    def test_aggregate_cache_tracks_descriptor_metadata_even_when_arm_keys_match(self):
        import test_lpbf_research_harness as harness
        engine=harness.FakeEngine();original_manifest=engine.manifest;original_aggregate=engine.aggregate
        label=['first']
        def plan(module,ctx,opts):
            result=original_manifest(module,ctx,opts)
            result['arms'][0]['descriptor']['label']=label[0]
            return result
        def aggregate(module,ctx,opts,manifest,records,bands):
            result=original_aggregate(module,ctx,opts,manifest,records,bands)
            result['testManifest']=copy.deepcopy(manifest['arms'][0]['descriptor'])
            return result
        engine.manifest=plan;engine.aggregate=aggregate
        deps=harness.make_dependencies(engine)
        first,_,_=harness.call(deps,harness.request('band'))
        label[0]='second'
        second,_,_=harness.call(deps,harness.request('band'))
        self.assertEqual(first['researchModels']['keyholeCavity']['testManifest']['label'],'first')
        self.assertEqual(second['researchModels']['keyholeCavity']['testManifest']['label'],'second')
