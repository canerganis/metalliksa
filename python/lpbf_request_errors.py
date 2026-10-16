"""Presentation/admission at unpinned boundaries; never change numerical physics."""
import json

SUPPORTED_ALLOYS_TEXT = "Ti-6Al-4V, AlSi10Mg, Inconel 718 or 316L Stainless Steel"


class LpbfRequestRefusal(ValueError):
    def __init__(self, code, field, message, detail=None):
        self.code, self.field, self.message = code, field, message
        self.detail = dict(detail or {})
        super().__init__(message)

    def envelope(self):
        return {"success": False, "errorKind": "validation", "error": {
            "code": self.code, "field": self.field, "message": self.message, "detail": self.detail}}


def refusal(code, field, message):
    """Keep legacy string error callers compatible, with stable machine-readable fields."""
    return {"success": False, "errorKind": "validation", "code": code, "field": field, "error": message}


def thermal_refusal(error):
    """Translate only known domain stops. Unexpected solver errors stay errors."""
    if not isinstance(error, ValueError):
        return None
    text = str(error)
    if text.endswith(": thermophysical data missing; supply sourced properties"):
        return LpbfRequestRefusal("MISSING_THERMOPHYSICAL_TABLE", "properties",
            "Thermophysical data are missing for this material. Supply a sourced property table in Material "
            f"properties, or select {SUPPORTED_ALLOYS_TEXT}.", {"diagnostic": text})
    if text.startswith("Thermal model validity exceeded at or above the material boiling limit"):
        return LpbfRequestRefusal("THERMAL_BOILING_LIMIT", "power_W",
            "The run reached the material boiling limit. Reduce laser power or increase scan speed and run again. "
            "This conduction model cannot calculate evaporation or free-surface flow.", {"diagnostic": text})
    return None


def validate_thermal_request(raw):
    from lpbf_simulation import validate
    try:
        return validate(raw)
    except ValueError as error:
        translated = thermal_refusal(error)
        if translated is not None:
            raise translated from error
        raise


def run_thermal_request(*args, solver=None, **kwargs):
    from lpbf_simulation import run
    try:
        return (solver or run)(*args, **kwargs)
    except ValueError as error:
        translated = thermal_refusal(error)
        if translated is not None:
            if getattr(error, "progress", None) is not None:
                translated.progress = error.progress
            raise translated from error
        raise


def validate_build_job_request(raw):
    from four_alloy_materials import resolve_alloy_id
    requested = raw.get("alloyId")
    if requested is not None and str(requested).strip() and resolve_alloy_id(requested) is None:
        raise LpbfRequestRefusal("UNSUPPORTED_BUILD_JOB_ALLOY", "alloyId",
            f"This material is not supported by Build Job. Select {SUPPORTED_ALLOYS_TEXT}.")


def refusal_frame(error):
    return json.dumps({"refusal": error.envelope()}, allow_nan=False)


def execution_refusal(log):
    for line in reversed(log.splitlines()):
        try:
            frame = json.loads(line)
            env = frame.get("refusal") if isinstance(frame, dict) else None
            err = env.get("error") if isinstance(env, dict) else None
            if (isinstance(env, dict) and env.get("success") is False and env.get("errorKind") == "validation"
                    and isinstance(err, dict) and all(isinstance(err.get(k), str) for k in ("code", "field", "message"))
                    and isinstance(err.get("detail"), dict)):
                return err
        except (ValueError, RecursionError):
            pass
    return None
