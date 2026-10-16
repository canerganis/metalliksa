"""Optional Warp availability at the transport boundary, independent of solver physics."""
import importlib


class GpuCapabilityError(RuntimeError):
    def __init__(self, capability):
        self.capability = capability
        reason = ("no GPU runtime (NVIDIA Warp)" if capability["code"] == "gpu-runtime-missing"
                  else "no available CUDA device for this request")
        super().__init__(f"This install has {reason}. CPU solvers still work.")


def warp_capability(device=None):
    try:
        wp = importlib.import_module("warp")
    except (ImportError, OSError):
        return dict(available=False, code="gpu-runtime-missing")
    if device == "cpu":
        return dict(available=True, code=None)
    try:
        wp.init()
        if any(device is None or str(item.alias) == device for item in wp.get_cuda_devices()):
            return dict(available=True, code=None)
    except Exception:
        pass
    return dict(available=False, code="gpu-device-missing")


def require_warp(device):
    # Leave invalid device syntax to the existing solver validator.
    import re
    if device != "cpu" and (not isinstance(device, str) or re.fullmatch(r"cuda:[0-9]+", device) is None):
        return
    capability = warp_capability(device)
    if not capability["available"]:
        raise GpuCapabilityError(capability)
