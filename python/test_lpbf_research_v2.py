"""Revision 5 compact relay and text-table regressions (synthetic transport)."""
import json
import unittest
from unittest.mock import patch

import lpbf_research_codes as codes
import lpbf_research_models as models
import test_lpbf_research_harness as h
from test_lpbf_research_harness import ResearchTestCase


class RevisionFive(ResearchTestCase):
    def test_v1_withdrawn(self):
        body = h.relay_request()
        body['relay']['kind'] = 'blind-freeze-v1'
        response, code, _ = h.call(h.make_dependencies(), body)
        self.assertEqual(code, 2)
        self.assertEqual(response['reasonCode'], 'RESEARCH_REQUEST_INVALID')

    def test_text_tables_and_compact_projection(self):
        deps = h.make_dependencies(h.FakeEngine(relay_fields=True))
        describe, _, _ = h.call(deps, h.relay_request('describe'))
        response, code, _ = h.call(deps, h.relay_request())
        self.assertEqual(code, 0)
        subset = json.loads(response['relay']['subsetJson'])
        self.assertEqual(subset['relaySchemaVersion'], 'blind-freeze-v2')
        self.assertNotIn('labels', subset)
        for table in ('labels', 'sentences', 'statusTexts'):
            self.assertEqual(describe[table + 'Sha256'], models.canonical_sha256_json(describe[table]))
        self.assertEqual(describe['labelsSha256'], response['digests']['labelsSha256'])
        self.assertEqual(describe['identity'], response['identity'])
        self.assertEqual(subset['statements']['keyholeCavity.validationStatus'], 'not-experimentally-validated')
        self.assertNotIn('Synthetic primary sentence.', response['relay']['subsetJson'])
        self.assertEqual(models.MAX_RESPONSE_BYTES, 16 * 1024 * 1024)
        self.assertEqual(codes.RELAY_SUBSET_MAX_CHARS, 16000)
        for sentence in describe['sentences'].values():
            self.assertNotRegex(sentence, r'\{[A-Za-z_]+\}')

    def test_relay_boundary_is_inclusive_and_never_truncates(self):
        for length in (16000, 16001):
            subset = {'ids': 'x' * (length - len(codes.canonical_json({'ids': ''})))}
            self.assertEqual(len(codes.canonical_json(subset)), length)
            with patch.object(models, 'blind_relay_subset', return_value=subset):
                response, code, _ = h.call(h.make_dependencies(), h.relay_request())
            self.assertEqual(code, 0)
            if length == 16000:
                self.assertEqual(response['relay']['subsetJson'], codes.canonical_json(subset))
            else:
                self.assertEqual(response['cause'], 'relay')
                self.assertEqual(response['reasonCode'], 'RESEARCH_RESPONSE_TOO_LARGE')

    def test_describe_digest_includes_labels_for_absent_fields(self):
        deps = h.make_dependencies(h.FakeEngine(relay_fields=True), labels={**h.FIXED_LABELS, 'absent.field': 'Absent'})
        describe, _, _ = h.call(deps, h.relay_request('describe'))
        complete, _, _ = h.call(deps, h.relay_request())
        self.assertEqual(describe['labelsSha256'], complete['digests']['labelsSha256'])

    def test_prose_stays_bound_by_digest_and_does_not_consume_relay_budget(self):
        relays = []
        for padding in (0, 2000):
            response, code, _ = h.call(h.make_dependencies(h.FakeEngine(relay_fields=True, statement_padding=padding)),
                                     h.relay_request())
            self.assertEqual(code, 0)
            self.assertTrue(response['success'])
            relays.append(json.loads(response['relay']['subsetJson']))
        self.assertNotEqual(relays[0]['digests']['researchModelsSha256'], relays[1]['digests']['researchModelsSha256'])
        self.assertEqual(relays[0]['statements'], relays[1]['statements'])

    def test_full_response_above_old_four_mib_cap_is_accepted(self):
        class LargeResponse(h.FakeEngine):
            def aggregate(self, module_id, *args):
                result = super().aggregate(module_id, *args)
                if module_id == 'keyholeCavity':
                    result['padding'] = 'x' * (5 * 1024 * 1024)
                return result
        response, code, stdout = h.call(h.make_dependencies(LargeResponse()), h.request('band', budget=None))
        self.assertEqual(code, 0)
        self.assertTrue(response['success'])
        self.assertGreater(len(stdout.encode('utf-8')), 4 * 1024 * 1024)
