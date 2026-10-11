"""
test_phase8_microstructure_contract.py: Phase 8 microstructure contract, unittest (no pytest needed).

Moved from test_phase8.py (pytest-only; the locked LPBF interpreter has no pytest):
  - compute_solidification_microstructure() without CFD data returns "unavailable" (exact reason, no numbers).
  - compute_solidification_microstructure() with a mock CFD result (OpenFOAM path) is "available".
Run: python -B -m unittest test_phase8_microstructure_contract
"""
import unittest

from lpbf_solidification_microstructure import compute_solidification_microstructure


class Phase8MicrostructureContractTest(unittest.TestCase):

    def test_solidification_microstructure_unavailable_without_cfd(self):
        """Without CFD data no default-constant estimate is returned."""
        params = {
            "power_W": 285.0,
            "speed_mm_s": 960.0,
        }
        material = {
            "absorptivity": 0.35,
            "k_WmK": 15.0,
            "liquidus_K": 1700.0,
        }
        expected_reason = (
            "no CFD solidification data (solidificationMicrostructure.meanG_K_m); "
            "G and R are not estimated from default constants"
        )
        for cfd in (None, {}, {"solidificationMicrostructure": {}}):
            result = compute_solidification_microstructure(params, material, cfd)

            assert result["status"] == "unavailable"
            assert result["source"] == "none"
            assert result["reason"] == expected_reason
            for key in ("G_K_m", "maxG_K_m", "R_m_s", "maxR_m_s", "coolingRate_K_s",
                        "PDAS_um", "SDAS_um", "morphology", "morphologyFractions"):
                assert result[key] is None, key
            assert "doi" in result and "disclaimer" in result

    def test_solidification_microstructure_cfd_path(self):
        """With a CFD result dict containing solidificationMicrostructure → use it."""
        mock_cfd_result = {
            "solidificationMicrostructure": {
                "meanG_K_m": 8.5e6,
                "meanR_m_s": 0.032,
                "meanCoolingRate_K_s": 2.72e5,
                "maxG_K_m": 1.2e7,
                "maxR_m_s": 0.05,
                "frontCellCount": 42,
            }
        }
        params = {"power_W": 300.0, "speed_mm_s": 800.0}
        material = {"absorptivity": 0.35, "k_WmK": 15.0, "liquidus_K": 1700.0}

        result = compute_solidification_microstructure(params, material, mock_cfd_result)

        assert result["status"] == "available"
        assert result["source"] == "openfoam-solidification-model-v1"
        assert abs(result["G_K_m"] - 8.5e6) < 1.0
        assert abs(result["R_m_s"] - 0.032) < 1e-9
        assert result["frontCellCount"] == 42
        # P7a: no spacing on the CFD path (unsourced prefactors deleted); the reason is served.
        assert result["PDAS_um"] is None and result["SDAS_um"] is None
        assert "no source" in result["spacingUnavailableReason"]


if __name__ == "__main__":
    unittest.main()
