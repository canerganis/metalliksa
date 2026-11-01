# Your blind test: a user guide

This guide is for a researcher who has their own laser powder-bed fusion single-track cross sections and wants to see
how the app's served melt-pool depth compares with them, without the app seeing the measurements first.

What it is: your own test of the model on your data, run on your computer. What it is not: validation of this app.
The app's evidence labels do not change (`experimentalValidation` stays false, the module stays `Screening only`),
and no result enters the project's G3o or G3s objectives, a calibration, the leaderboard or the research registry.

Design reference: `docs/research/SPEC_research_hub_data_2026-10-14.md` (Part P).

## 1. What you need

1. An inputs file (CSV): one row per track, or per section with `track_id` and `section_id`. Columns: `condition_id`
   (or unique `track_id` values), `track_id`, `section_id`, `power_W`, `speed_mm_s`, `spot_um`, optional
   `power_u_k1_W`. Units in brackets are read and converted, for example `Speed (m/s)` or `Power (kW)`. A column
   that looks like a measurement (depth, width, height, cap, area and similar) is refused in this file.
2. A targets file (CSV) with exactly the same keys, plus `depth_um`, optional `width_um`, `depth_u_um` and
   `depth_status`. You upload it only after the freeze.
3. The metadata form: alloy, mode (before or after measuring), how depth was measured, beam size and definition,
   power basis, plate and atmosphere, replication, uncertainty and whether the data were published or used for
   machine calibration. Every field has a help text in the app.

Download the templates from the first step. Each template has one row marked `SYNTHETIC-EXAMPLE`; delete it, because
the app refuses that row.

Alloys: Ti-6Al-4V, AlSi10Mg, 316L, IN718 and IN625 are all scored with the same thresholds. The thresholds were
registered for Ti-6Al-4V and AlSi10Mg and are reused unchanged for the other three; the report says so. IN625 has no
leverage cut, so an IN625 test that meets all four thresholds ends inconclusive. One test holds one alloy; results
are never pooled across alloys.

## 2. The steps

1. Research Hub, tab "Your blind test". Fill the description.
2. Pick the inputs file and press "Check inputs with the app". Read the parsed inputs table (values in canonical
   units, the unit read from each header and the conversion), the best reachable outcome, the block issues with how
   to fix them, the labels and the declared divergences. Tick the acknowledgements the check asks for.
3. Freeze. The app computes the served prediction and four sensitivity runs (power and beam size each 5 % lower and
   higher) for every condition, stores them and shows a receipt with hashes only. A freeze can hold the simulation
   queue for up to about a minute.
4. Share the `freezeSha256` from the receipt with someone outside this computer, or commit it to a repository,
   before you measure or upload measurements. This app cannot prove the order of events by itself.
5. Measure (if you have not yet), then upload the targets file and answer whether you saw predictions before you
   finalised it. A malformed file is refused with row and column numbers only and uses no attempt.
6. Read the report. Export the comparison CSV and the bundle if you need them.

After measuring first (post-measurement mode) you can fix the targets file by its SHA-256 before the freeze: pick it
in the description step and the browser computes the hash; the file itself is not sent. Do not open and save that
file again in a spreadsheet program before scoring; even an unchanged save usually changes its bytes. On plain http
to another computer the browser cannot hash; paste the value from `sha256sum` or
`certutil -hashfile <file> SHA256` instead.

## 3. Reading the report

1. Blindness status, one of: blind-committed, blind-prospective-declared, blind-retrospective-declared, or a
   not-blind status with its reason (predictions viewed or revealed, overlap with an earlier test on this computer,
   changed targets on a later attempt, data in this app's spent ledger, Build Job history, machine calibration). A
   not-blind result still shows its numbers, labelled for information.
2. Served arm status: thresholds-met, threshold-not-met, inconclusive (with the reason) or descriptive. The four
   thresholds are median APE 0.20, 90th percentile APE 0.35, mean signed error 0.10 and maximum APE 0.50 on at
   least 12 conditions, with leverage and resolution qualifiers.
3. Labels on every value. Your values are `Measured (user-supplied)` with trust tier `Declared` (nobody has checked
   the table). Served values are `Unresolved: the served result does not yet list the source of each value.` The
   sensitivity runs are an input sensitivity range, not an error bar. The research arm is not requested in this
   version.
4. Declared divergences from the pre-registered method are listed in full, with the ones that applied marked.

## 4. What the app enforces, and what it cannot

Enforced: inputs and targets travel in separate files; the targets never reach the app before a freeze exists; the
freeze process cannot load the targets parser; no predicted value appears in any preview, receipt, list, job record
or log; the frozen predictions are served only after a reveal or a score; frozen values are never recomputed; every
record is written with its hash file and the ledger is hash chained; every attempt and reveal is printed in later
reports.

Not enforceable: the order of events is recorded on this computer's clock; the served model is public and
deterministic, so viewing predictions elsewhere in the app is declared by you, not prevented; anyone with disk access
can rewrite the store, which only an externally shared hash can detect.

## 5. Where the data live

The store is `METALLIKSA_USER_BLIND_ROOT`, by default `.runtime/user-blind/` in the checkout (in Docker
`/data/user-blind`). Nothing is uploaded anywhere. There is no delete button, because the history is evidence. To
archive, stop the app and move the whole store folder; the app starts a new empty store on the next test. Do not edit
`ledger.jsonl`: if its hash chain no longer verifies, the app refuses new tests in that store (existing tests can
still be read and exported).

Shared servers: the store is not per user. When the server is reachable by others (`METALLIKSA_HOST` not a loopback
address) blind tests are refused unless an operator sets `METALLIKSA_USER_BLIND_SINGLE_USER=true`. Read-only installs
refuse them too.

## 6. Offline command line

`python python/tools/lpbf_user_blind.py` offers `templates`, `preview`, `freeze`, `reveal`, `score`, `list`, `show`,
`bundle` and `verify`. Run it in the same environment as the worker (both Windows or both WSL); a store created by
one refuses changes from the other. `show` and `bundle` print or export predictions only after a reveal or a score,
or with `--reveal` and the exact phrase. `verify --bundle FILE` prints the `freezeSha256` for you to compare with the
value you shared, re-checks every hash and re-computes the statistics.
