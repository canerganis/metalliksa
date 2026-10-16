"""Optional GPU capability tests; no Warp installation or GPU required."""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from gpu_capability import GpuCapabilityError, require_warp, warp_capability


class GpuCapabilityTests(unittest.TestCase):
    def test_missing_runtime(self):
        with patch("gpu_capability.importlib.import_module", side_effect=ModuleNotFoundError("No module named 'warp'")):
            state = warp_capability()
            self.assertEqual(state["code"], "gpu-runtime-missing")
            self.assertFalse(state["available"])
            with self.assertRaises(GpuCapabilityError) as ctx:
                require_warp("cuda:0")
            self.assertEqual(ctx.exception.capability["code"], state["code"])
            self.assertNotIn("No module named", str(ctx.exception))

    def test_missing_device_and_explicit_ordinal(self):
        api = SimpleNamespace(init=Mock(), get_cuda_devices=Mock(return_value=[]))
        with patch("gpu_capability.importlib.import_module", return_value=api):
            self.assertEqual(warp_capability()["code"], "gpu-device-missing")
            with self.assertRaises(GpuCapabilityError):
                require_warp("cuda:0")
            # Warp CPU ray tracing remains usable when the runtime is installed.
            require_warp("cpu")
            api.get_cuda_devices.return_value = [SimpleNamespace(alias="cuda:1")]
            self.assertTrue(warp_capability()["available"])
            with self.assertRaises(GpuCapabilityError):
                require_warp("cuda:0")
            require_warp("cuda:1")

    def test_rpc_and_queue_preserve_capability(self):
        import lpbf_worker
        import lpbf_worker_rpc
        for code in ("gpu-runtime-missing", "gpu-device-missing"):
            error = GpuCapabilityError({"available": False, "code": code})
            with patch("gpu_capability.require_warp", side_effect=error):
                with self.assertRaises(GpuCapabilityError):
                    lpbf_worker_rpc.dispatch({"method": "keyhole-raytracing", "payload": {"device": "cuda:0"}}, None, None)
                with self.assertRaises(GpuCapabilityError):
                    lpbf_worker.Queue.submit(None, {"jobType": "gpu-thermal-pilot", "executionEngine": "warp", "backend": "cuda:0"})
            reply = lpbf_worker.rpc_error_response({"id": 1}, error)
            self.assertEqual(reply["capability"]["code"], code)
            self.assertEqual(reply["errorKind"], "capability")


if __name__ == "__main__":
    unittest.main()
