# Published factor and unresolved source reconciliation

## Selected value and source
GRIDSHIFT retains the **published 2024 South African NGGEF: 0.960 tCO2e/MWh**, rather than replacing it with an independently calculated alternative. Attribution: Department of Forestry, Fisheries and the Environment, *South Africa’s 2024 Grid Emission Factors Report*, Government Gazette 55353, Notice **7891**, 11 September 2026. [Official PDF](https://www.gov.za/sites/default/files/gcis_document/202609/55353 gon 7891.pdf).

Table 1 (printed p. 3 / PDF index 7) and Table 7 (p. 14/index 18) publish the value. Section 5.4 (p. 9/index 13) excludes transmission/distribution losses from NGGEF; Table 6 (p. 12/index 16) assigns NGGEF to Scope 2 and loss factors to Scope 3. Footnotes 2/4 identify IPCC Second Assessment Report GWPs. Later prose mentions grid-loss adjustments ambiguously. Tables 3–4 and footnotes 3/5 give apparently conflicting generation/auxiliary-consumption information. These source ambiguities remain unresolved.

## Independent arithmetic check — not a replacement factor
The audit transcribed the following displayed quantities from Tables 3–4 (printed p. 9–10 / PDF indices 13–14):

| Quantity | Displayed value | Unit |
|---|---:|---|
| Generation emissions | 204823175 | tCO2e |
| Imported electricity emissions | 4708 | tCO2e |
| Generation | 230436320 | MWh |
| Auxiliary consumption | 16538861 | MWh |
| Own consumption | 7924377 | MWh |
| Imported electricity | 8405350 | MWh |

The following are our arithmetic checks, not additional official claims:

- Adding emissions gives 204827883 tCO2e.
- Subtracting auxiliary and own consumption from generation, then adding imports, gives 214378432 MWh. Their ratio is approximately **0.9554500473**, which does not round to 0.960 at three decimal places.
- Reading the footnote literally as saying generation is already net instead gives denominator 238841670 MWh and ratio approximately **0.8575885565**. This also does not reproduce 0.960.
- The analogous domestic subtraction yields approximately 0.9944171977, rounding to the published 0.994; the literal-net reading yields approximately 0.8888493576. This illustrates the ambiguity, not proof of which source input is wrong.
- For an exactly 0.960 ratio, the first calculation would require a denominator smaller by 1016053.875 MWh. This is a conditional algebraic difference, **not measured missing electricity**, and a rounded 0.960 does not imply one exact denominator gap.

The displayed tables/footnotes do not suffice to establish how the published factor was derived. No authority has resolved the discrepancy for this prototype. Do not describe GRIDSHIFT as independently deriving, certifying or validating the official factor. Do not silently substitute 0.95545,0.85759 or a guessed input correction.

## Appropriate claim and policy boundary
This is a narrow, offline **location-based purchased-electricity emissions estimate** using a manually transcribed published factor and explicitly synthetic or unverified activity. It is not a full Scope 2 compliance assessment. It does not assess organizational boundaries, market-based reporting, contractual instruments, assurance, carbon credits, additionality or causal avoided emissions. Source GWP metadata is retained; compatibility with a particular reporting regime is not established.

Matching the activity year to the factor data year is this prototype’s conservative supported-use policy. It is **not a claim that every reporting framework universally mandates exact-year matching or forbids a disclosed latest-available factor**. This implementation supports 2024 activity only, offers no proxy-year mode and must not relabel 2026 usage to make it pass. Data year 2024 and publication year 2026 are distinct.

Source uncertainty remains **NOT_QUANTIFIED_IN_SOURCE**. Historical changes, source-reconciliation differences and exact Decimal arithmetic do not justify a confidence interval, a symmetric sensitivity band, or an assertion of zero uncertainty. Activity truth, transcription risk and source-model uncertainty remain separate limitations.

## Review provenance
This note incorporates an independent arithmetic check of user-supplied AI-assisted feedback dated 25 October 2026. The feedback is not authenticated human expert certification. The source issue is disclosed, not claimed resolved. No external clarification request, source-factor change or new empirical validation is represented by this note.
