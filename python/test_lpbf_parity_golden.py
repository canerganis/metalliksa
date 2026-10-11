"""LPBF 5c parity goldens (design stage P2/P3): bit equality before and after the bump.

Each case in tools/lpbf_parity_check.py is checked against python/golden/lpbf_parity/.
The goldens were first recorded at 7482697c... (the side before the 5c bump) and,
after that bump, re-recorded twice each at edddf0dc... in a commit of their own (B5
step 2). They are the "before" side of the next bump and must never be re-recorded
in the same commit as a manifest edit. G2 (real bare-plate
fixture, ~106-140 s) runs only with LPBF_PARITY_SLOW=1; the fast cases take about
1.5 minutes. The mutation tests prove that a changed golden byte, a changed
numerical tolerance, a changed material value and an unpinned implementation
each make the check fail.
"""

import contextlib
import copy
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
_SPEC = importlib.util.spec_from_file_location("lpbf_parity_check", HERE / "tools" / "lpbf_parity_check.py")
parity = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(parity)

PRE_BUMP_FINGERPRINT = "7482697c458b6c1aa2a77829f2fbce0c4ce4ac9466e9a3583e97b9a799b5e483"
# Main before the 5c bump (design 5c stage B); that bump record's "from" side.
PRE_BUMP_REVISION = "520903802a5cb89e368af60f68e53f232c99046d"
# The goldens are recorded at this implementation (re-recorded after the 2026-10-07 keyhole-regime
# bump d92d1a3a -> cda80143, on top of the balling-screen bump), and GOLDEN_REVISION is a commit carrying it
# (the re-pin commit c2e4c63d of research/in625-regime-threshold): the "from" side of the next bump. in625-regime
# (2026-10-11, ec7e1f7a -> 0d52d7f7) re-recorded all goldens: only 7 G11/G18 thermal-dict digests changed (regime label/basis
# text, IN625 note and grid labels, new regimeKeyholeThreshold), the rest recording metadata. Before that, la6-gusarov
# (2026-10-08, cda80143 -> ec7e1f7a; first pinned 5f9d651e, then the exported provenance title was fixed) re-recorded all goldens: 97 text/digest observations (plus G3 stripe crossSectionArea 6400 -> 2698.01);
# previously only G11 and G18
# (label/basis text of the thermal dicts) changed.
# P1 sourced-physics bump (2026-10-11, 0d52d7f7 -> c61ab6a8, re-pin commit a486ac08 of feat/p1-sourced-physics)
# re-recorded all goldens: 10 G11/G18 observations changed numerically (Rosenthal field power A P with no ramp and no
# latent factor, depth = max(d_iso, Fabbro leg), effectiveAbsorptivity flat for Eagar-Tsai and Goldak), the rest
# recording metadata.
# P1 follow-on (2026-10-11, c61ab6a8 -> 7870aae6, re-pin commit 6de85dd5): additive process-map cell keys
# keyholeIndexLackOfFusion / lackOfFusionNote; content drift in the 7 G11/G18 digest keys, the rest recording metadata.
GOLDEN_FINGERPRINT = "7870aae64cf0b6c4aa5459d9e7f6f6a6bcea5822a1d1068e0d7f44d264c48ede"
GOLDEN_REVISION = "6de85dd50276987a80cfd162f5840ef3347dc7f7"
SLOW = os.environ.get("LPBF_PARITY_SLOW") == "1"
# Off the reference machine every case test is skipped (the goldens are bit-exact for one
# environment). METALLIKSA_REQUIRE_PARITY=1 turns such a "NOT VERIFIED" skip into a failure,
# so a gate run that is meant to be the reference proof cannot pass on skips.
REQUIRE_PARITY = os.environ.get("METALLIKSA_REQUIRE_PARITY") == "1"


def skip_or_fail(test, reason):
    if REQUIRE_PARITY:
        test.fail(f"METALLIKSA_REQUIRE_PARITY=1 and not verified: {reason}")
    test.skipTest(reason)


class ParityGoldenCaseTests(unittest.TestCase):
    """One test per golden case; all observations must be bit-equal."""


def _case_test(case):
    def test(self):
        if case.slow and not SLOW:
            self.skipTest("slow case: set LPBF_PARITY_SLOW=1 (G2 bare plate, ~106-140 s)")
        outcome = parity.check_case(case, parity.DEFAULT_WORK_ROOT)
        if outcome["skipped"] is not None:
            skip_or_fail(self, f"NOT VERIFIED: {outcome['skipped']}")
        self.assertEqual(outcome["problems"], [], f"{case.id} differs from its golden")
    test.__doc__ = f"{case.group}: {case.description}"
    return test


for _case in parity.CASES:
    setattr(ParityGoldenCaseTests, f"test_{_case.id}", _case_test(_case))


class ParityHarnessTests(unittest.TestCase):
    def setUp(self):
        self.root = HERE / ".tmp-lpbf-parity-mutation"
        self.root.mkdir(exist_ok=True)
        self.addCleanup(shutil.rmtree, self.root, True)

    def test_every_case_has_a_twice_recorded_pre_bump_golden(self):
        for case in parity.CASES:
            with self.subTest(case=case.id):
                golden = json.loads(parity.golden_path(case).read_text(encoding="utf-8"))
                self.assertEqual(golden["schema"], parity.GOLDEN_SCHEMA)
                self.assertEqual(golden["case"], case.id)
                self.assertEqual(golden["recordedImplementationHash"], GOLDEN_FINGERPRINT)
                self.assertEqual(golden["recordedVersion"], "enthalpy-fv-6")
                self.assertTrue(golden["recordedTwice"])
                self.assertGreater(len(golden["observations"]), 0)
        self.assertEqual(sorted(p.stem for p in parity.GOLDEN_DIR.glob("*.json")),
                         sorted(case.id for case in parity.CASES))

    def test_v1_and_bare_plate_goldens_carry_the_bound_identities(self):
        v1 = json.loads(parity.golden_path(parity.CASE_BY_ID["g1_v1_60w_in718"]).read_text(encoding="utf-8"))
        observations = v1["observations"]
        self.assertEqual(observations["result.coreContract.inputSha256"], parity.V1_INPUT_SHA256)
        self.assertTrue(observations["result.coreContract.materialSha256"].startswith("6a8d7bde"))
        self.assertTrue(observations["result.material.materialRevisionSha256"].startswith("5c9179e9"))
        self.assertEqual(observations["result.validationStatus"], "unvalidated")
        self.assertIs(observations["result.productionReady"], False)
        # Corrected-physics bump: only analyticalComparison.goldak differs from the archived V1 run.
        self.assertIs(observations["v1Archive.strippedResultEqual"], False)
        self.assertNotEqual(observations["result.canonicalSha256"], parity.V1_ARCHIVED_RESULT_STRIPPED_SHA256)
        # Wave B (2026-10-07): LA-3 (keyhole risk null + King mode indicator) and the LT-3 top-level
        # solidificationResolution label move the stripped digest 6a5e59be... -> ff428b93...; the V1
        # metrics, numericalDiagnostics, artifacts and identity digests are bit-equal.
        # Balling screen (2026-10-07, f3ba9896 -> d92d1a3a): geometricDefectScreen.balling carries no risk
        # without the Eagar-Tsai L/W ("low" -> null, new reason) and moves it ff428b93... -> f9b41280...
        # la6-gusarov (2026-10-08, cda80143 -> ec7e1f7a): assumptions sentence + geometricDefectScreen modelId v2 and
        # balling sources/basis move it f9b41280... -> e37e76ab... (V1 scans at 0 deg: metrics bit-equal).
        self.assertEqual(observations["result.canonicalSha256"],
                         "e37e76ab061f62bb094f1092acc30cfa29bd2d3889653b6305fe9d083d4d7c53")
        self.assertEqual(observations["result.key.solidificationResolution"] is not None, True)
        self.assertEqual(observations["result.implementationHashOccurrencesAfterStrip"], 0)
        self.assertEqual(observations["result.artifactsImplementationHashOccurrences"], 0)
        bare = json.loads(parity.golden_path(
            parity.CASE_BY_ID["g2_bare_plate_100w_corridor"]).read_text(encoding="utf-8"))["observations"]
        self.assertIs(bare["fixture.strippedResultEqual"], True)
        self.assertIs(bare["fixture.npzBytesEqual"], True)
        self.assertEqual(bare["fixture.artifactsMismatched"], [])
        self.assertEqual(bare["fixture.fieldArtifactsCompared"], 67)
        self.assertEqual(bare["fixture.artifactsCompared"], 68)

    def test_b5_goldens_document_todays_material_values(self):
        # B5 step 2: these are the values the corrected-physics bump is expected to move.
        authority = {"g17_evaporation_ti6al4v": 8.9e6, "g17_evaporation_316l": 6.25e6,
                     "g17_evaporation_alsi10mg": 10.5e6}
        for case_id, value in authority.items():
            with self.subTest(case=case_id):
                observations = json.loads(parity.golden_path(parity.CASE_BY_ID[case_id]).read_text(
                    encoding="utf-8"))["observations"]
                self.assertGreater(observations["evaporation.inversionCalls"], 0)
                self.assertEqual(observations["evaporation.latentHeatVapUsed_J_kg"], [[value, value.hex()]])
                self.assertEqual(observations["evaporation.authorityLatentHeatVap_J_kg"], [value, value.hex()])
                self.assertIs(observations["evaporation.materialSnapshotHasLatentHeatVap"], False)
                self.assertIs(observations["evaporation.authorityProbe.resultCanonicalEqual"], True)
        in625 = json.loads(parity.golden_path(parity.CASE_BY_ID["g18_in625_latent_heat"]).read_text(
            encoding="utf-8"))["observations"]
        self.assertEqual([in625[f"meltpool.in625.equalWithLatentHeatFusion.{v}"] for v in ("227000", "260000", "290000")],
                         [False, False, True])
        self.assertEqual(in625["in625.snapshot.latentHeat_J_kg"][0], 290000.0)
        self.assertEqual(in625["in625.transientSpecification.latentHeat_J_kg"][0], 227000.0)
        # Tier-2 bump (2026-10-06): peak-anchored extents; the reported peak stays T(0,0,0). Wave B
        # (2026-10-07, LA-2): T(0,0,0) is now the regularised point-source value, 2500.2 -> 35097.0 C
        # (labelled peakTemperatureBasis), and the extents grow (144.7/104.2/755.3/33.2 before). P1 bump
        # (2026-10-11): field power A P (no multi-reflection ramp, no latent factor) and depth = max(d_iso, Fabbro
        # leg): 154.9/110.4/804.9/35.2 -> 119.3/57.9/490.3/0.0 um, peak 35097.0 -> 21250.8 C.
        g11 = json.loads(parity.golden_path(parity.CASE_BY_ID["g11_build_job_meltpool"]).read_text(
            encoding="utf-8"))["rawValues"]
        self.assertEqual(g11["meltpool.0.geometry_um"], [119.3, 57.9, 490.3, 0.0])
        self.assertEqual(g11["meltpool.0.peakTemperature_C"], 21250.8)
        emissivity = json.loads(parity.golden_path(parity.CASE_BY_ID["g19_emissivity_echo"]).read_text(
            encoding="utf-8"))["observations"]
        for name in ("Ti-6Al-4V", "316L Stainless Steel", "AlSi10Mg", "Inconel 718"):
            self.assertEqual(emissivity[f"validate.{name}.emissivity"], [[0.35, (0.35).hex()]] * 2)
        self.assertEqual(emissivity["run.override0.36"], {"error": "ValueError: LPBF material revision identity mismatch"})
        self.assertIs(emissivity["explicit0.35.canonicalEqualsImplicit"], True)

    def test_evaporation_wrapper_records_an_unknown_call_shape_as_a_note(self):
        note = "unrecognised call shape: 4 positional, keywords ['l_vap']"
        self.assertEqual(parity._distinct([6.4e6, note, 6.4e6]), [[6.4e6, (6.4e6).hex()], note])
        self.assertEqual(parity._maximum([0.5, 0.25]), [0.5, (0.5).hex()])
        self.assertEqual(parity._maximum([0.5, note]), [note])
        self.assertEqual(parity._maximum([]), None)

    def _mutated_golden_dir(self, case_id, mutate):
        directory = Path(tempfile.mkdtemp(dir=self.root))
        for path in parity.GOLDEN_DIR.glob("*.json"):
            shutil.copy2(path, directory / path.name)
        target = directory / f"{case_id}.json"
        golden = json.loads(target.read_text(encoding="utf-8"))
        mutate(golden["observations"])
        target.write_text(json.dumps(golden), encoding="utf-8")
        return directory

    def test_one_changed_golden_digest_character_fails_the_check(self):
        def flip(observations):
            key = "eagarTsai.temperature"
            value = observations[key]
            observations[key] = ("0" if value[0] != "0" else "1") + value[1:]
        directory = self._mutated_golden_dir("g12_analytical_modules", flip)
        with patch.object(parity, "GOLDEN_DIR", directory):
            outcome = parity.check_case(parity.CASE_BY_ID["g12_analytical_modules"], self.root)
        self.assertEqual(len(outcome["problems"]), 1)
        self.assertIn("changed eagarTsai.temperature", outcome["problems"][0])

    def test_removed_golden_observation_fails_the_check(self):
        directory = self._mutated_golden_dir("npz_determinism",
                                             lambda observations: observations.pop("npz.resaveTwiceEqual"))
        with patch.object(parity, "GOLDEN_DIR", directory):
            outcome = parity.check_case(parity.CASE_BY_ID["npz_determinism"], self.root)
        self.assertEqual(outcome["problems"], ["unexpected new observation npz.resaveTwiceEqual"])

    def test_a_few_ulp_material_change_fails_a_solver_case(self):
        # Zero tolerance: absorptivity 0.38 -> 0.38 + 1e-15 (about 18 ulp) must move the
        # transient result. (SOURCE_QUADRATURE_RELATIVE_TOLERANCE cannot serve as the
        # mutation here: the CPU scheduler keeps beam travel per step <= 0.25 radius, so
        # integrated_source never reaches its refinement branch in a CPU transient; G13 covers
        # that branch directly, see the next test.)
        import four_alloy_materials
        in718 = four_alloy_materials._THERMAL["in718"]
        with patch.dict(in718, {"absorptivity_IR": in718["absorptivity_IR"] + 1e-15}):
            outcome = parity.check_case(parity.CASE_BY_ID["g3_powder_island"], self.root)
        problems = "\n".join(outcome["problems"])
        self.assertIn("changed result.canonicalSha256", problems)
        self.assertIn("changed result.key.metrics", problems)

    def test_changed_source_quadrature_tolerance_fails_the_refinement_case(self):
        # G13 drives integrated_source into its N-vs-2N branch directly; a tighter
        # convergence tolerance adds a refinement level and must change the pinned field.
        import lpbf_core_physics
        case = parity.CASE_BY_ID["g13_source_quadrature_refinement"]
        self.assertEqual(parity.check_case(case, self.root)["problems"], [])
        with patch.object(lpbf_core_physics, "SOURCE_QUADRATURE_RELATIVE_TOLERANCE", 1e-12):
            outcome = parity.check_case(case, self.root)
        problems = "\n".join(outcome["problems"])
        self.assertIn("changed integratedSource.dt2.500e-04.orders", problems)
        self.assertIn("changed integratedSource.dt2.500e-04:", problems)

    def test_changed_numerical_tolerance_in_the_scheduler_fails_a_solver_case(self):
        # The source-limited step accepts dt when allowed >= dt*(1-1e-12); a different
        # sensible-increment cap (25 K -> 24.999999 K) is a tolerance change that must show.
        import lpbf_heat_source
        import lpbf_simulation
        original = lpbf_heat_source.source_limited_step

        def tighter(*args, **kwargs):
            args = list(args)
            args[11] = args[11] * (24.999999 / 25.0)  # capacity scales the 25 K increment cap
            return original(*args, **kwargs)

        with patch.object(lpbf_simulation, "source_limited_step", tighter):
            outcome = parity.check_case(parity.CASE_BY_ID["g3_powder_island"], self.root)
        self.assertTrue(any(p.startswith("changed result.canonicalSha256") for p in outcome["problems"]),
                        outcome["problems"])

    def test_changed_material_value_fails_the_material_golden(self):
        import four_alloy_materials
        in718 = four_alloy_materials._THERMAL["in718"]
        with patch.dict(in718, {"liquidus_C": in718["liquidus_C"] + 1e-9}):
            outcome = parity.check_case(parity.CASE_BY_ID["g9_material_snapshots"], self.root)
        problems = "\n".join(outcome["problems"])
        self.assertIn("changed registry.material.Inconel 718", problems)
        self.assertIn("changed fam.canonical_material_source.in718.sha256", problems)

    def test_unpinned_implementation_fails_the_check(self):
        with patch.object(parity, "pinned_fingerprint", return_value="0" * 64):
            outcome = parity.check_case(parity.CASE_BY_ID["g12_analytical_modules"], self.root)
        self.assertTrue(any("!= pinned" in p for p in outcome["problems"]), outcome["problems"])

    def test_hash_only_bump_changes_no_result_or_artifact(self):
        # Simulated bump: a different implementation_fingerprint() (and pin) with identical
        # numerics must leave every observation of the solver cases bit-equal, so the
        # fingerprint is carried only by provenance.implementationHash.
        import lpbf_simulation
        fake = "f" * 64
        with patch.object(lpbf_simulation, "implementation_fingerprint", return_value=fake), \
                patch.object(parity, "pinned_fingerprint", return_value=fake):
            for case_id in ("g1_v1_60w_in718", "g3_powder_stripe_multilayer", "g4_layered_plate",
                            "g8_observers"):
                with self.subTest(case=case_id):
                    outcome = parity.check_case(parity.CASE_BY_ID[case_id], self.root, allow_environment_mismatch=True)
                    self.assertEqual(outcome["problems"], [])
                    self.assertEqual(outcome["implementationHashes"], [fake])

    def test_expect_unpinned_turns_only_the_pin_mismatch_into_a_warning(self):
        import lpbf_simulation
        moved = "e" * 64
        case = parity.CASE_BY_ID["g3_powder_island"]
        with patch.object(lpbf_simulation, "implementation_fingerprint", return_value=moved):
            strict = parity.check_case(case, self.root)
            bump = parity.check_case(case, self.root, expect_unpinned=True)
        self.assertTrue(any("!= pinned" in p for p in strict["problems"]), strict["problems"])
        self.assertEqual(bump["problems"], [])
        self.assertTrue(any("!= pinned" in w for w in bump["warnings"]), bump["warnings"])
        # A stale result hash and observation diffs stay failures in bump-branch mode.
        problems, _ = parity.check_implementation(case, ["a" * 64], parity.pinned_fingerprint(), moved,
                                                  expect_unpinned=True)
        self.assertTrue(any("provenance.implementationHash" in p for p in problems), problems)
        directory = self._mutated_golden_dir(
            "g12_analytical_modules", lambda observations: observations.update({"fabbro.depth": "0" * 64}))
        with patch.object(parity, "GOLDEN_DIR", directory), \
                patch.object(lpbf_simulation, "implementation_fingerprint", return_value=moved):
            outcome = parity.check_case(parity.CASE_BY_ID["g12_analytical_modules"], self.root,
                                        expect_unpinned=True)
        self.assertEqual(len(outcome["problems"]), 1)
        self.assertIn("changed fabbro.depth", outcome["problems"][0])

    def test_goldens_record_the_full_reference_environment(self):
        for case in parity.CASES:
            with self.subTest(case=case.id):
                recorded = json.loads(parity.golden_path(case).read_text(encoding="utf-8"))["recordedEnvironment"]
                self.assertEqual(set(recorded), {"python", "numpy", "platform", "runtime", "cpu", "numpyRuntime"})
                self.assertIn("simdFound", recorded["numpyRuntime"])
                self.assertIn("blas", recorded["numpyRuntime"])

    def test_other_environment_is_skipped_not_passed_unless_overridden(self):
        case = parity.CASE_BY_ID["g12_analytical_modules"]
        other = dict(parity.environment(), cpu="Some Other CPU")
        with patch.object(parity, "environment", return_value=other):
            skipped = parity.check_case(case, self.root)
            self.assertIn("environment differs from the recording in cpu", skipped["skipped"])
            self.assertEqual(skipped["observations"], {})
            self.assertEqual(parity.main(["--check", "--case", case.id, "--work-root", str(self.root)]), 3)
            compared = parity.check_case(case, self.root, allow_environment_mismatch=True)
        self.assertIsNone(compared["skipped"])
        self.assertEqual(compared["problems"], [])
        self.assertTrue(any("compared despite" in w for w in compared["warnings"]))

    def test_g11_g18_run_with_gpu_modules_blocked_when_warp_is_importable(self):
        # Since the tier-2 bump the melt-pool kernels touch the GPU modules only on explicit request, so
        # G11/G18 are no longer skipped on warp hosts: they run with the GPU modules blocked.
        import importlib
        import importlib.util
        original = importlib.util.find_spec

        def find_spec(name, *args, **kwargs):
            return object() if name == "warp" else original(name, *args, **kwargs)

        with patch.object(importlib.util, "find_spec", find_spec):
            for case_id in ("g11_build_job_meltpool", "g18_in625_latent_heat"):
                outcome = parity.check_case(parity.CASE_BY_ID[case_id], self.root, allow_environment_mismatch=True)
                self.assertIsNone(outcome["skipped"], case_id)
        for name in parity._GPU_MELTPOOL_MODULES:
            with self.assertRaises(ImportError):
                parity._cpu_meltpool_only(lambda name=name: importlib.import_module(name))
        with self.assertRaisesRegex(ValueError, "must not request the GPU melt-pool path"):
            parity._require_cpu_meltpool_payloads([{"absorption_model": "powder-raytrace"}])
        with self.assertRaisesRegex(ValueError, "must not request the GPU melt-pool path"):
            parity._require_cpu_meltpool_payloads([{"thermal_slice_backend": "warp"}])

    def test_g2_fixture_comparison_ignores_only_the_named_post_capture_labels(self):
        # Wave B LT-3 added a top-level label after the bare-plate fixture was captured; the fixture
        # comparison may drop exactly that name (when the fixture lacks it) and nothing else.
        self.assertEqual(parity.FIXTURE_POST_CAPTURE_LABEL_KEYS, ("solidificationResolution",))
        _capture, reference = parity._fixture()
        for key in parity.FIXTURE_POST_CAPTURE_LABEL_KEYS:
            self.assertNotIn(key, reference)
        for numeric in ("metrics", "numericalDiagnostics", "thermalHistory", "energyBalance", "discretization"):
            self.assertNotIn(numeric, parity.FIXTURE_POST_CAPTURE_LABEL_KEYS)

    def test_cfd_case_module_falls_back_only_when_lpbf_cfd_cases_itself_is_missing(self):
        import sys
        with patch.dict(sys.modules, {"lpbf_cfd_cases": None}):
            self.assertEqual(parity._cfd_case_module().__name__, "lpbf_cfd")
        directory = Path(tempfile.mkdtemp(dir=self.root))
        (directory / "lpbf_cfd_cases.py").write_text("import lpbf_missing_dependency_for_test\n",
                                                     encoding="utf-8")
        sys.modules.pop("lpbf_cfd_cases", None)
        with patch.object(sys, "path", [str(directory), *sys.path]):
            with self.assertRaises(ModuleNotFoundError) as raised:
                parity._cfd_case_module()
        sys.modules.pop("lpbf_cfd_cases", None)
        self.assertEqual(raised.exception.name, "lpbf_missing_dependency_for_test")

    def test_bump_record_refuses_same_hash_and_foreign_goldens(self):
        # The goldens are recorded at GOLDEN_FINGERPRINT, the current pin, so they are the
        # "from" side of the NEXT bump: skeleton mode (worktree as "from") accepts them, a
        # record from the older PRE_BUMP_REVISION refuses them, and a record from
        # GOLDEN_REVISION refuses the unchanged fingerprint unless it is a dry run.
        spec = importlib.util.spec_from_file_location("lpbf_bump_record", HERE / "tools" / "lpbf_bump_record.py")
        bump = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bump)
        try:
            before = bump.revision_side(PRE_BUMP_REVISION)
            recorded = bump.revision_side(GOLDEN_REVISION)
        except subprocess.CalledProcessError:
            skip_or_fail(self, f"revision {PRE_BUMP_REVISION[:12]} or {GOLDEN_REVISION[:12]} is not in this clone")
        self.assertEqual(before["implementationHash"], PRE_BUMP_FINGERPRINT)
        self.assertEqual(before["manifestCount"], 37)
        self.assertEqual(recorded["implementationHash"], GOLDEN_FINGERPRINT)
        self.assertEqual(recorded["manifestCount"], 36)
        skeleton = bump.build_record(None, False, False)
        self.assertEqual(skeleton["fromHash"], GOLDEN_FINGERPRINT)
        self.assertIsNone(skeleton["toHash"])
        with self.assertRaisesRegex(SystemExit, "goldens not recorded at fromHash"):
            bump.build_record(PRE_BUMP_REVISION, False, False)
        with self.assertRaisesRegex(SystemExit, "toHash equals fromHash"):
            bump.build_record(GOLDEN_REVISION, False, False)
        dry = bump.build_record(GOLDEN_REVISION, False, False, allow_same_hash=True)
        self.assertTrue(dry["dryRunSameHash"])
        self.assertEqual(dry["fromHash"], GOLDEN_FINGERPRINT)
        directory = self._mutated_golden_dir("npz_determinism", lambda observations: None)
        target = directory / "npz_determinism.json"
        golden = json.loads(target.read_text(encoding="utf-8"))
        golden["recordedImplementationHash"] = "b" * 64
        target.write_text(json.dumps(golden), encoding="utf-8")
        with patch.object(bump, "GOLDEN_DIR", directory):
            with self.assertRaisesRegex(SystemExit, "goldens not recorded at fromHash"):
                bump.build_record(GOLDEN_REVISION, False, False, allow_same_hash=True)

    def _check(self, *args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = parity.main(["--check", "--work-root", str(self.root), *args])
        return code, output.getvalue()

    def _synthetic_drift_dir(self):
        # Synthetic drift fixture: the G18 golden says the melt-pool table holds 250 kJ/kg and
        # the G12 goldens are untouched, so only G18 differs from the current implementation.
        def mutate(observations):
            observations["meltpool.in625.table.latent_heat_fusion_J_kg"] = [250000.0, (250000.0).hex()]
        return self._mutated_golden_dir("g18_in625_latent_heat", mutate)

    def test_expect_drift_allows_only_the_named_case_and_reports_hex_values(self):
        cases = ["--case", "g18_in625_latent_heat", "--case", "g12_analytical_modules"]
        with patch.object(parity, "GOLDEN_DIR", self._synthetic_drift_dir()):
            code, output = self._check(*cases)
            self.assertEqual(code, 1, output)  # unlisted drift fails
            self.assertIn("FAIL g18_in625_latent_heat", output)
            code, output = self._check(*cases, "--expect-drift", "g18_in625_latent_heat")
            self.assertEqual(code, 0, output)
            self.assertIn("DRIFT g18_in625_latent_heat", output)
            self.assertIn("PASS g12_analytical_modules", output)
            self.assertIn("DRIFT meltpool.in625.table.latent_heat_fusion_J_kg: 250000.0 (0x1.e848000000000p+17)"
                          " -> 290000.0 (0x1.1b34000000000p+18)", output)
            self.assertIn("RESULT: PASS (planned drift in g18_in625_latent_heat)", output)

    def test_expect_drift_with_a_wrong_allowlist_fails(self):
        cases = ["--case", "g18_in625_latent_heat", "--case", "g12_analytical_modules"]
        with patch.object(parity, "GOLDEN_DIR", self._synthetic_drift_dir()):
            # Wrong case named: the real drift is unlisted AND the named case is stale.
            code, output = self._check(*cases, "--expect-drift", "g12_analytical_modules")
            self.assertEqual(code, 1, output)
            self.assertIn("FAIL g18_in625_latent_heat", output)
            self.assertIn("FAIL g12_analytical_modules", output)
            self.assertIn("stale --expect-drift entry", output)
            # Right case plus a stale extra one still fails.
            code, output = self._check(*cases, "--expect-drift", "g18_in625_latent_heat,g12_analytical_modules")
            self.assertEqual(code, 1, output)
            self.assertIn("DRIFT g18_in625_latent_heat", output)
            self.assertIn("RESULT: FAIL (1 case(s))", output)
            # A named case that is not selected cannot prove its drift.
            code, output = self._check("--case", "g18_in625_latent_heat",
                                       "--expect-drift", "g18_in625_latent_heat,g12_analytical_modules")
            self.assertEqual(code, 1, output)
            self.assertIn("FAIL g12_analytical_modules: named in --expect-drift but not selected", output)
        # Without any drift the allowlist is stale.
        code, output = self._check("--case", "g12_analytical_modules", "--expect-drift", "g12_analytical_modules")
        self.assertEqual(code, 1, output)
        self.assertIn("stale --expect-drift entry", output)
        with self.assertRaisesRegex(SystemExit, "unknown case"):
            self._check("--case", "g12_analytical_modules", "--expect-drift", "g99_missing")
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            parity.main(["--record", "--case", "g12_analytical_modules", "--expect-drift", "g12_analytical_modules"])

    def test_expect_drift_still_fails_on_pin_and_hash_problems(self):
        with patch.object(parity, "GOLDEN_DIR", self._synthetic_drift_dir()), \
                patch.object(parity, "pinned_fingerprint", return_value="0" * 64):
            code, output = self._check("--case", "g18_in625_latent_heat", "--expect-drift", "g18_in625_latent_heat")
        self.assertEqual(code, 1, output)
        self.assertIn("!= pinned", output)

    def test_expect_drift_on_a_runtime_material_change_in_a_solver_case(self):
        # Synthetic drift without editing manifest code: a few-ulp absorptivity change
        # (patched in memory, as in test_a_few_ulp_material_change_fails_a_solver_case).
        import four_alloy_materials
        in718 = four_alloy_materials._THERMAL["in718"]
        with patch.dict(in718, {"absorptivity_IR": in718["absorptivity_IR"] + 1e-15}):
            code, output = self._check("--case", "g3_powder_island")
            self.assertEqual(code, 1, output)
            # The material identity moved too: naming the case alone is not enough.
            code, output = self._check("--case", "g3_powder_island", "--expect-drift", "g3_powder_island")
            self.assertEqual(code, 1, output)
            self.assertIn("identity observation", output)
            code, output = self._check(
                "--case", "g3_powder_island", "--expect-drift",
                "g3_powder_island,g3_powder_island:result.coreContract.materialSha256,"
                "g3_powder_island:result.coreContract.inputSha256,"
                "g3_powder_island:result.material.materialRevisionSha256")
        self.assertEqual(code, 0, output)
        self.assertIn("DRIFT g3_powder_island", output)
        self.assertIn("DRIFT result.canonicalSha256: sha256 ", output)

    def test_expect_drift_refuses_reference_cases_as_a_whole(self):
        for case_id in ("g1_v1_60w_in718", "g2_bare_plate_100w_corridor", "g4_layered_plate"):
            with self.subTest(case=case_id):
                with self.assertRaisesRegex(SystemExit, "reference transient case"):
                    parity.parse_expect_drift([case_id])
                self.assertEqual([e.text for e in parity.parse_expect_drift([f"{case_id}:result.key.metrics"])],
                                 [f"{case_id}:result.key.metrics"])
        with self.assertRaisesRegex(SystemExit, "empty case or key"):
            parity.parse_expect_drift(["g18_in625_latent_heat:"])

    def test_expect_drift_refuses_globs_for_reference_cases_but_accepts_exact_keys(self):
        # Review pb-r2 S5: g1/g2/g4 take exact observation keys only; CASE:* and every other
        # fnmatch pattern is refused at parse time, whatever the pattern looks like.
        for case_id in ("g1_v1_60w_in718", "g2_bare_plate_100w_corridor", "g4_layered_plate"):
            for pattern in ("*", "result.*", "result.key.?etrics", "result.key.[m]etrics", "*.key.settings"):
                with self.subTest(case=case_id, pattern=pattern):
                    with self.assertRaisesRegex(SystemExit, "glob character.*exact observation keys"):
                        parity.parse_expect_drift([f"{case_id}:{pattern}"])
            entries = parity.parse_expect_drift([f"{case_id}:result.key.analyticalComparison"])
            self.assertEqual([(e.case_id, e.pattern) for e in entries],
                             [(case_id, "result.key.analyticalComparison")])
        # Non-reference cases keep their globs (G6 sub-runs are named by exact key at the next bump).
        entries = parity.parse_expect_drift(["g6_screening_and_fallback:*.key.metrics", "g3_powder_island"])
        self.assertEqual([e.text for e in entries], ["g6_screening_and_fallback:*.key.metrics", "g3_powder_island"])

    @staticmethod
    def _synthetic_outcome(before, after):
        return {"golden": {"observations": before}, "observations": after, "problems": [],
                "implementationProblems": [], "observationDiffs": ["changed"], "rawValues": {}}

    def test_expect_drift_protects_reference_numerics_beyond_the_original_list(self):
        keys = ("peakInterpolatedMeltPool", "midTrackCrossSection", "midTrackInterpolatedCrossSection",
                "massBalance", "numericalDiagnostics", "phaseAudit", "settings", "discretization", "scanPath")
        for case_id in parity.REFERENCE_CASES:
            for name in keys:
                with self.subTest(case=case_id, key=name):
                    key = f"result.key.{name}"
                    case = parity.CASE_BY_ID[case_id]
                    # Even an exact entry for the key does not let a reference numeric drift.
                    entries = parity.parse_expect_drift([f"{case_id}:{key}"])
                    result = parity.evaluate_drift(case, self._synthetic_outcome({key: "0" * 64}, {key: "1" * 64}),
                                                   entries)
                    self.assertEqual(result["status"], "FAIL")
                    self.assertIn(f"changed {key}: reference-case numerics never drift under --expect-drift",
                                  result["problems"])
        # The same key in a NON-reference case is an ordinary allowed observation.
        case = parity.CASE_BY_ID["g3_powder_island"]
        entries = parity.parse_expect_drift(["g3_powder_island:result.key.settings"])
        result = parity.evaluate_drift(
            case, self._synthetic_outcome({"result.key.settings": "0" * 64}, {"result.key.settings": "1" * 64}), entries)
        self.assertEqual((result["status"], result["problems"]), ("DRIFT", []))

    def test_expect_drift_never_lets_an_honesty_observation_drift_in_any_case(self):
        names = ("validationStatus", "productionReady", "confidence", "effectiveMode")
        keys = [f"result.{name}" for name in names] + [f"result.key.{name}" for name in names]
        keys.append("result.coreContract.solverId")
        for case_id in ("g3_powder_island", "g5_evaporation", "g6_screening_and_fallback"):
            for key in keys:
                with self.subTest(case=case_id, key=key):
                    case = parity.CASE_BY_ID[case_id]
                    drifted = self._synthetic_outcome({key: "unvalidated", "other": 1}, {key: "validated", "other": 2})
                    for allow in (case_id, f"{case_id}:*", f"{case_id}:{key}"):
                        result = parity.evaluate_drift(case, drifted, parity.parse_expect_drift([allow]))
                        self.assertEqual(result["status"], "FAIL", allow)
                        self.assertIn(f"changed {key}: honesty observation never drifts under --expect-drift",
                                      result["problems"])
        # A changed validationStatus in a non-reference case stays refused even with CASE:*; the other
        # drifted observation in the same case is still reported as allowed.
        case = parity.CASE_BY_ID["g12_analytical_modules"]
        outcome = self._synthetic_outcome({"validationStatus": "unvalidated", "goldak.field": "0" * 64},
                                          {"validationStatus": "validated", "goldak.field": "1" * 64})
        result = parity.evaluate_drift(case, outcome, parity.parse_expect_drift(["g12_analytical_modules:*"]))
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("changed validationStatus: honesty observation never drifts under --expect-drift",
                      result["problems"])
        self.assertEqual([record["key"] for record in result["drift"]], ["goldak.field"])

    def test_expect_drift_refuses_the_widened_honesty_observations_in_any_case(self):
        # Review rr2 S2: the evidence-honesty flags (and the G9 IN625 admission verdict) are protected
        # like validationStatus: CASE, CASE:* and the exact CASE:<key> entry all fail, in every case.
        patterns = ("*.experimentalValidation", "*.key.experimentalValidation",
                    "*.experimentalComparison", "*.key.experimentalComparison",
                    "*.unresolvedPhysics", "*.key.unresolvedPhysics",
                    "*.opticalOperatorMatched", "*.key.opticalOperatorMatched",
                    "in625.validateScreeningAdmission",
                    "experimentalValidation", "experimentalComparison",
                    "unresolvedPhysics", "opticalOperatorMatched")
        for pattern in patterns:
            self.assertIn(pattern, parity.HONESTY_PATTERNS)
            # Concrete observation keys this pattern covers (fnmatch '*' also spans dots).
            keys = ([pattern] if "*" not in pattern else [pattern.replace("*", "result", 1), pattern.replace("*", "a.b", 1)])
            for key in keys:
                for case_id in ("g3_powder_island", "g9_material_snapshots", "g14_calibration_measurements",
                                "g15_bare_plate_square_optical_observer"):
                    with self.subTest(pattern=pattern, case=case_id, key=key):
                        case = parity.CASE_BY_ID[case_id]
                        drifted = self._synthetic_outcome({key: "0" * 64, "other": 1}, {key: "1" * 64, "other": 2})
                        for allow in (case_id, f"{case_id}:*", f"{case_id}:{key}"):
                            result = parity.evaluate_drift(case, drifted, parity.parse_expect_drift([allow]))
                            self.assertEqual(result["status"], "FAIL", allow)
                            self.assertIn(f"changed {key}: honesty observation never drifts under --expect-drift",
                                          result["problems"])
        # The patterns are exact names, not substrings: an unrelated observation that merely contains the
        # word stays an ordinary allowed observation.
        case = parity.CASE_BY_ID["g12_analytical_modules"]
        outcome = self._synthetic_outcome({"goldak.experimentalValidationNote": "0" * 64},
                                          {"goldak.experimentalValidationNote": "1" * 64})
        result = parity.evaluate_drift(case, outcome, parity.parse_expect_drift(["g12_analytical_modules:*"]))
        self.assertEqual((result["status"], result["problems"]), ("DRIFT", []))

    def test_checked_in_drift_allowlist_names_no_honesty_or_identity_observation(self):
        import fnmatch
        allowlist = HERE.parent / "docs" / "LPBF_IMPLEMENTATION_BUMP_2026-10-04_corrected-physics.expect-drift.txt"
        entries = [line.strip() for line in allowlist.read_text(encoding="utf-8").splitlines() if line.strip()]
        self.assertGreater(len(entries), 0)
        for entry in entries:
            case_id, separator, key = entry.partition(":")
            with self.subTest(entry=entry):
                self.assertTrue(separator and key, "every entry names CASE:KEY")
                self.assertIn(case_id, parity.CASE_BY_ID)
                for pattern in parity.HONESTY_PATTERNS:
                    self.assertFalse(fnmatch.fnmatchcase(key, pattern), f"{entry} matches honesty pattern {pattern}")
                for pattern in parity.IDENTITY_PATTERNS:
                    self.assertFalse(fnmatch.fnmatchcase(key, pattern), f"{entry} matches identity pattern {pattern}")

    def test_expect_drift_on_g1_allows_only_named_non_numeric_observations(self):
        def reviewer(observations):  # review b5g S1: result digest + material revision + V1 equality
            observations["result.canonicalSha256"] = "0" * 64
            observations["result.material.materialRevisionSha256"] = "1" * 64
            observations["v1Archive.strippedResultEqual"] = True
        g1 = ["--case", "g1_v1_60w_in718"]
        with patch.object(parity, "GOLDEN_DIR", self._mutated_golden_dir("g1_v1_60w_in718", reviewer)):
            code, output = self._check(*g1, "--expect-drift",
                                       "g1_v1_60w_in718:result.canonicalSha256,"
                                       "g1_v1_60w_in718:v1Archive.strippedResultEqual")
        self.assertEqual(code, 1, output)
        self.assertIn("changed result.material.materialRevisionSha256: identity observation", output)

        def planned(observations):  # the four G1 observations a corrected bump may name
            for key in ("result.key.analyticalComparison", "result.canonicalSha256", "result.orderedTypedSha256"):
                observations[key] = "0" * 64
            observations["v1Archive.strippedResultEqual"] = True
        allow = ("g1_v1_60w_in718:result.key.analyticalComparison,g1_v1_60w_in718:result.canonicalSha256,"
                 "g1_v1_60w_in718:result.orderedTypedSha256,g1_v1_60w_in718:v1Archive.strippedResultEqual")
        with patch.object(parity, "GOLDEN_DIR", self._mutated_golden_dir("g1_v1_60w_in718", planned)):
            code, output = self._check(*g1, "--expect-drift", allow)
        self.assertEqual(code, 0, output)
        self.assertIn("DRIFT g1_v1_60w_in718", output)
        self.assertIn("4 observation(s) drifted", output)

        def numerics(observations):
            observations["result.key.metrics"] = "0" * 64
        with patch.object(parity, "GOLDEN_DIR", self._mutated_golden_dir("g1_v1_60w_in718", numerics)):
            code, output = self._check(*g1, "--expect-drift", "g1_v1_60w_in718:result.key.metrics")
        self.assertEqual(code, 1, output)
        self.assertIn("reference-case numerics never drift", output)

    def test_expect_drift_identity_keys_need_the_exact_key_and_unlisted_keys_fail(self):
        def identity(observations):
            observations["result.coreContract.materialSha256"] = "2" * 64
        island = ["--case", "g3_powder_island"]
        with patch.object(parity, "GOLDEN_DIR", self._mutated_golden_dir("g3_powder_island", identity)):
            code, output = self._check(*island, "--expect-drift", "g3_powder_island")
            self.assertEqual(code, 1, output)
            self.assertIn("identity observation", output)
            code, output = self._check(*island, "--expect-drift", "g3_powder_island:result.coreContract.*")
            self.assertEqual(code, 1, output)
            code, output = self._check(*island, "--expect-drift",
                                       "g3_powder_island:result.coreContract.materialSha256")
            self.assertEqual(code, 0, output)

        def two(observations):
            observations["meltpool.in625.table.latent_heat_fusion_J_kg"] = [250000.0, (250000.0).hex()]
            observations["in625.snapshot.latentHeat_J_kg"] = [280000.0, (280000.0).hex()]
        with patch.object(parity, "GOLDEN_DIR", self._mutated_golden_dir("g18_in625_latent_heat", two)):
            code, output = self._check("--case", "g18_in625_latent_heat", "--expect-drift",
                                       "g18_in625_latent_heat:meltpool.in625.table.*")
        self.assertEqual(code, 1, output)
        self.assertIn("changed in625.snapshot.latentHeat_J_kg: not named by --expect-drift", output)
        self.assertNotIn("allowed by --expect-drift", output)

    def test_drift_report_prints_raw_before_and_after_values(self):
        case = parity.CASE_BY_ID["g12_analytical_modules"]
        parity.execute(case, self.root)
        raw = copy.deepcopy(parity.LAST_RAW_VALUES["goldak.field"])
        before = copy.deepcopy(raw)
        before["q"] = raw["q"] * 0.5

        def mutate(observations):
            observations["goldak.field"] = "0" * 64
        directory = self._mutated_golden_dir("g12_analytical_modules", mutate)
        target = directory / "g12_analytical_modules.json"
        golden = json.loads(target.read_text(encoding="utf-8"))
        golden["rawValues"] = {"goldak.field": before}
        target.write_text(json.dumps(golden), encoding="utf-8")
        with patch.object(parity, "GOLDEN_DIR", directory):
            code, output = self._check("--case", case.id, "--expect-drift", f"{case.id}:goldak.*")
        self.assertEqual(code, 0, output)
        self.assertIn(f"raw q: {before['q']!r} ({before['q'].hex()}) -> {raw['q']!r} ({raw['q'].hex()})", output)

    def test_expect_drift_fails_on_a_result_implementation_hash_mismatch(self):
        original = parity.result_observations

        def stale_hash(*args, **kwargs):
            observations, _ = original(*args, **kwargs)
            return observations, "a" * 64

        def mutate(observations):
            observations["result.key.metrics"] = "0" * 64
        with patch.object(parity, "GOLDEN_DIR", self._mutated_golden_dir("g3_powder_island", mutate)), \
                patch.object(parity, "result_observations", stale_hash):
            code, output = self._check("--case", "g3_powder_island", "--expect-drift", "g3_powder_island")
        self.assertEqual(code, 1, output)
        self.assertIn("result provenance.implementationHash " + "a" * 64, output)
        self.assertNotIn("allowed by --expect-drift", output)

    def test_expect_drift_wrong_schema_golden_has_no_stale_line(self):
        directory = self._mutated_golden_dir("g18_in625_latent_heat", lambda observations: None)
        target = directory / "g18_in625_latent_heat.json"
        golden = json.loads(target.read_text(encoding="utf-8"))
        golden["case"] = "something-else"
        target.write_text(json.dumps(golden), encoding="utf-8")
        with patch.object(parity, "GOLDEN_DIR", directory):
            code, output = self._check("--case", "g18_in625_latent_heat", "--expect-drift", "g18_in625_latent_heat")
        self.assertEqual(code, 1, output)
        self.assertIn("wrong schema or case id", output)
        self.assertNotIn("stale", output)

    def test_expect_drift_off_the_reference_environment_is_diagnostic_not_pass(self):
        other = dict(parity.environment(), cpu="Some Other CPU")
        with patch.object(parity, "GOLDEN_DIR", self._synthetic_drift_dir()), \
                patch.object(parity, "environment", return_value=other):
            code, output = self._check("--case", "g18_in625_latent_heat", "--allow-environment-mismatch",
                                       "--expect-drift", "g18_in625_latent_heat")
        self.assertEqual(code, 3, output)
        self.assertIn("RESULT: DIAGNOSTIC", output)

    def test_bump_record_parity_after_uses_the_same_drift_allowlist(self):
        spec = importlib.util.spec_from_file_location("lpbf_bump_record", HERE / "tools" / "lpbf_bump_record.py")
        bump = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bump)
        subset = (parity.CASE_BY_ID["g18_in625_latent_heat"], parity.CASE_BY_ID["g12_analytical_modules"])
        with patch.object(parity, "GOLDEN_DIR", self._synthetic_drift_dir()), \
                patch.object(parity, "CASES", subset), \
                patch.object(bump, "_parity_module", return_value=parity):
            strict = bump.parity_after(False)
            planned = bump.parity_after(False, ["g18_in625_latent_heat"])
            stale = bump.parity_after(False, ["g18_in625_latent_heat", "g12_analytical_modules"])
        self.assertEqual(strict["g18_in625_latent_heat"]["status"], "FAIL")
        self.assertEqual(planned["g18_in625_latent_heat"]["status"], "DRIFT")
        self.assertEqual(planned["g12_analytical_modules"]["status"], "PASS")
        record = planned["g18_in625_latent_heat"]["drift"][0]
        self.assertEqual(record["key"], "meltpool.in625.table.latent_heat_fusion_J_kg")
        self.assertEqual(record["before"], [250000.0, (250000.0).hex()])
        self.assertEqual(record["after"], [290000.0, (290000.0).hex()])
        self.assertEqual(stale["g12_analytical_modules"]["status"], "FAIL")

    def test_require_parity_turns_a_not_verified_skip_into_a_failure(self):
        module = sys.modules[__name__]
        with patch.object(module, "REQUIRE_PARITY", True):
            with self.assertRaises(self.failureException):
                skip_or_fail(self, "NOT VERIFIED: environment differs")
        with patch.object(module, "REQUIRE_PARITY", False):
            with self.assertRaises(unittest.SkipTest):
                skip_or_fail(self, "NOT VERIFIED: environment differs")

    def test_record_refuses_an_unpinned_implementation(self):
        with patch.object(parity, "pinned_fingerprint", return_value="0" * 64):
            self.assertEqual(parity.main(["--record", "--case", "npz_determinism",
                                          "--work-root", str(self.root)]), 2)

    def test_strip_result_removes_only_volatile_and_worker_fields(self):
        result = {"runtime_s": 1.0, "runKind": "transient-thermal", "metrics": {"peak": 1.5},
                  "provenance": {"createdAt": "t", "runtime_s": 2.0, "executionRuntime": {"python": "x"},
                                 "implementationHash": "h", "inputHash": "i"},
                  "artifacts": [{"path": "input.json"}, {"path": "capabilities.json"},
                                {"path": "field-series.json", "sha256": "s"}]}
        original = copy.deepcopy(result)
        stripped, implementation = parity.strip_result(result)
        self.assertEqual(result, original)
        self.assertEqual(implementation, "h")
        self.assertEqual(stripped, {"metrics": {"peak": 1.5}, "provenance": {"inputHash": "i"},
                                    "artifacts": [{"path": "field-series.json", "sha256": "s"}]})

    def test_typed_digest_pins_order_and_types_that_canonical_json_ignores(self):
        pairs = (({"a": 1, "b": 2}, {"b": 2, "a": 1}), ({"x": 1}, {"x": 1.0}),
                 ({"x": (1, 2)}, {"x": [1, 2]}), ({"x": 0.0}, {"x": -0.0}))
        for left, right in pairs:
            with self.subTest(left=left, right=right):
                self.assertNotEqual(parity.typed_sha256(left), parity.typed_sha256(right))
        self.assertEqual(parity.canonical_json_sha256({"a": 1, "b": 2}),
                         parity.canonical_json_sha256({"b": 2, "a": 1}))


if __name__ == "__main__":
    unittest.main()
