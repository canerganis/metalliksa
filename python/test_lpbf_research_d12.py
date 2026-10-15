"""D-12 Revision 5 capacity checks using the real evaluator, no experimental claims."""
import json
import unittest
from dataclasses import replace

import lpbf_research_cache as cache
import lpbf_research_codes as codes
import lpbf_research_models as models
from lpbf_research_measure import TimedEngine, request
from test_lpbf_research_harness import ResearchTestCase


class RelayCapacity(ResearchTestCase):
    def test_real_default_relays_and_eighty_arm_responses(self):
        for alloy in ('ti6al4v', 'alsi10mg'):
            for cap in (False, True):
                with self.subTest(alloy=alloy, cap=cap):
                    deps = replace(models.default_dependencies(), engine=TimedEngine(cap), cache=cache.ResearchLRU())
                    body = request(alloy)
                    body.update(sender='blind-freeze', supersedeKey='p8-research:blind:' + 'a' * 16,
                                relay=dict(kind='blind-freeze-v2', previewSha256='a' * 64, conditionOrdinal=0))
                    # Normal path: strictly progressing budgeted chunks, including the synthetic cap probe.
                    body['timeBudgetMs'] = 1500
                    previous = -1
                    for _ in range(500):
                        stdout, exit_code = models.run(json.dumps(body), deps)
                        response = json.loads(stdout)
                        self.assertEqual(exit_code, 0)
                        self.assertTrue(response['success'], response)
                        self.assertGreater(response['progress']['armsDone'], previous)
                        previous = response['progress']['armsDone']
                        if response['progress']['complete']:
                            break
                    else:
                        self.fail('band did not complete')
                    size = len(response['relay']['subsetJson'])
                    self.assertLessEqual(size, 16000)
                    self.assertLessEqual(len(stdout.encode('utf-8')), 16 * 1024 * 1024)
                    subset = json.loads(response['relay']['subsetJson'])
                    scored = subset['scored']['meltDepthLink.fields.linkedMeltDepth_um']
                    self.assertEqual(scored['band']['manifestLength'], 80 if cap else (20 if alloy == 'ti6al4v' else 25))
                    self.assertIsInstance(scored['band']['min'], (int, float))
                    self.assertIsInstance(subset['support']['keyholeCavity.band.onsetSupport']['total'], int)
                    self.assertIn(subset['notes']['meltDepthLink.consistencyNote.sentenceId'], codes.SENTENCES)
                    describe_body = {**body, 'stage': 'describe', 'timeBudgetMs': None}
                    describe_stdout, describe_code = models.run(json.dumps(describe_body), deps)
                    describe = json.loads(describe_stdout)
                    self.assertEqual(describe_code, 0)
                    self.assertEqual(describe['labelsSha256'], response['digests']['labelsSha256'])
                    self.assertEqual(describe['identity'], response['identity'])
                    print(f'D12 {alloy} cap={cap}: relay={size} chars; response={len(stdout.encode("utf-8"))} bytes', flush=True)
