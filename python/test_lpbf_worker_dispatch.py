import unittest
from unittest.mock import MagicMock

import lpbf_worker
import lpbf_worker_rpc

# The method names served by the original if/elif chain in lpbf_worker.py (frozen literal; 29
# until 2026-10-04, when experimental-validation, support-optimization, bayesian-optimizer,
# transient-enthalpy-fdm, modulus-fno, powder-dem-compaction, transient-3d-gpu, stl-voxelize,
# optical-tomography, toolpath-thermal-map, thermal-accumulation, thermomechanical-distortion,
# industrial-fatigue and multilaser-plume were deleted
# with their routes/views; toolpath-kinematics and adaptive-feedforward were deleted with scan path kinematics).
# 2026-10-16: solidification-estimates added (SOL-C opt-in estimate channel, RC1).
ORIGINAL_METHOD_NAMES = (
    "capabilities",
    "estimate",
    "submit",
    "submit-repeat",
    "artifact",
    "capture",
    "archive-capture",
    "get",
    "cancel",
    "solidification-microstructure",
    "solidification-estimates",
    "fatigue-fracture",
    "keyhole-raytracing",
    "purge-unverified-artifacts",
)


def original_method_names():
    return list(ORIGINAL_METHOD_NAMES)


class WorkerDispatchTest(unittest.TestCase):
    def test_original_method_list_is_complete(self):
        names = original_method_names()
        self.assertEqual(len(names), 14)
        self.assertEqual(len(names), len(set(names)))

    def test_every_original_method_has_a_handler(self):
        served = lpbf_worker_rpc.method_names()
        for name in original_method_names():
            self.assertIn(name, served, name)
        self.assertEqual(served, set(original_method_names()))

    def test_table_handlers_are_callable_and_disjoint(self):
        tables = (lpbf_worker_rpc.QUEUE_HANDLERS, lpbf_worker_rpc.RESEARCH_HANDLERS)
        for table in tables:
            for name, handler in table.items():
                self.assertTrue(callable(handler), name)
        self.assertFalse(set(tables[0]) & set(tables[1]))

    def test_queue_methods_route_to_queue(self):
        queue = MagicMock()
        for method, attr in (("submit", "submit"), ("get", "get"), ("cancel", "cancel"),
                             ("artifact", "artifact"), ("capture", "capture"),
                             ("archive-capture", "archive_capture")):
            lpbf_worker_rpc.dispatch({"method": method, "payload": "x"}, queue, lambda q: None)
            getattr(queue, attr).assert_called_once_with("x")
        lpbf_worker_rpc.dispatch({"method": "submit-repeat", "payload": "y"}, queue, lambda q: None)
        queue.submit.assert_called_with("y", execution_scope="repeat")

    def test_capabilities_uses_injected_handler(self):
        self.assertEqual(
            lpbf_worker_rpc.dispatch({"method": "capabilities"}, "q", lambda q: {"q": q}), {"q": "q"})

    def test_unknown_method_error_shape(self):
        with self.assertRaises(ValueError) as caught:
            lpbf_worker_rpc.dispatch({"id": 1, "method": "no-such-method"}, MagicMock(), lambda q: None)
        self.assertEqual(str(caught.exception), "Unknown method")

    def test_non_string_method_matches_original_unknown_method(self):
        for method in ([], {}, None, 0, ["submit"], {"a": 1}):
            with self.assertRaises(ValueError) as caught:
                lpbf_worker_rpc.dispatch({"id": 1, "method": method}, MagicMock(), lambda q: None)
            self.assertEqual(str(caught.exception), "Unknown method", repr(method))

    def test_missing_method_key_error_matches_original(self):
        with self.assertRaises(KeyError) as caught:
            lpbf_worker_rpc.dispatch({"id": 1}, MagicMock(), lambda q: None)
        self.assertEqual(str(caught.exception), "'method'")

    def test_worker_module_wires_rpc(self):
        self.assertIs(lpbf_worker.lpbf_worker_rpc, lpbf_worker_rpc)


if __name__ == "__main__":
    unittest.main()
