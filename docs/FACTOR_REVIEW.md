# Independent factor review — 25 October 2026

## Verified source facts
DFFE's 2024 Grid Emission Factors Report, Government Gazette 55353, Notice 7891, published 11 September 2026, uses calendar-year 2024 data. Table 1 (printed p3 / PDF index7) reports NGGEF **0.960 tCO2e/MWh**; Table 7 (p14/index18) agrees. Other factors: DGGEF 0.994; TLGEF 0.021; DLGEF 0.071.

Section 5.4 (p9/index13) assigns NGGEF to consumption/Scope2, includes imports, excludes T&D losses; Table6 (p12/index16) assigns losses to Scope3. Appendix A (p19/index23) uses purchased electricity × NGGEF. Footnotes 2/4 (p9–10) specify IPCC Second Assessment Report GWPs. No numerical uncertainty or individual-gas breakdown located. Approximately two-year publication lag is explicit (p5).

Source caveats: contents still labels some tables/figures 2023; actual table is 2024. Later narrative (p13,15) loosely mentions losses, unlike explicit Scope2 boundary. Use section5.4/Table6, disclose ambiguity. Do not substitute generation factor or add loss factors to Scope2.

## Implementation recommendations (reviewer)
- Default reject country/year mismatch; do not relabel 2024 factor as 2026 simply because publication is 2026.
- Keep purchased grid electricity distinct from generation, on-site solar and monetary invoice amounts.
- Source precision is three decimals: deterministic computation does not imply metrological accuracy.
- Set uncertainty to NOT_QUANTIFIED_IN_SOURCE, never zero or fabricated ± interval. Keep input quality and factor provenance separate.
- Synthetic activity remains synthetic even with official factor. No savings, independent assurance, blockchain or regulatory-compliance claim follows from multiplication.
- Test 500 MWh -> 480 tCO2e and equivalent kWh conversion as arithmetic benchmarks, not validated customer outcomes.

## Access and licence evidence
Official landing links the PDF and displays Government of South Africa copyright. No open-content licence established. Safest publication bundle includes numeric facts, attribution and links only, not PDF reproduction or a claim the source document is MIT-licensed. This is a conservative packaging recommendation, not a legal opinion.

PDF: https://www.gov.za/sites/default/files/gcis_document/202609/55353gon7891.pdf
Landing: https://www.gov.za/documents/notices/national-environmental-management-air-quality-act-report-south-africa%E2%80%99s-2024-grid

## Verification limits
Web extraction read source text and tables; PDF screenshot calls returned references without viewable pixels. Direct curl returned HTTP503, so no downloaded bytes/hash or visual-table verification is claimed. No outreach, changes to source, publication or spend performed.
