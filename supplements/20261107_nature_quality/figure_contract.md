# Figure contract

Backend: Python / Matplotlib, reused from the existing quantitative-figure task; saved as the selected backend. This is a revision of quantitative plots, not an AI raster schematic or a journal submission.

Audience and destination: undergraduate NLP course report and presentation. General Nature-inspired visual style; no claim of Nature submission compliance. Final physical sizes: 228.6 × 162.6 mm and 228.6 × 182.9 mm. Body glyphs >= 7 pt; minimum glyph floor 5 pt. White background, editable SVG/PDF text, PNG/TIFF 600 dpi. PNGs are the only user-facing delivery, as requested.

User override: images only, no explanatory paragraphs or footnotes. Essential panel titles, axes, units, legends and metric labels remain. This also overrides the Academic Figure Prompt palette-confirmation/prompt-output steps: retain the already established blue/teal/neutral palette and adapt its four-layer design prompt internally, without a new palette question or user-facing prompt.

Core question: do the prepared samples satisfy the measurable structural requirements for this continuation task, and how did source-text sizes change?

Claim: measured sample completeness, type consistency, exact-pair uniqueness and vocabulary coverage can be quantified; known character anomalies have recorded dispositions. This does not establish semantic transcription accuracy, which remains unlabelled.

Archetype: quantitative grid, followed by paired source-size comparison. No unsupported overall data-quality score, radar polygon, accuracy, Precision/Recall/F1, or missing-data imputation.

Evidence chain for figure 1:
- a: structural quality dimensions (complete sample fields, field-type consistency, exact source-target uniqueness, vocabulary coverage); semantic accuracy explicitly unavailable.
- b: known anomaly disposition (170 source-backed repairs, 26 quarantined occurrences, zero PUA remaining in active text).
- c: representation and partition sizes, exact counts by source and train/validation.
- d: observed target-length distributions, all samples, with median and interquartile range and no inferential error bars.

Evidence chain for figure 2:
- a: paired raw/processed Han counts for all 17 works, same zero-based absolute scale.
- b: per-work proportional net change, (processed-raw)/raw, same ordering. This is a size change, not a quality-accuracy score.

Data integrity: verify frozen archive hashes; recompute extended QC on all 72,690 logical samples. Do not count source-specific JSONL copies as additional observations. No resampling or deletion. Length statistics are descriptive; overlapping windows are not independent replicates, so no KS p-values, bootstrap confidence intervals or significance stars are used.

Reference adaptation: the two user-supplied articles motivate completeness, consistency, uniqueness, profiling and distribution checks. Accuracy requires a reference; numeric mean/mode imputation and automatic IQR deletion are not appropriate repairs for novel text. Definitions are cross-checked with the Government Data Quality Framework.

Required audits: source preflight; rendered axes alignment within 1.5 pt; PDF glyph floor; PDF collision audit; panel-by-panel PNG inspection. Preserve audit artifacts outside the frozen corpus.
