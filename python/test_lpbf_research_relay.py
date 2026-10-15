"""R-REL: research senders and the hash-bound blind relay (integration contract 2026-10-15, Revision 3, 14.1 to 14.4,
14.7), with the fake evaluator and the stubbed identity, property set, arm table and labels of R-TR-11.

R-REL-1 sender and relay request checks. R-REL-2 digests on complete responses only; relay only on complete band
responses of relay requests. R-REL-3 subsetJson is pure ASCII canonical JSON with the closed key set BLIND_RELAY_V1.
R-REL-4 determinism and binding. R-REL-5 the 12,000-character relay cap. R-REL-6 transport survival of the string.
Plus the committed relay fixture tests/fixtures/lpbf-research-relay-v1.json.
"""

from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import lpbf_research_cache as research_cache  # noqa: E402
import lpbf_research_codes as codes  # noqa: E402
import test_lpbf_research_harness as h  # noqa: E402
from test_lpbf_research_harness import ResearchTestCase  # noqa: E402

# The committed relay path list hash (R-REL-3). Changing BLIND_RELAY_V1 changes it; the hub checks it as "known".
EXPECTED_RELAY_PATHS_SHA256 = "2c1493d690f779660c4401dd5b85adbbdb092ce4b8754b62fa5c9c8a08619f69"


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _call(body, engine=None, deps=None):
    deps = deps or h.make_dependencies(engine or h.FakeEngine(relay_fields=True))
    parsed, code, text = h.call(deps, body)
    return parsed, code, text


def _key_set(value, spec):
    """The recursive key structure of value, down to the opaque (None) leaves of spec."""
    if not isinstance(spec, dict):
        return None
    if not isinstance(value, dict):
        return "not-an-object"
    return {key: _key_set(value[key], spec[key]) if key in spec else "unexpected" for key in value}


def _spec_shape(spec):
    return {key: _spec_shape(sub) if isinstance(sub, dict) else None for key, sub in spec.items()}


def _plain(spec):
    return {key: _plain(sub) if hasattr(sub, "items") else None for key, sub in spec.items()}


class RequestChecks(ResearchTestCase):  # R-REL-1
    def refuse(self, body, pointer, rule, limit=None):
        parsed, code, _ = _call(body)
        self.assertEqual(code, 2, parsed)
        self.assertEqual(parsed["reasonCode"], "RESEARCH_REQUEST_INVALID")
        hits = [p for p in parsed["problems"] if (p["pointer"], p["rule"]) == (pointer, rule)]
        self.assertEqual(len(hits), 1, parsed["problems"])
        self.assertEqual(hits[0]["limit"], limit)
        self.assertNotRegex(hits[0]["message"], "[–—]")
        return parsed

    def accept(self, body):
        parsed, code, _ = _call(body)
        self.assertEqual(code, 0, parsed)
        return parsed

    def test_sender_enum_and_default(self):
        self.accept(h.request("nominal"))  # absent sender is research-panel
        body = h.request("nominal")
        body["sender"] = "research-panel"
        self.accept(body)
        body["sender"] = "served-solver"
        self.refuse(body, "/sender", "wrong-type")
        body["sender"] = None
        self.refuse(body, "/sender", "wrong-type")

    def test_supersede_key_prefix_per_sender(self):
        panel = h.request("nominal")
        panel["supersedeKey"] = "p8-research:blind:" + h.PREVIEW_SHA256[:16]
        self.refuse(panel, "/supersedeKey", "sender-key-mismatch")
        self.accept(h.relay_request("nominal"))
        blind = h.relay_request("nominal", supersede_key="p8-research:blind:" + "0" * 16)
        self.refuse(blind, "/supersedeKey", "sender-key-mismatch")  # must name the relay's preview
        blind = h.relay_request("nominal", supersede_key="p8-research:melt-pool")
        self.refuse(blind, "/supersedeKey", "sender-key-mismatch")
        no_relay = h.request("describe")
        no_relay.update(sender="blind-freeze", supersedeKey="p8-research:blind:" + "a" * 16)
        self.accept(no_relay)  # describe without a relay: the pattern alone
        batch = h.relay_request("nominal", sender="batch-client")
        self.accept(batch)
        for bad in ("p8-research:batch:short", "p8-research:batch:UPPERCASE1", "p8-research:batch:" + "a" * 33,
                    "p8-research:melt-pool"):
            batch["supersedeKey"] = bad
            self.refuse(batch, "/supersedeKey", "sender-key-mismatch")

    def test_the_relay_member_is_closed(self):
        cases = [
            ({"kind": "blind-freeze-v2"}, "/relay/kind", "wrong-type", None),
            ({"previewSha256": "A" * 64}, "/relay/previewSha256", "wrong-type", None),
            ({"conditionOrdinal": -1}, "/relay/conditionOrdinal", "below-min", 0),
            ({"conditionOrdinal": 1024}, "/relay/conditionOrdinal", "above-max", 1023),
            ({"conditionOrdinal": 1.0}, "/relay/conditionOrdinal", "wrong-type", None),
            ({"conditionOrdinal": True}, "/relay/conditionOrdinal", "wrong-type", None),
            ({"extra": 1}, "/relay/extra", "unknown-key", None),
        ]
        for change, pointer, rule, limit in cases:
            with self.subTest(pointer=pointer, rule=rule):
                body = h.relay_request("nominal", sender="batch-client")
                body["relay"].update(change)
                self.refuse(body, pointer, rule, limit)
        body = h.relay_request("nominal", sender="batch-client")
        body["relay"] = [1]
        self.refuse(body, "/relay", "wrong-type")
        body = h.relay_request("nominal", ordinal=1023, sender="batch-client")
        self.accept(body)

    def test_relay_sender_options_and_required_rules(self):
        panel = h.request("nominal")
        panel["relay"] = {"kind": "blind-freeze-v1", "previewSha256": h.PREVIEW_SHA256, "conditionOrdinal": 0}
        self.refuse(panel, "/relay", "relay-sender-mismatch")
        batch = h.relay_request("nominal", sender="batch-client")
        batch["researchOptions"] = {"surfaceBalance": {"emissivity": 0.4}}
        self.refuse(batch, "/researchOptions", "relay-options-forbidden")
        batch_options = h.request("nominal", options={"surfaceBalance": {"emissivity": 0.4}})
        batch_options.update(sender="batch-client", supersedeKey="p8-research:batch:run0001a")
        self.accept(batch_options)  # options without a relay are allowed for the batch client
        blind = h.relay_request("nominal")
        blind["researchOptions"] = {}
        self.refuse(blind, "/researchOptions", "relay-options-forbidden")
        blind_band = h.relay_request("band")
        del blind_band["relay"]
        self.refuse(blind_band, "/relay", "relay-required")
        batch_band = h.relay_request("band", sender="batch-client")
        del batch_band["relay"]
        self.accept(batch_band)

    def test_unknown_members_are_still_refused(self):
        body = h.relay_request("nominal")
        body["relayJson"] = "x"
        self.refuse(body, "/relayJson", "unknown-key")


class DigestsAndRelayPresence(ResearchTestCase):  # R-REL-2
    def test_digests_only_on_complete_responses_and_equal_to_the_canonical_hash(self):
        deps = h.make_dependencies(h.FakeEngine(relay_fields=True))
        describe, _, _ = h.call(deps, h.relay_request("describe"))
        self.assertNotIn("digests", describe)
        self.assertNotIn("relay", describe)
        nominal, _, _ = h.call(deps, h.relay_request("nominal"))
        self.assertEqual(nominal["digests"], {
            "researchModelsSha256": _sha(codes.canonical_json(nominal["researchModels"])),
            "labelsSha256": _sha(codes.canonical_json(nominal["labels"]))})
        self.assertNotIn("relay", nominal)
        clock = h.FakeClock()
        chunk_deps = h.make_dependencies(h.FakeEngine(relay_fields=True, clock=clock, seconds_per_arm=10.0),
                                         clock=clock)
        partial, _, _ = h.call(chunk_deps, h.relay_request("band", budget=250))
        self.assertFalse(partial["progress"]["complete"])
        self.assertNotIn("digests", partial)
        self.assertNotIn("relay", partial)
        complete, _, _ = h.call(deps, h.relay_request("band"))
        self.assertTrue(complete["progress"]["complete"])
        self.assertEqual(complete["digests"]["researchModelsSha256"],
                         _sha(codes.canonical_json(complete["researchModels"])))
        self.assertEqual(sorted(complete["relay"]), ["kind", "subsetJson", "subsetSha256"])

    def test_no_relay_without_a_relay_request(self):
        parsed, _, _ = _call(h.request("band", budget=None))
        self.assertIn("digests", parsed)
        self.assertNotIn("relay", parsed)


class SubsetShape(ResearchTestCase):  # R-REL-3
    def test_subset_is_ascii_canonical_json_with_the_closed_key_set(self):
        parsed, code, _ = _call(h.relay_request("band"))
        self.assertEqual(code, 0, parsed)
        text = parsed["relay"]["subsetJson"]
        self.assertTrue(text.isascii())
        subset = json.loads(text)
        self.assertEqual(codes.canonical_json(subset), text)  # canonical: re-encoding reproduces the bytes
        self.assertEqual(parsed["relay"]["subsetSha256"], hashlib.sha256(text.encode("ascii")).hexdigest())
        spec = _plain(codes.BLIND_RELAY_V1)
        self.assertEqual(_key_set(subset, spec), _spec_shape(spec))
        self.assertEqual(subset["relaySchemaVersion"], "blind-freeze-v1")
        self.assertEqual(subset["relayPathsSha256"], codes.RELAY_PATHS_SHA256)
        self.assertEqual(subset["digests"], parsed["digests"])
        self.assertEqual(subset["requestKey"], parsed["requestKey"])
        self.assertEqual(subset["identity"], parsed["identity"])
        scored = subset["scored"]["meltDepthLink.fields.linkedMeltDepth_um"]
        self.assertNotIn("manifest", scored["band"])
        self.assertEqual(scored["band"]["manifestLength"], 6)
        self.assertEqual(sorted(subset["labels"]), sorted(
            f"{path.split('.')[0]}.{path.split('.')[2]}" for section in ("scored", "context")
            for path in codes.BLIND_RELAY_V1[section]))
        self.assertEqual(subset["notes"]["keyholeCavity.consistencyNote.knownContradictions[].id"],
                         ["fake-contradiction"])
        for volatile in ("computeMs", "cache", "clientRequestId", "stage", "progress", "timeBudgetMs", "supersedeKey"):
            self.assertNotIn(f'"{volatile}"', text)

    def test_relay_paths_hash_matches_the_committed_path_list(self):
        paths = codes.relay_paths()
        self.assertEqual(codes.RELAY_PATHS_SHA256,
                         hashlib.sha256(codes.canonical_json(paths).encode("ascii")).hexdigest())
        self.assertEqual(codes.RELAY_PATHS_SHA256, EXPECTED_RELAY_PATHS_SHA256)
        self.assertIn(["scored", "meltDepthLink.fields.linkedMeltDepth_um"], paths)

    def test_paths_the_block_lacks_are_null_not_dropped(self):
        parsed, _, _ = _call(h.relay_request("band"), engine=h.FakeEngine())  # no relay paths emitted
        subset = json.loads(parsed["relay"]["subsetJson"])
        spec = _plain(codes.BLIND_RELAY_V1)
        self.assertEqual(_key_set(subset, spec), _spec_shape(spec))
        self.assertIsNone(subset["scored"]["meltDepthLink.fields.linkedMeltDepth_um"])
        self.assertEqual(subset["labels"], {})


class Determinism(ResearchTestCase):  # R-REL-4
    def _relay(self, body, deps):
        parsed, code, _ = h.call(deps, body)
        self.assertEqual(code, 0, parsed)
        return parsed

    def test_cold_warm_chunked_and_transport_members_give_the_same_bytes(self):
        deps = h.make_dependencies(h.FakeEngine(relay_fields=True))
        cold = self._relay(h.relay_request("band"), deps)
        warm = self._relay(h.relay_request("band", client_id="blind:2"), deps)
        self.assertEqual(warm["cache"]["armsComputed"], 0)
        clock = h.FakeClock()
        chunk_deps = h.make_dependencies(h.FakeEngine(relay_fields=True, clock=clock, seconds_per_arm=0.1),
                                         clock=clock)
        while True:
            chunked = self._relay(h.relay_request("band", budget=250), chunk_deps)
            if chunked["progress"]["complete"]:
                break
        batch_a = self._relay(h.relay_request("band", sender="batch-client",
                                              supersede_key="p8-research:batch:runaaaa1"), deps)
        batch_b = self._relay(h.relay_request("band", sender="batch-client", budget=8000,
                                              supersede_key="p8-research:batch:runbbbb2"), deps)
        self.assertEqual(cold["relay"], warm["relay"])
        self.assertEqual(cold["relay"], chunked["relay"])
        self.assertEqual(batch_a["relay"], batch_b["relay"])
        self.assertNotEqual(cold["relay"]["subsetJson"], batch_a["relay"]["subsetJson"])  # sender is in the subset

    def test_binding_changes_the_subset_but_no_request_or_cache_key(self):
        deps = h.make_dependencies(h.FakeEngine(relay_fields=True))
        base = self._relay(h.relay_request("band"), deps)
        keys_after_base = sorted(deps.cache.keys())
        other_ordinal = self._relay(h.relay_request("band", ordinal=7), deps)
        other_preview = self._relay(h.relay_request("band", preview="b" * 64), deps)
        batch = self._relay(h.relay_request("band", sender="batch-client"), deps)
        panel = self._relay(h.request("band", budget=None), deps)
        for other in (other_ordinal, other_preview):
            self.assertNotEqual(other["relay"]["subsetJson"], base["relay"]["subsetJson"])
            self.assertNotEqual(other["relay"]["subsetSha256"], base["relay"]["subsetSha256"])
        for other in (other_ordinal, other_preview, batch, panel):
            self.assertEqual(other["requestKey"], base["requestKey"])
            self.assertEqual(other["cache"]["armsComputed"], 0)  # every arm reused
            self.assertEqual(other["digests"], base["digests"])
        self.assertEqual(sorted(deps.cache.keys()), keys_after_base)  # no new arm or aggregate key


class RelayCap(ResearchTestCase):  # R-REL-5
    def test_a_subset_above_12000_characters_is_too_large_with_cause_relay(self):
        log = []
        engine = h.FakeEngine(relay_fields=True, statement_padding=2000)
        parsed, code, _ = h.call(h.make_dependencies(engine, log=log), h.relay_request("band"))
        self.assertEqual((code, parsed), (0, {"success": False, "errorKind": "research",
                                              "reasonCode": "RESEARCH_RESPONSE_TOO_LARGE", "cause": "relay"}))
        self.assertTrue(any("relay subsetJson has" in line for line in log))
        self.assertEqual(codes.RELAY_SUBSET_MAX_CHARS, 12000)
        # the same block without a relay request is served: the cap is on the relay string only
        parsed, code, _ = h.call(h.make_dependencies(engine), h.request("band", budget=None))
        self.assertEqual(code, 0)
        self.assertTrue(parsed["success"])

    def test_cost_constants(self):
        self.assertEqual((codes.RELAY_MAX_CONDITIONS, codes.BATCH_DEFAULT_MAX_REQUESTS, codes.BATCH_MAX_REQUESTS),
                         (48, 48, 256))
        self.assertLessEqual(codes.RELAY_MAX_CONDITIONS * codes.RELAY_SUBSET_MAX_CHARS, 576000)


class Transport(ResearchTestCase):  # R-REL-6
    def test_reserialization_with_other_float_formatting_leaves_the_string_and_digest(self):
        parsed, _, text = _call(h.relay_request("band"))
        original = parsed["relay"]

        def js_like(value):
            """Re-encode as a JavaScript client would: integral floats lose their '.0'."""
            if isinstance(value, float) and value.is_integer():
                return int(value)
            if isinstance(value, dict):
                return {k: js_like(v) for k, v in value.items()}
            if isinstance(value, list):
                return [js_like(v) for v in value]
            return value
        rewritten = json.dumps(js_like(json.loads(text)), indent=2, ensure_ascii=False)
        relayed = json.loads(rewritten)["relay"]
        self.assertEqual(relayed["subsetJson"], original["subsetJson"])
        self.assertEqual(hashlib.sha256(relayed["subsetJson"].encode("ascii")).hexdigest(), original["subsetSha256"])
        # parsing and re-serializing the subset itself would change the digest: that is why it travels as a string
        reparsed = codes.canonical_json(js_like(json.loads(original["subsetJson"])))
        self.assertNotEqual(hashlib.sha256(reparsed.encode("ascii")).hexdigest(), original["subsetSha256"])


class RelayFixture(ResearchTestCase):
    def test_relay_output_equals_the_committed_fixture(self):
        expected = json.loads(h.RELAY_FIXTURE_PATH.read_text(encoding="utf-8"))
        got = h.relay_fixture_response()
        self.assertEqual(got, expected, "relay shape changed: if deliberate, regenerate with "
                                        "python -B test_lpbf_research_harness.py --write-fixture")
        self.assertEqual(h.fixture_text(got), h.RELAY_FIXTURE_PATH.read_text(encoding="utf-8").replace("\r\n", "\n"))
        self.assertEqual(expected["identity"]["researchImplementationSha256"], h.STUB_RESEARCH_SHA256)
        self.assertEqual(expected["relay"]["subsetSha256"],
                         hashlib.sha256(expected["relay"]["subsetJson"].encode("ascii")).hexdigest())

    def test_the_cache_bounds_are_unchanged_by_senders(self):
        lru = research_cache.ResearchLRU()
        self.assertEqual((lru.max_entries, lru.max_bytes), (research_cache.MAX_ENTRIES, research_cache.MAX_BYTES))


if __name__ == "__main__":
    unittest.main()
