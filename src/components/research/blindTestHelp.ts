/**
 * Help text of the blind test form as data (spec 4.1: every metadata field says what it is and how it changes the grade
 * or the status). Plain English. No claim of accuracy or validation.
 */
import type { BlindMetadataDraft } from "../../data/lpbfUserBlind";

/** Every place in this app where a served or research depth is visible (spec 4.1). */
export const PREDICTION_SURFACES: readonly string[] = [
  "the Build Job result",
  "the process window",
  "the melt-pool cross-section lab (thermal route)",
  "the Dataset Comparison lab, including the spent-set descriptive panel",
  "the Melt Pool vs Measurements lab",
  "the machine-calibration block",
  "the Research model panel (Melt Pool lab and Build Job Decision lab)",
  "any CLI that prints a served or research depth",
];

export const PLAN_PANEL_SENTENCE = "The experiment plan panel shows no depth, only a score, the kernel disagreement and an interval width, so viewing it does not count as viewing predictions.";

export const PREDICTIONS_VIEWED_HELP = `"No" is an informed answer only if you have not seen a served or research depth for these conditions anywhere in this app. A depth is visible in: ${PREDICTION_SURFACES.join("; ")}. Answer "yes" if you saw one, and "unsure" if you cannot tell. "Yes" or "unsure" ends the test as not blind, and the report says so. ${PLAN_PANEL_SENTENCE}`;

export interface BlindFieldHelp { label: string; help: string }

export const BLIND_FIELD_HELP: Record<keyof BlindMetadataDraft, BlindFieldHelp> = {
  blockLabel: { label: "Block label", help: "A name for this set of tracks, 1 to 80 letters, digits, spaces and . _ ( ) / -, not starting with = + - or @. It is for display only and changes no grade or status." },
  mode: { label: "Mode", help: "Pre-measurement means you freeze the predictions before you measure. Post-measurement means the measurements already exist; you can still fix the targets file by its hash before the freeze to keep the test blind. Mode sets the blindness status of the report. There is no default." },
  alloy: { label: "Alloy", help: "Selects the served model path and the leverage cut. All five alloys are scored with the same thresholds. The thresholds were registered for Ti-6Al-4V and AlSi10Mg and are reused unchanged for 316L, IN718 and IN625, which the report labels. IN625 has no leverage cut, so an IN625 test that meets all four thresholds ends inconclusive. Each test holds one alloy; results are never pooled across alloys." },
  quantity: { label: "Quantity", help: "Melt pool depth is the quantity scored in protocol 1." },
  depthBoundary: { label: "Depth boundary", help: "How the depth boundary was found. Anything other than an etched fusion boundary is a block issue, because the observable differs from what the model computes." },
  measurementMethod: { label: "Measurement method", help: "Optical or SEM cross section, or other. It is recorded and changes no grade." },
  depthDatum: { label: "Depth datum", help: "Where depth is measured from. Only the original surface matches the model. Any other value, including unresolved (the default), is a block issue." },
  reduction: { label: "Reduction", help: "How your depths were reduced before upload. Upload one row per track, or one row per section with track_id and section_id. A maximum only or a single selected section is a block issue. One mean per condition can never meet the resolution qualifier, because no track scatter exists. A sheet with a mean and a standard deviation is not accepted: an SD column is an unknown header. There is no default." },
  crossSectionLocation: { label: "Cross section location", help: "Where along the track the section was cut. Near the track start or end, or unstated (the default), is a block issue because those sections show transients." },
  beamDiameter_um: { label: "Block beam size (um)", help: "One beam size for the whole block. Needed only when the inputs file has no spot_um column. If both are given, the column wins per row. Refused when neither is given." },
  beamQuantity: { label: "Beam size is a", help: "Whether the beam value you give is a diameter or a radius. A radius is doubled before the definition conversion, and the factor is frozen. This guards against a case such as a 37.5 um value that may be the radius of a 75 um beam. There is no default." },
  beamDefinition: { label: "Beam definition", help: "1/e2, D4sigma, FWHM or unstated. Unstated is read as 1/e2, gives beam grade C and a label. FWHM is converted with a fixed factor. D4sigma is taken as 1/e2 for a Gaussian. The input, the factor and the converted value are frozen." },
  beamBasis: { label: "Beam basis", help: "Measured at the work plane, measured at another plane, or nominal (the default). It sets the beam grade." },
  beamProfile: { label: "Beam profile", help: "The served model is Gaussian. Top-hat or ring is a block issue. Unknown (the default) adds a label and is not an issue." },
  beamUncertaintyReleased: { label: "Beam uncertainty released", help: "Tick when you supply a beam uncertainty. It can raise the beam grade." },
  beamUk1_um: { label: "Beam uncertainty (um, k=1)", help: "Standard uncertainty of the beam size. Used for the beam grade when released." },
  powerBasis: { label: "Power basis", help: "Measured at the workpiece, measured elsewhere, commanded (the default) or unstated. Commanded and unstated give power grade C." },
  powerMeterNamed: { label: "Power meter named", help: "Tick when the power meter is named in your records. It can raise the power grade." },
  powerUncertaintyReleased: { label: "Power uncertainty released", help: "Tick when you supply a relative power uncertainty. It can raise the power grade." },
  powerUk1Rel: { label: "Power uncertainty (relative, k=1)", help: "Relative standard uncertainty of the power, for example 0.02. A value above 0.05 is labelled, because it exceeds the 5 % input sensitivity band." },
  wavelength_nm: { label: "Wavelength (nm)", help: "The served model is an infrared flat plate model. Values outside 1030 to 1100 nm are refused. There is no default." },
  substrateKind: { label: "Substrate", help: "Bare plate is what the served model computes. A powder layer is shown for information and is not scored. There is no default." },
  layerThickness_um: { label: "Layer thickness (um)", help: "5 to 200 um, required for a powder layer. Leave empty for a bare plate." },
  amSubstrate: { label: "Additively built substrate", help: "Tick when the plate itself was additively built. It changes the default depth uncertainty assumption." },
  thickness_mm: { label: "Plate thickness (mm)", help: "Empty is a block issue." },
  surfacePreparation: { label: "Surface preparation", help: "Machined, ground, polished, blasted, as-built, other or unstated. Unstated (the default) is a block issue." },
  alsi10mgState: { label: "AlSi10Mg plate state", help: "As-built or heat-treated. The served property data follow the as-built convention, so heat-treated or unstated adds a label on AlSi10Mg arms. Used only for AlSi10Mg." },
  preheat_C: { label: "Plate temperature (C)", help: "The plate temperature before the first track. Required to compute predictions; refused when missing." },
  preheatBasis: { label: "Plate temperature basis", help: "Measured, set-point or nominal ambient. Nominal ambient adds a label and a declared divergence." },
  atmosphere: { label: "Atmosphere", help: "Argon, nitrogen, helium, vacuum, air or other. Unstated (the default) is a block issue." },
  tracksPerCondition: { label: "Tracks per condition", help: "A whole number from 1 to 20. Checked against your inputs file at the preview. A single track per condition needs enough replicated conditions elsewhere in the block to meet the resolution qualifier." },
  sectionsPerTrack: { label: "Sections per track", help: "A whole number from 1 to 20. Sections of one track are never replicates." },
  rowsAreSeparateTracks: { label: "Repeated rows are separate tracks", help: "Tick when several rows of one condition without a track_id are really separate tracks. Without it, such a file is refused." },
  depthUncertaintyBasis: { label: "Depth uncertainty basis", help: "Per row, one value for the block, or not released (the default). Not released uses the app's assumed measurement uncertainty and adds the label u_m assumed." },
  depthUncertaintyU: { label: "Block depth uncertainty (um)", help: "Positive number, required when the basis is block. The uncertainty used is this value divided by the coverage factor." },
  coverageFactor: { label: "Coverage factor", help: "1 if your uncertainty is a standard uncertainty, 2 if it is expanded with k=2." },
  chemistryBasis: { label: "Chemistry basis", help: "Certified heat analysis, supplier nominal or unstated. Recorded only. With certified sulfur and oxygen the label says so, otherwise it says they are missing. Not a served model input." },
  sulfur_ppm: { label: "Sulfur (ppm)", help: "Recorded only." },
  oxygen_ppm: { label: "Oxygen (ppm)", help: "Recorded only." },
  predictionsViewedBeforeFreeze: { label: "Predictions viewed before the freeze", help: PREDICTIONS_VIEWED_HELP },
  dataPreviouslyPublished: { label: "Data previously published", help: "No, yes or unknown (the default). Unknown is a block issue because independence is not established. Published data cannot be a pre-measurement test; choose post-measurement." },
  publishedDoi: { label: "DOI of the publication", help: "A DOI such as 10.1234/abc. If the DOI is in this app's list of already used data, the test is not blind." },
  usedForMachineCalibration: { label: "Used for machine calibration", help: "Tick yes if these conditions were used to fit a machine calibration in this app or elsewhere. Yes ends the test as not blind. There is no default." },
  targetCommitmentSha256: { label: "Targets file SHA-256", help: "Post-measurement mode only. Pick your finished targets file here to compute its SHA-256 in the browser, or paste a hash. If the file you upload for scoring has this hash, the test is blind by commitment." },
  csvDialect: { label: "CSV format", help: "Comma separated with decimal points (the default), semicolon separated with decimal points, or semicolon separated with decimal commas. A header with the wrong separator is caught before upload." },
};

const READABLE: Record<string, string> = {
  "comma-dot": "Comma separated, decimal point",
  "semicolon-dot": "Semicolon separated, decimal point",
  "semicolon-comma": "Semicolon separated, decimal comma",
  "1/e2": "1/e2",
  "no": "No", "yes": "Yes", "unsure": "Unsure", "unknown": "Unknown", "unstated": "Not stated",
};
/** Option text for an enumerated word: names such as Ti-6Al-4V, 1/e2 and FWHM stay as they are. */
export function blindOptionLabel(word: string): string {
  if (word in READABLE) return READABLE[word];
  if (/^[A-Z0-9]/.test(word)) return word;
  const spaced = word.replace(/-/g, " ");
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}
