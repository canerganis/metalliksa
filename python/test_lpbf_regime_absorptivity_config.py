"""Pins the stage-0 freeze of the regime-dependent absorptivity evaluation (config hash, pre-registration hash, roles).

Self-contained: expected hashes and roles are written here. SCREENING ONLY, NOT VALIDATION."""

import hashlib
import sys
import unittest
from pathlib import Path

PYTHON_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PYTHON_DIR))

import lpbf_regime_absorptivity_config as C  # noqa: E402
import lpbf_simulation  # noqa: E402

REPO_ROOT = PYTHON_DIR.parent
CONFIG_SHA256 = "8d629929370d8fdf2f60a3d4de72f3ccc77290c0eee58cc5ad8f230edaba91f9"
PREREG_LF_SHA256 = "ccc365f120cbe29c98997aa6b1d9d3e3eeb795359ab9631ac534100e112d76f4"
FINGERPRINT = "ec7e1f7a6606e937e448fefe97549b49a7ddfe7b95376b93867ae007b0c12555"


class RegimeAbsorptivityConfigFreeze(unittest.TestCase):
    def test_config_hash_pin(self):
        self.assertEqual(C.config_sha256(), CONFIG_SHA256,
                         "the config is pre-registered: a change needs a recorded deviation, not an edit")
        self.assertEqual(C.CONFIG["version"], "lpbf-regime-absorptivity-config-2")

    def test_points_to_amendment_1_and_its_file_hash(self):
        self.assertEqual(C.CONFIG["preregistration"]["commit"][:8], "fe30687d")
        self.assertEqual(C.CONFIG["preregistration"]["sha256Lf"], PREREG_LF_SHA256)
        doc = (REPO_ROOT / C.PREREGISTRATION_DOC).read_bytes().replace(b"\r\n", b"\n")
        self.assertEqual(hashlib.sha256(doc).hexdigest(), PREREG_LF_SHA256,
                         "the pre-registration file changed after Amendment 1")

    def test_frozen_fingerprint_unchanged_and_modules_outside_manifest(self):
        self.assertEqual(C.FROZEN_FINGERPRINT, FINGERPRINT)
        # The declared run was made at FINGERPRINT. Later planned bumps (in625-regime, 2026-10-11) move the
        # implementation; the runner then refuses to run instead of producing results at another fingerprint.
        if lpbf_simulation.implementation_fingerprint() != FINGERPRINT:
            src = (REPO_ROOT / "python" / "tools" / "lpbf_regime_absorptivity_eval.py").read_text(encoding="utf-8")
            self.assertIn("if fp != C.FROZEN_FINGERPRINT:", src)
        for name in ("lpbf_regime_absorptivity_config.py", "lpbf_regime_absorptivity_kernel.py",
                     "tools/lpbf_regime_absorptivity_eval.py"):
            self.assertNotIn(name, lpbf_simulation.IMPLEMENTATION_SOURCE_FILES)

    def test_labels_are_not_promoted(self):
        lab = C.CONFIG["labels"]
        self.assertFalse(lab["experimentalValidation"])
        self.assertEqual(lab["validationStatus"], "unvalidated")
        self.assertFalse(lab["productionReady"])

    def test_amendment_roles(self):
        roles = C.CONFIG["dataRoles"]
        self.assertEqual(roles["testOnly"], ["ghosh-in625-2018"])
        self.assertEqual(set(roles["diagnosticOnly"]), {"trapp-316l-2017", "cunningham-ti64-2019"})
        self.assertFalse(set(roles["diagnosticOnly"]) & set(roles["meltPoolSources"]))
        self.assertEqual(set(roles["heldOutPartlyExposed"]), {"hofmann-316l-2026", "totis-ti64-2021"})
        self.assertNotIn("iii", C.CONFIG["metrics"]["regime"]["labelSets"])
        man = C.CONFIG["sourceManifest"]["sources"]
        self.assertFalse(man["ku-leuven-316l-2021"]["gate"]["width"])
        self.assertFalse(man["ku-leuven-ti64-2021"]["gate"]["width"])
        self.assertFalse(man["totis-ti64-2021"]["gate"]["width"])
        self.assertEqual(C.CONFIG["sourceManifest"]["totisWidthStage0"]["outcome"], "unconfirmed")
        for sid in ("trapp-316l-2017", "cunningham-ti64-2019"):
            self.assertEqual(man[sid]["gate"], {"depth": False, "width": False})

    def test_law_parameters_and_arm_g_label(self):
        law = C.CONFIG["law"]
        self.assertEqual((law["H_on"], law["A_kh"], law["H_s"]), (15.0, 0.70, 5.0))
        self.assertIn("adapted", C.CONFIG["arms"]["G"]["label"])
        self.assertEqual(C.CONFIG["metrics"]["intervalScore"], {"alpha": 0.10, "margin": 1.05,
                                                                "reference": "Gneiting and Raftery 2007"})
        self.assertEqual(C.CONFIG["nuisance"]["gridSize"], {"laneInactive": 8, "laneActive": 16})


if __name__ == "__main__":
    unittest.main()
