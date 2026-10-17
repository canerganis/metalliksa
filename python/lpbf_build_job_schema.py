#!/usr/bin/env python3
"""Pydantic request schema for POST /api/python/lpbf-build-job."""

from __future__ import annotations

from typing import Annotated, Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Keep in sync with src/physics/lpbfBuildMesh.ts MAX_LPBF_SLICER_TRIANGLES.
MAX_LPBF_SLICER_TRIANGLES = 12000


class LpbfBuildJobRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    alloyId: Optional[str] = "in718"
    thermalMaterial: Optional[str] = None
    slicerMaterial: Optional[str] = None
    laserPower_W: float = Field(285.0, gt=0)
    scanSpeed_mm_s: Optional[float] = Field(None, gt=0)
    scanSpeed_mms: Optional[float] = Field(None, gt=0)
    beamDiameter_um: float = Field(80.0, gt=0)
    preheatTemp_C: float = 80.0
    layerThickness_um: float = Field(40.0, gt=0)
    hatchSpacing_um: float = Field(110.0, gt=0)
    laserWavelength: str = "IR_1064nm"
    preset: str = "nozzle"
    customTriangles: Optional[List[Any]] = None
    cadAssetName: str = ""
    triangleCountNative: Optional[int] = None
    maxTriangles: int = Field(MAX_LPBF_SLICER_TRIANGLES, ge=1, le=50000)
    recoatTimePerLayer_s: float = 9.0
    processSeed: int = 42
    seed: Optional[int] = None
    scanStrategy: str = "stripe"
    stripeWidth_mm: float = Field(5.0, gt=0)
    scanRotation_deg: float = 67.0
    hatchDwell_ms: float = Field(0.0, ge=0)
    inclineAngle_deg: float = 0.0
    surfaceIncline_deg: Optional[float] = None
    downskinOverhang_deg: Optional[float] = None
    # Faz 5: lazy by default — UI opts in via Run UQ / Validate vs NIST.
    enableUq: bool = False
    uqSamples: int = Field(96, ge=8, le=500)
    includeAmbench: bool = False
    defectSqrtAreas_um: Optional[List[Annotated[float, Field(gt=0, allow_inf_nan=False)]]] = None
    defectSqrtAreasPaste: Optional[str] = None
    hardness_HV: Optional[float] = Field(None, gt=0, allow_inf_nan=False)
    ctDetectionThreshold_um: Optional[float] = None
    # Group 7 explicit fatigue scenario (no defaults; murakami_fatigue_screening validates the choices).
    defectSqrtArea_um: Optional[float] = Field(None, gt=0, allow_inf_nan=False)
    defectEvidence: Optional[str] = None
    defectLocation: Optional[str] = None
    hardnessEvidence: Optional[str] = None
    loadRatio: Optional[float] = Field(None, allow_inf_nan=False)
    cycleTarget: Optional[float] = Field(None, gt=0, allow_inf_nan=False)
    specimenOrientation: Optional[str] = None
    defectIsLongCrack: Optional[bool] = None
    defectSampling: Optional[dict] = None
    ctDetectionMethod: Optional[str] = None
    # Group 8: optional named cooling interval {high_C, low_C} and Ti isothermal hold {temperature_C, time_s, interpolate}.
    kineticsCoolingInterval_C: Optional[dict] = None
    isothermalHold: Optional[dict] = None
    # Group 2: explicit constrained-bar and released-cantilever scenarios {bar: {...}, cantilever: {...}}.
    mechanicsScenario: Optional[dict] = None
    bypassCache: bool = False
    gitSha: Optional[str] = None

    @field_validator("customTriangles")
    @classmethod
    def cap_triangles(cls, value: Optional[List[Any]], info):
        if value is None:
            return None
        # Cap applied in model_dump / solver with maxTriangles; soft-trim here for safety.
        if len(value) > MAX_LPBF_SLICER_TRIANGLES:
            return value[:MAX_LPBF_SLICER_TRIANGLES]
        return value

    def resolved_scan_speed(self) -> float:
        if self.scanSpeed_mm_s is not None:
            return float(self.scanSpeed_mm_s)
        if self.scanSpeed_mms is not None:
            return float(self.scanSpeed_mms)
        return 960.0

    def resolved_seed(self) -> int:
        if self.seed is not None:
            return int(self.seed)
        return int(self.processSeed)

    def to_solver_dict(self) -> dict:
        data = self.model_dump()
        data["scanSpeed_mm_s"] = self.resolved_scan_speed()
        data["processSeed"] = self.resolved_seed()
        tris = data.get("customTriangles")
        cap = int(data.get("maxTriangles") or MAX_LPBF_SLICER_TRIANGLES)
        if tris is not None and len(tris) > cap:
            data["customTriangles"] = tris[:cap]
            data["triangleCountNative"] = data.get("triangleCountNative") or len(tris)
        return data
