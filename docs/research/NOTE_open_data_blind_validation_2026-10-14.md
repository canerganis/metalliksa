# NOTE: why open single-track data could not support a blind depth test (Ti-6Al-4V, AlSi10Mg)

Status: DRAFT, internal. Not for publication or external sharing without the maintainer. Not committed.
File: `docs/research/NOTE_open_data_blind_validation_2026-10-14.md` (worktree `Metalliksa-1-wt-hub`).
Evidence window: audits and sweeps dated 2026-10-14. `GOAL.md` and `BOARD.md` read as of 2026-10-15. Drafted 2026-10-15.
Roadmap item: GOAL.md "Roadmap after the batch push", item 5 (findings note, drafted here, external publication needs the maintainer).
This note contains no measured depth values. Process inputs and counts appear only where they explain a metadata gap.

## 1. Short answer

1. No source we audited or swept met the minimum needed for a blind melt-pool or keyhole depth block, for either alloy. Seven sources were audited one by one by custodial readers before any target was opened. Three sweeps (repositories, Ti-6Al-4V papers, AlSi10Mg papers) screened the rest on metadata.
2. The same five gaps repeat: depth datum, beam definition, measured delivered power, a tabulated per-condition depth, and replicates. Only one audited source (Leis 2021) has a confirmed per-condition depth table, and it fails on the datum.
3. Access is rarely the limit. Several sets are fully open and still fail, because they are already spent, powder-only, figure-only, or missing keys.
4. Consequence recorded in GOAL.md: G2 (Ti-6Al-4V keyhole vapour depth) and G3o (open-data melt depth) are BLOCKED BY DATA. Every target is unread and unspent, and no rule was loosened. G3 as written is permanently blocked because the maintainer has no laboratory access.
5. The remedy is reporting, not search effort. Section 7 is the minimum checklist. The campaign specification (Appendix A) is the reference design for people who can run a campaign.

## 2. Question

Can a single-track source that is openly available today serve as a blind test block for the app's two depth predictors?

1. Keyhole vapour depth (G2), tested under the P3 pre-registration against X-ray vapour depression data.
2. Melt depth (G3, and its open-data successor G3o), tested under the MELT pre-registration against etched fusion-boundary data.

Primary alloys are Ti-6Al-4V and AlSi10Mg (maintainer decision 2026-10-14). IN625 is out of scope here. "Blind" means the predictor and its inputs are frozen and hashed before any outcome is read, and the block is independent of everything used for calibration or earlier scoring.

The G3 acceptance thresholds are fixed in GOAL.md: median absolute relative error at most 20 %, 90th percentile at most 35 %, absolute mean signed error at most 10 %, no condition above 50 %, at least 12 conditions per block. They were frozen before any target was read and were not changed in this work.

## 3. Method

1. Pre-registration first. The P3 protocol (Amendments 4 to 6) and the MELT protocol (Amendments 2 to 6) define eligibility, key resolution, reductions and pass rules before any data is read. ORCHESTRA.md section 4 stays binding, as GOAL.md states: no tuning on held-out data, one declared run, negative results reported.
2. Custodial metadata audits before any target. A reader who is not the scorer extracts only process inputs, equipment, substrate, datum wording, table structure, replicates and data availability. Outcome digits are masked. Each report ends with an exposure statement, and an exposed reader is not used for blind work on that source. Seven audits were done: Bitharas raw archive, Ruckh 2025, Leis 2021, Ullah 2025, Gong 2014, Hyer 2020 and the Udine Mendeley set.
3. Archive handling for the Bitharas raw archive. The SHA-256 was recorded before any listing. The reader opened only the zip central directory (names, no member opened, no header, pixel or payload read). Key resolution then ran under a frozen grammar. A power, speed or beam token with no unit never resolves, because mapping it to a unit would be inference.
4. Sweeps on metadata only. The repository sweep read landing pages, API metadata and README text with digits masked, and downloaded no data file. The two literature sweeps used sentence filters that drop depth, width and penetration wording. Slips are disclosed in Section 8.
5. No loosening. The stop rule in GOAL.md kill criterion 1 applies: stop scoring when beam, power, datum, observable identity, exposure or campaign independence is unresolved, and report a data blocker. The grammar was not changed after the names were seen, and no eligibility rule was relaxed to admit a candidate.

## 4. Per-source results

### 4.1 Audited sources (custodial or masked audit before any target)

"Not stated" means not stated in the text the auditor read. Figures were not rendered, except Leis Figure 1.

| Source and setting | Datum | Beam definition | Power measured | Tabulated per-condition depth | Replicates | Open availability | Outcome |
|---|---|---|---|---|---|---|---|
| Bitharas 2022 raw archive. Ti-6Al-4V, X-ray vapour depression, bare scans | Not assessed, no frame opened | Not resolvable per condition. No beam token in any folder name | Not established. Power and speed tokens carry no unit and the power tokens lie outside the Methods power range, so they are not watts | None in the raw route. Figure_data.xlsx exists in the repo and was never opened | 7 scanned bare acquisitions, below the declared minimum of 8 conditions with both beams | Yes. CC BY, 15565 members, 4509771341 bytes | INCONCLUSIVE by data blocker at Stage 1. Targets unread |
| Ruckh 2025, Addit. Manuf. 113:105007. Ti-6Al-4V, X-ray cavity, powder layer on a plate | Not read. The Methods sentence defining the cavity dimensions was withheld from the auditor | One beam value given. Definition and measured or nominal not stated | Not stated whether measured or commanded | Main-text Table 1 is regime level only. Supplementary Tables 1 to 3 are cited and unread | Eight power and speed sets with ten radiographs each in one analysis. Total condition count not stated | Data "on request". No repository, no DOI. ESRF ID19 | Powder only, so not a P3 secondary block. G2 stays blocked. Auditor exposed |
| Leis, Weber, Graf 2021, Materials 14:5255. AlSi10Mg, etched single beads, one powder layer on an AM AlSi10Mg block | Stated only in Figure 1 (p.4): depth is drawn from the bead top, not from the original substrate surface | 1/e2, three nominal settings set by defocus. Whether each was measured is not stated | Commanded. No meter named | Yes. Appendix Table A2, about 82 rows. Average, minus and plus columns are undefined. 15 rows are N/A in every depth and width cell | 3 repeats, at least 6 beads per set. Beads per row and sections per bead not stated | Yes. CC BY 4.0, tables inside the article | INCONCLUSIVE by metadata (MELT A6: depth from the cap top). Targets unread and unspent. 3 of about 80 depth rows had been seen earlier by a sweep author |
| Ullah et al. 2025, Opt. Laser Technol. Ti-6Al-4V, beam-shaped single tracks, powder layers on a plate | Not stated | Nominal spot per beam mode in Table 1. Text says "measured" but gives no method and no definition | Nominal, commanded. No meter | No. Depth is in figures and supplementary figures. The one error table compares model and experiment on four rows | No standard deviation or error bars. Track and plate structure is ambiguous (Section 9) | Article open access. Supplement with the paper. Further data "on request". No dataset DOI | INCONCLUSIVE by metadata |
| Gong et al. 2014, SFF proceedings. Ti-6Al-4V, EOS M270, a bare-plate arm and a powder-layer arm | Not stated | No beam diameter and no definition | Nominal, commanded | No. Table 1 lists factor levels only. Outcomes are in figures | None. One mid-bead section per bead | PDF openly hosted. No data deposit | INCONCLUSIVE by metadata. Only multi-condition bare-plate set found; descriptive use at most |
| Hyer et al. 2020, Metallogr. Microstruct. Anal. AlSi10Mg, multi-layer cubes, top-layer melt pools | Not stated. Substrate, powder top and bead top are not named | One "Gaussian spot size" value. Definition and measured or nominal not stated | Commanded | No. Table 1 tabulates relative density. Pool depth is figure-only | None. One cube per parameter set implied | DOI only. No data statement | INCONCLUSIVE by metadata |
| Udine set (Vaglio et al. 2020, Data in Brief; Mendeley s9438vb5xd). Ti-6Al-4V, single tracks, powder layer on a printed base from the same job | Not defined in the Methods text. A figure was not read | 1/e2 stated, nominal setting | Commanded setpoints | A spreadsheet exists per the repo attribution note. Not opened in the audit | One per condition, 80 conditions (8 powers by 10 speeds) | Yes. CC BY 4.0, 105 MB zip | SPENT. Already in the repo for calibration and held-out checks, so not blind |

### 4.2 Sweep-level candidates (metadata from landing pages, READMEs and papers; not custodially audited)

| Source | Alloy and observable | Main gap | Open | Status |
|---|---|---|---|---|
| KU Leuven figshare 15035709, 15035712 (Coen et al.) | Ti-6Al-4V melt pool CSVs | README is one line. No key stated in the dataset text | CC0 | SPENT (committed in the repo, used in calibration) |
| NIST mds2-2923 | IN625 and IN718 bare plates, three machines | Secondary alloys. Probably overlaps the spent AM-Bench tracks | Open licence | Not new, not a primary alloy |
| NIST mds2-3707, mds2-4103 (AM-Bench 2025) | IN718 | Secondary alloy. Answer keys public by design. Pads use fixed laser parameters | Open licence | Exposed by design |
| NIST mds2-2525 | Ti-6Al-4V bare thin plates, X-ray, plus Al | About 4 to 6 conditions. No Ti-6Al-4V depth table. Absorptance already used in the repo | Open licence | Too small |
| Zenodo 20549954 | Ti-6Al-4V beam shaping, EOS M290 | Files restricted behind a login | Record CC BY, files restricted | Not usable |
| Zenodo 11173421 (Bahari-Sambran et al.) | AlSi10Mg cube melt pools mixed with literature rows | No beam, no single tracks, no datum, no replicates stated | CC BY | Weak |
| Borealis 10.5683/SP3/YSXRGA | Multi-alloy literature compilation | No uniform datum or beam definition. Depth recorded as zero when unreported. Source papers likely already used | CC BY | Pointer list only |
| MDF 10.18126/yjyd-kayg (Paulson, Gould) | Ti-6Al-4V X-ray, powder channel, 9 single-line runs | Raw images only, powder, no depth reduction released. Would need our own segmentation | CC BY 4.0, 9.9 GB | Descriptive powder block at best |
| Gorgannejad 2023 | Ti-6Al-4V X-ray, bare, 40 conditions, D4sigma stated | Per-condition table not released. One beam diameter, which gives INCONCLUSIVE under P3 Amendment 3 item 4. No data statement | Not open | Lead only |
| Pyeon 2021 | Ti-6Al-4V X-ray, bare, 14 conditions, two beams | Inputs are in Table 1 but no depth table. Beam definition unstated. The two beams are close in size | Not open | Lead only |
| Els 2016, Yadroitsava 2015 (one CUT campaign family) | Ti-6Al-4V bare-plate tracks | Spot size without a definition. Commanded power. Condition counts and speed grid not tabulated | PDFs | Descriptive at most |
| Dilip 2017 | Ti-6Al-4V powder on a thin plate, 16 settings | Powder, thin plate, one track per setting. Partly exposed through repo prose | PDF | Descriptive at most |
| Porter 2022 (GitHub ConorPorter3/Single-Tracks) | AlSi10Mg, 352 tracks, unetched sections | Beam diameter, definition, machine and preheat not stated. Datum not defined in the README | GPL-3.0. Images 2.7 GB, not downloaded | Missing beam blocks a Peclet or keyhole-index test |
| Patel 2022 | AlSi10Mg, 57 conditions | Multi-track weld lines or cube top layers. One section per sample. Partly exposed | arXiv | Second tier |
| Solyaev 2025 | AlSi10Mg single tracks, six powders | Depth only in figures plus a 7-case table | CC BY 4.0 | Lead only |
| Hojjatzadeh 2019, Guo 2022 | AlSi10Mg X-ray | Figures and videos only. Raw data on request | Paper only | No numeric dataset |
| Martin 2019, Hojjatzadeh 2020, Wang 2022, Wu 2023, Ren 2023 | Ti-6Al-4V X-ray | No per-condition depth table, or data "on request" or "will be made available" | Paper only | No numeric dataset |
| Cunningham 2019 and Gan Data 1, Zhao 2020, Miner and Narra (CMU) | Ti-6Al-4V | Spent or exposed. The CMU set has no power or beam column | Mixed | Not blind |

## 5. What the pattern shows

1. Five gaps account for nearly every failure. Across the seven audited sources, none documents a measured delivered power in the text read. Only two (Leis, Udine) state a beam definition, and both are nominal settings. Only Leis has a confirmed depth table in the article. Only Leis states a datum (in a figure), and it is the bead top.
2. Open does not mean usable. Fully open sets fail for other reasons: Udine and KU Leuven are spent, Paulson and Gould is powder with raw images only, and the Bitharas archive names carry unitless tokens.
3. Fixing the datum alone would not rescue the unresolved sources. Ullah and Hyer would still have figure-only depth and undefined beams. Gong would still have no beam diameter and figure-only depth. A figure render could change the datum line in the table, but not the verdict. Udine is spent regardless.
4. Powder versus bare plate. The sets that tabulate depth (Leis, Udine, Ullah) are powder or printed-base sets. The bare-plate multi-condition sets (Gong, Els and Yadroitsava) have commanded power, no beam measurement and, for Gong, one section per bead.
5. Observable mismatch. X-ray vapour depth is not etched fusion depth, so an X-ray set cannot serve the MELT block and an etched set cannot serve P3.
6. Exposure removes sets that would otherwise qualify on paper. Several sets that are open and tabulated had already entered calibration or earlier comparison in this program (Section 8).
7. Access walls cut the rest. Restricted files, "on request" statements, bot walls and paywalls blocked reading of several candidates. The standing rule is that authors are not emailed, so "on request" sets stay unavailable.

## 6. Method limits (what this note does not show)

1. This is a result about the sources we reached. The AlSi10Mg sweep states that its search result is not a proof of absence. Several papers were behind bot walls and some were read through author manuscripts or open APIs only.
2. Audits read text extractions with digits masked. Datum wording that exists only in a figure is invisible to them. Leis Figure 1 needed a page render that the maintainer approved, and the same render was not done for Ullah, Gong, Hyer or Udine.
3. Some files were never opened by design (Figure_data.xlsx, the Udine spreadsheet, Ruckh supplementary tables, Porter section images), so their contents are unknown, not absent.
4. Aboulkhair 2016 is a named G3o candidate in GOAL.md, and BOARD records it as in the library but not opened beyond the title. No audit of it is among the sources of this note, so it is open, not blocked.
5. A follow-up key search for the Bitharas archive is recorded on BOARD (workflow `bitharas-key-search`). Its outcome is not part of this note. The maintainer decided on 2026-10-15 that if the keys cannot support a usable blind test, the archive is spent descriptively in the research panel.

## 7. Minimum reporting checklist for a dataset that can support blind tests

A source needs all items below before a scorer should accept it as a block. They are written so a dataset README can answer each in one line.

| # | Item | Why a blind test needs it | Audited sources that failed it |
|---|---|---|---|
| 1 | Substrate: bare plate or powder layer; powder layer reference (measured, not only nominal); plate material, thickness, state, surface preparation, preheat, atmosphere | Absorptance, the datum and the heat sink all depend on it. Plate thickness must be several times the depth | Ruckh, Leis, Ullah, Hyer, Udine (powder or printed base). Gong has a bare arm but no plate state |
| 2 | Delivered laser power measured at the work plane, with the meter and uncertainty named. A commanded value must be labelled commanded | The model input is delivered power. A setpoint hides an unknown offset | All seven (none documents a measured power in the text read) |
| 3 | Beam diameter at the work plane: measured, with the definition named (D4sigma preferred, 1/e2 or FWHM named) and the focus offset. One value per condition when it varies | Beam size drives both regimes. Without a named definition the value cannot be converted | All seven (two give a definition for a nominal beam) |
| 4 | Scan speed with a unit, scan length, and which part of the track was sectioned or imaged | Unitless tokens never resolve. Start and end effects differ from the steady track | Bitharas (unitless tokens). Ullah and Hyer do not state section position or count. Others not assessed |
| 5 | Observable identity and datum: fusion depth below the original substrate surface, vapour cavity depth, or depth plus height, and how the original surface was located when powder was present | Depth from a bead top or a powder top is a different quantity and the MELT rule returns INCONCLUSIVE | Leis (bead top), Ullah, Gong, Hyer, Udine (unstated); Ruckh and Bitharas not read |
| 6 | Reduction: single section, mean over sections, or mean over a steady frame window; what the spread columns mean (standard deviation, range or confidence) | The scorer must compare like with like and carry the measurement uncertainty | Leis (spread undefined). Gong, Hyer, Udine, Ullah (no spread or averaging stated) |
| 7 | A per-condition table in a machine-readable file, with a column dictionary and units, inputs separate from outcomes, one row per track or per section. Not figure-only | Digitising figures adds an unmeasured error and an unpinned protocol | Ullah, Gong, Hyer (figure-only). Ruckh, Bitharas and Udine unverified |
| 8 | Replicates: independent tracks per condition, sections per track. Frames and sections of one track are not replicates | The pass rule and the discrimination simulation assume independent tracks | Gong, Hyer, Udine, Ullah. Leis partial |
| 9 | Etch and imaging protocol, and whether section selection was blind to the condition | Etch contrast and selection bias move the boundary | Mostly not stated |
| 10 | Certified chemistry of powder and plate including oxygen and sulphur | Surface tension and its temperature slope depend on them | Not stated in most audited sources |
| 11 | Enough conditions and the right spread: at least 12 conditions per block, with conduction-side and keyhole-side conditions both present | A block entirely on one side cannot test the regime boundary | Bitharas (7), Ruckh (not stated), Ullah (9 per beam mode) |
| 12 | Independence statement: which earlier modelling, calibration or published comparison used these rows | Reuse makes the block spent | Udine, KU Leuven, Cunningham and Gan, Zhao, CMU |
| 13 | Persistent identifier, licence, file names that carry the keys, and a README that answers items 1 to 12 | A dataset that must be reverse-engineered from folder names is not a registered input | Bitharas (names), Ruckh, Ullah, Hyer (no repository) |
| 14 | Optional but best: depth targets released in a separate file after the inputs, so a custodian can hold them until the predictor is frozen | It lets an outside party run the freeze-then-compare protocol | Not offered by any source |

Design guidance from GOAL.md for a campaign that is meant to count toward G3: 32 conditions with 4 tracks each, power uncertainty 3 % and beam uncertainty 2 % at k = 2. The 40-condition fallback at 3 % and 5 % is the probable plan, because the 2 % beam figure is unproven.

## 8. Exposure log (what readers saw; no values recorded here)

This list matters because any future block drawn from these sources must declare it.

1. Ruckh 2025: the Haiku auditor saw figure-caption fit coefficients, a ratio threshold, a pixel uncertainty and a spread range, plus two outcome words in the abstract. That auditor must not do blind work on Ruckh. The lead was not exposed.
2. Leis 2021: a sweep author saw 3 of about 80 depth rows and a few area cells in a table layout check. The audit saw caption fragments (words only).
3. Ti-6Al-4V etched sweep: two Dilip 2017 depths were seen in repo prose (Dilip is partly exposed). Search-tool summaries leaked a few Ullah 2025 values and one regime-threshold phrase (not recorded).
4. Ti-6Al-4V X-ray sweep: a qualitative pore-onset passage (Gorgannejad), regime boundary statements from the Ruckh abstract, simulation error ratios (Samaei) and one correlation sentence (Pyeon).
5. AlSi10Mg sweep: about six Patel 2022 table rows, one text number from Thijs 2013, four regime labels from a repo file.
6. BOARD: a grep of the Gusarov thin-wall preprint printed one melt-depth row (not recorded; preprint not in the library).
7. Hyer 2020 audit: one block of Table 1 relative density cells and a sentence giving the direction of a depth trend.
8. Gong 2014 audit: qualitative sentences about width and depth. Udine audit: caption words and a masked line naming the datum. Ullah audit: process table, no outcomes.
9. Bitharas names: the power, speed and focus labels and the path L-2R1 are now known to the lead, so any successor route must list that exposure.

## 9. Source conflicts to resolve before anyone relies on the tables

1. Udine datum. The Ti-6Al-4V etched sweep reads it as the printed-base top. The later custodial audit finds no datum statement in the Methods text. This note uses the audit.
2. Ullah track structure. The audit reads 27 tracks per layer thickness per plate on three plates, three tracks per specimen. The etched sweep reads one track per condition. Neither reports a replicate statistic. This note treats replication as unresolved.
3. Leis powder layer. The audit gives a nominal layer height and separately a measured rim height. The AlSi10Mg sweep reports the rim value as the layer. This note states neither value. It also shows that the reference level of the powder layer is itself ambiguous.
4. Porter 2022. The repository sweep reports no repository record. The AlSi10Mg sweep found the GitHub deposit. GitHub was not among the repositories the sweep listed.
5. Ruckh substrate. The X-ray sweep treats it as possibly bare or powder and cites an unverified layer value from a search summary. The audit, from the Methods, finds a powder layer on a plate. This note uses the audit.

## 10. Recommendation

1. Keep G2 and G3o at BLOCKED BY DATA. Do not loosen a rule to admit a source. GOAL.md already names the reopen condition: a new open release with stated datum, beam definition and tabulated per-condition depths.
2. Use Section 7 as the admission gate for the monthly open-data sweep (roadmap item 4). Apply it on metadata only, name the owner of the sealed pass before any outcome file is opened, and record exposure the same way as in Section 8.
3. Route blind testing through the user's own lab. The bring-your-own-data feature (roadmap item 1) runs the freeze-then-compare protocol where the data exist. The app asks datum, beam definition and replicates, freezes predictions before reading targets, then compares.
4. Spent sets stay descriptive. The comparison panel (roadmap item 2) is labelled "not validation, data already seen". Whether Leis, Gong or the Bitharas archive are shown there is a separate maintainer decision.
5. For people who can run a campaign, the specification in Appendix A is the reference. It stays a published specification for others, not a plan this program executes (GOAL.md, no laboratory access).
6. Any external use of this note or the checklist needs the maintainer. Under the standing rule, authors are not contacted. The checklist can be shared as a reporting standard alongside the specification without naming individual sources, if the maintainer wants that.

## 11. Open items before any external use

1. Audit Aboulkhair 2016 on metadata before any statement that the open AlSi10Mg route is exhausted.
2. Fold in the Bitharas key search result and the maintainer's descriptive-spend decision.
3. Have a fresh auditor verify the Ruckh Methods lines withheld from the first auditor, and decide whether the supplementary tables are worth a sealed read.
4. Decide whether to render the datum figures for Ullah, Gong, Hyer and Udine (maintainer approval is needed for renders, as for Leis). It would settle the datum cell only.
5. Resolve the Section 9 conflicts against the primary papers.
6. Recheck the NIST pages when the portal is reachable. The sweeps recorded timeouts and 5xx errors there.

## Appendix A. Campaign specification (pointer)

`docs/research/SPEC_new_campaign_2026-10-11.md` on branch `research/ti64-primary` (branch tip `e91d0fbd` when checked on 2026-10-15). It includes the Ti-6Al-4V and AlSi10Mg amendment, written spec-only because there is no laboratory access. This note does not summarise the specification, and the file was not read for this draft. Read it from that branch.

## Appendix B. Sources used for this note

1. `Metalliksa-1/.orchestra/GOAL.md` (status sections).
2. `Metalliksa-1/.orchestra/BOARD.md` (2026-10-14 entries).
3. `Metalliksa-1/.orchestra/reports/`: `ruckh2025_masked_audit`, `leis2021_custodial_audit`, `ullah2025_custodial_audit`, `gong2014_custodial_audit`, `hyer2020_custodial_audit`, `udine_ti64_custodial_audit`, `open_dataset_sweep`, `ti64_etched_sweep`, `ti64_xray_sweep`, `alsi10mg_sweep` (each `_2026-10-14.md`).
4. `research/p3-cavity-astra:docs/research/p3_stage0/STAGE0_STAGE1_RECORD_2026-10-14.md`.
