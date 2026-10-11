import statistics

# Heuristic penalty weights (volume fractions added to a sample's index when a mechanism is flagged). They are NOT
# sourced from a measurement or a paper: they are fixed placeholders that only rank flagged samples above clean ones.
# There is no keyhole penalty: defect_diagnostics() assigns no keyhole risk (D/W alone cannot resolve keyhole
# porosity) and no sourced keyhole flag exists, so keyhole never contributes to the index.
LOF_VOLUME_PENALTY = 0.05
BALLING_VOLUME_PENALTY = 0.08
# Lack-of-fusion statuses that defect_diagnostics() emits when the Tang overlap screen fails or nothing melts.
LOF_FAIL_STATUSES = ("lack-of-fusion-screened", "inadequate-penetration", "no-melt")

INDEX_LABEL = "Unsourced screening index (not a measured or predicted relative density)"
INDEX_EVIDENCE_LABEL = "Screening only"
INDEX_BASIS = (
    "Unsourced screening index, not a density or porosity estimate: 100 % minus a sum of fixed penalty fractions "
    "that have no literature or measurement source (lack of fusion 5 % when the Tang overlap screen fails, 2.5 % "
    "when marginal; balling 8 % for High, 2.4 % for Moderate) and an unsourced 0.01 % powder-gas prior, averaged "
    "over the sampled inputs. There is no keyhole term. It is not calibrated against any density measurement and "
    "only ranks flagged samples below clean ones."
)
SPREAD_BASIS = (
    "Mean plus or minus 1.96 standard deviations of the per-sample heuristic penalty over the Monte Carlo input "
    "samples. It is the spread of the penalties, not a confidence interval of any density."
)
CONFIDENCE_NOTE = (
    "Not assessed. The sample count is the number of sampled inputs, not independent evidence; no density "
    "measurement supports this index."
)


def aggregate_part_porosity(defect_samples, powder_gas_prior_percent=0.01):
    """
    Aggregate track/layer risks back to the CAD part as an unsourced screening index.

    The index is 100 % minus summed fixed, unsourced penalties; it is not a measured or predicted relative density.
    powder_gas_prior_percent is in percent of volume (0.01 means 0.01 %, i.e. a fraction of 0.0001).

    defect_samples is a list of results from defect_diagnostics() evaluated
    across a Monte Carlo sweep of inputs (power, speed, etc.).
    """
    if not defect_samples:
        return {"error": "No defect samples provided for aggregation."}

    prior_fraction = float(powder_gas_prior_percent) / 100.0

    porosity_samples = []
    # keyhole stays in the payload at 0: no sourced keyhole risk flag exists, so it is never counted.
    mechanism_counts = {"lackOfFusion": 0, "keyhole": 0, "balling": 0, "gasPore": len(defect_samples)}

    for sample in defect_samples:
        sample_porosity = prior_fraction

        # Lack of fusion: riskScreened is True when the Tang overlap screen fails, False when the geometry is covered and None
        # when marginal or unresolved; the penalty applies only when the screen actually fails.
        lof = sample.get("lackOfFusion", {})
        if lof.get("status") in LOF_FAIL_STATUSES or lof.get("riskScreened") is True:
            sample_porosity += LOF_VOLUME_PENALTY
            mechanism_counts["lackOfFusion"] += 1
        elif lof.get("status") == "marginal":
            sample_porosity += LOF_VOLUME_PENALTY * 0.5

        # Balling
        bl = sample.get("balling", {})
        bl_risk = bl.get("risk")
        if bl_risk == "high":
            sample_porosity += BALLING_VOLUME_PENALTY
            mechanism_counts["balling"] += 1
        elif bl_risk == "moderate":
            sample_porosity += BALLING_VOLUME_PENALTY * 0.3

        porosity_samples.append(sample_porosity)

    avg_porosity = statistics.mean(porosity_samples)
    stdev_porosity = statistics.stdev(porosity_samples) if len(porosity_samples) > 1 else 0.0

    spread_high_penalty = avg_porosity + 1.96 * stdev_porosity
    spread_low_penalty = max(0.0, avg_porosity - 1.96 * stdev_porosity)

    def to_index_percent(penalty_fraction):
        return round(min(100.0, max(0.0, 100.0 - penalty_fraction * 100.0)), 3)

    # The gas-pore count is the baseline prior applied to every sample, not a screened mechanism, so it never
    # counts as the dominant mechanism.
    screened = {k: v for k, v in mechanism_counts.items() if k != "gasPore"}
    dominant_mechanism = max(screened, key=screened.get)
    if screened[dominant_mechanism] == 0:
        dominant_mechanism = "none"

    return {
        "status": "aggregated",
        "screeningIndex": {
            "label": INDEX_LABEL,
            "evidenceLabel": INDEX_EVIDENCE_LABEL,
            "basis": INDEX_BASIS,
            "mean_percent": to_index_percent(avg_porosity),
            # Lower index value = larger penalties. Both ends are the spread of the penalties, see spreadBasis.
            "spread_lower_percent": to_index_percent(spread_high_penalty),
            "spread_upper_percent": to_index_percent(spread_low_penalty),
            "spreadBasis": SPREAD_BASIS,
        },
        "porosity": {
            "mean_fraction": round(avg_porosity, 5),
            "stdev_fraction": round(stdev_porosity, 5),
            "label": "Sum of fixed heuristic penalty fractions, not a predicted porosity",
        },
        "dominantMechanism": dominant_mechanism,
        "mechanismCounts": mechanism_counts,
        "confidence": "unassessed",
        "confidenceNote": CONFIDENCE_NOTE,
        "sampleCount": len(defect_samples),
    }
