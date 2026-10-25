# E1 exclusions

Excluded from this business-decision comparison. Each item is either tested elsewhere or not done.

1. **Implementation-integrity attacks**: tampered or re-hashed workspace envelopes, stale or forged imported approvals, non-portable JSON numbers (floats, exponent forms, integers beyond ±(2^53−1)), size and record limits, malformed or unknown-field schemas, and empty files. They test the software, not reviewer decisions, and both arms would need different tooling to see them. They are covered by `lane-b/adversarial/` and the web tests. EXPERIMENT_E1.md listed some of these; they were moved out deliberately to keep the comparison fair.
2. **The 8 frozen expectation misses and the C17 message divergence** from `lane-b/adversarial/` run2. They are kept unchanged there and explained in `lane-b/MISS_DISPOSITIONS.md`.
3. **The 5 R1 portability regression tests**. They are regression tests, not benchmark cases.
4. **The previous 24-case benchmark** (`benchmarks/`). It is not re-run or re-scored, and its tie stands.
5. **Real or rights-cleared public cases.** None were included, because no licence was verified for use. This is not done.
6. **Human productivity or usefulness claims.** E1 is rules versus rules only; any such claim needs real participants.
7. **Market-based Scope 2, other countries, other factor years, and time-of-use.** These are outside the prototype's scope.
8. **Run outputs of any kind.** None exist at freeze time, and none may be added to this folder.
