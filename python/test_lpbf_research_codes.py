"""R-CODE: closed codes/labels, evidence precedence and closure-dependent status."""
import json
from dataclasses import replace
from unittest import mock
from test_lpbf_research_harness import ResearchTestCase
from test_lpbf_research_arm import resolved, options, request
import lpbf_research_arm as arm
import lpbf_research_manifest as manifest
import lpbf_research_models as models
import lpbf_research_codes as codes


class CodeContract(ResearchTestCase):
    def test_registry_precedence_and_pending_wording(self):
        self.assertEqual(codes.winning_code(['NONFINITE_RESULT','PECLET_OUTSIDE_NUMERICAL_SCOPE']),'PECLET_OUTSIDE_NUMERICAL_SCOPE')
        with self.assertRaises(ValueError):codes.winning_code(['SOURCE_SCOPE_TRANSFER'])
        for code,entry in codes.REASON_CODES.items():
            self.assertIn(entry['class'],codes.CLASS_ORDER)
            self.assertTrue(entry['scope']);self.assertTrue(entry['text'])
            self.assertNotIn('\u2013',entry['text']);self.assertNotIn('\u2014',entry['text'])
        self.assertEqual(codes.WORDING['approvalStatus'],'pending maintainer approval')
        for module,fields in manifest.FIELD_LIST.items():
            for field in fields:self.assertIn(module+'.'+field,codes.LEAF_LABELS)

    def test_process_inputs_excluded_and_custom_coefficient_dependencies(self):
        engine=arm.Engine();ctx=resolved();opts=options()
        plan=engine.manifest('keyholeCavity',ctx,opts)
        row=engine.evaluate_arm('keyholeCavity',ctx,opts,plan['arms'][0],{})
        result=engine.aggregate('keyholeCavity',ctx,opts,plan,{'nominal':row},None)
        field=result['fields']['cavityDepth_um']
        self.assertEqual(field['sourceEvidenceKind'],'Literature estimate')
        self.assertNotIn('power_W',field['dependsOn'])
        self.assertEqual(result['consistencyNote']['status'],'extrapolated')
        self.assertNotIn('inside',result['consistencyNote']['sentence']['value'])
        self.assertEqual(field['validationStatus'],arm.NON_SURFACE_VALIDATION)
        for value in result['consistencyNote']['onsetMismatch'].values():
            if isinstance(value,dict) and value.get('unit') and value.get('unit')!='1':
                self.assertIn(value['validationStatus'],(arm.NON_SURFACE_VALIDATION,arm.SURFACE_VALIDATION))
        custom=options({'surfaceBalance':{'emissivity':.4}})
        plan=engine.manifest('surfaceBalance',ctx,custom)
        r=engine.evaluate_arm('surfaceBalance',ctx,custom,plan['arms'][0],{'keyholeCavity/nominal':row})
        f=arm._field('surfaceBalance','beamCenterBalanceTemperature_K',r['values']['beamCenterBalanceTemperature_K'],r)
        self.assertEqual(f['sourceEvidenceKind'],'User input');self.assertIn('emissivity',f['weakestInputs'])
        self.assertEqual(f['validationStatus'],arm.SURFACE_VALIDATION)
        reset=options({'surfaceBalance':{'emissivity':.3}})
        p=engine.manifest('surfaceBalance',ctx,reset)['arms'][0]
        self.assertNotEqual(p['provenance']['emissivity']['kind'],'userInput')

    def test_real_transport_serializes_and_keeps_onset_support_in_cavity_only(self):
        deps=models.default_dependencies();logs=[];deps=replace(deps,log=logs.append)
        stdout,exit_code=models.run(json.dumps(request()),deps)
        response=json.loads(stdout)
        self.assertEqual(exit_code,0);self.assertEqual(logs,[])
        self.assertTrue(response['success'],response)
        block=response['researchModels']
        self.assertEqual(block['keyholeCavity']['band']['onsetSupport']['total']['value'],20)
        self.assertNotIn('onsetSupport',block['meltDepthLink']['band'])
        for module in models.CONTAINERS:
            self.assertEqual(set(block[module]['fields']),set(manifest.FIELD_LIST[module]))
            self.assertEqual(block[module]['moduleEvidenceCeiling'],'screening-only')
            for key in block[module]['fields']:self.assertIn(module+'.'+key,response['labels'])
        for descriptor in block['keyholeCavity']['band']['manifest']:
            for change in descriptor['changes']:
                self.assertIn('unit',change['value'])
                if change['nominalAnchor'] is not None:self.assertIn('value',change['nominalAnchor'])

    def test_cause_specific_permanent_refusals(self):
        s=manifest.nominal_state(resolved())
        r=arm._reason('PECLET_OUTSIDE_NUMERICAL_SCOPE',[],{'state':{**s,'v':200.}})
        self.assertEqual((r['limitMin'],r['limitMax']),(.01,10.))
        self.assertTrue(r['changeInputs']);self.assertIn('software limit',codes.refusal_text(r['code'],r))
        r=arm._reason('ONSET_REFERENCE_UNAVAILABLE',[],{'state':{**s,'Tv':None}})
        self.assertEqual(r['cause'],'alloy-not-admitted');self.assertNotIn('Enter a value',codes.refusal_text(r['code'],r))
        r=arm._reason('VAPOUR_PRESSURE_OUTSIDE_SOURCE_RANGE',[],{'state':s})
        self.assertIn('always withheld',codes.refusal_text(r['code'],r))
