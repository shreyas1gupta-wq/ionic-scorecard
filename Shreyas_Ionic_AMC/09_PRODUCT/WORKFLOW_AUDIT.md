# Full workflow audit

**40 of 43 checks pass.**

| step | item | result | detail |
|---|---|---|---|
| 1 scoring | earnings_quality_decomp.py | **FAIL** | FileNotFoundError: [Errno 2] No such file or directory: 'C:\\Users\\Shreyas.1Gupta\\OneDri |
| 1 scoring | fix_thin_coverage_v3.py | PASS | wrote C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\.c |
| 1 scoring | audit_v3_freeze.py | **FAIL** | 20 of 21 hard invariants pass. |
| 2 excel | build_scores_excel.py | PASS | calls: Sell 199 | Hold 552  (of which 195 trim-eligible) |
| 3 build | Talaulikar HNI_DEEP | PASS | === HNI_DEEP: 103 slides |
| 4 gate | Talaulikar HNI_DEEP check_geometry.py | PASS | 0 findings, 0 known-benign, 0 real |
| 4 gate | Talaulikar HNI_DEEP check_geometry2.py | PASS | 1 findings, 1 known-benign, 0 real |
| 4 gate | Talaulikar HNI_DEEP tellscan.py | PASS | 0 findings, 0 known-benign, 0 real |
| 3 build | Talaulikar STANDARD | PASS | === STANDARD: 48 slides |
| 4 gate | Talaulikar STANDARD check_geometry.py | PASS | 0 findings, 0 known-benign, 0 real |
| 4 gate | Talaulikar STANDARD check_geometry2.py | PASS | 1 findings, 1 known-benign, 0 real |
| 4 gate | Talaulikar STANDARD tellscan.py | PASS | 0 findings, 0 known-benign, 0 real |
| 3 build | Talaulikar RM_SIMPLE | PASS | === RM_SIMPLE: 30 slides |
| 4 gate | Talaulikar RM_SIMPLE check_geometry.py | PASS | 0 findings, 0 known-benign, 0 real |
| 4 gate | Talaulikar RM_SIMPLE check_geometry2.py | PASS | 1 findings, 1 known-benign, 0 real |
| 4 gate | Talaulikar RM_SIMPLE tellscan.py | PASS | 0 findings, 0 known-benign, 0 real |
| 3 build | ABXY_Showcase HNI_DEEP | PASS | === HNI_DEEP: 67 slides |
| 4 gate | ABXY_Showcase HNI_DEEP check_geometry.py | PASS | 0 findings, 0 known-benign, 0 real |
| 4 gate | ABXY_Showcase HNI_DEEP check_geometry2.py | PASS | 1 findings, 1 known-benign, 0 real |
| 4 gate | ABXY_Showcase HNI_DEEP tellscan.py | PASS | 23 findings, 23 known-benign, 0 real |
| 3 build | ABXY_Showcase STANDARD | PASS | === STANDARD: 38 slides |
| 4 gate | ABXY_Showcase STANDARD check_geometry.py | PASS | 0 findings, 0 known-benign, 0 real |
| 4 gate | ABXY_Showcase STANDARD check_geometry2.py | PASS | 1 findings, 1 known-benign, 0 real |
| 4 gate | ABXY_Showcase STANDARD tellscan.py | PASS | 21 findings, 21 known-benign, 0 real |
| 3 build | ABXY_Showcase RM_SIMPLE | PASS | === RM_SIMPLE: 20 slides |
| 4 gate | ABXY_Showcase RM_SIMPLE check_geometry.py | PASS | 0 findings, 0 known-benign, 0 real |
| 4 gate | ABXY_Showcase RM_SIMPLE check_geometry2.py | PASS | 1 findings, 1 known-benign, 0 real |
| 4 gate | ABXY_Showcase RM_SIMPLE tellscan.py | PASS | 12 findings, 12 known-benign, 0 real |
| 3 build | ABXY_Family HNI_DEEP | PASS | === HNI_DEEP: 67 slides |
| 4 gate | ABXY_Family HNI_DEEP check_geometry.py | PASS | 0 findings, 0 known-benign, 0 real |
| 4 gate | ABXY_Family HNI_DEEP check_geometry2.py | PASS | 1 findings, 1 known-benign, 0 real |
| 4 gate | ABXY_Family HNI_DEEP tellscan.py | PASS | 1 findings, 1 known-benign, 0 real |
| 3 build | ABXY_Family STANDARD | PASS | === STANDARD: 38 slides |
| 4 gate | ABXY_Family STANDARD check_geometry.py | PASS | 0 findings, 0 known-benign, 0 real |
| 4 gate | ABXY_Family STANDARD check_geometry2.py | PASS | 1 findings, 1 known-benign, 0 real |
| 4 gate | ABXY_Family STANDARD tellscan.py | PASS | 0 findings, 0 known-benign, 0 real |
| 3 build | ABXY_Family RM_SIMPLE | PASS | === RM_SIMPLE: 20 slides |
| 4 gate | ABXY_Family RM_SIMPLE check_geometry.py | PASS | 0 findings, 0 known-benign, 0 real |
| 4 gate | ABXY_Family RM_SIMPLE check_geometry2.py | PASS | 1 findings, 1 known-benign, 0 real |
| 4 gate | ABXY_Family RM_SIMPLE tellscan.py | PASS | 0 findings, 0 known-benign, 0 real |
| 4b dots | check_dots.py (all decks) | PASS | PASS -- every deck's signal dots carry colour |
| 5 method | data/azby_family.py | PASS | 0 findings |
| 5 method | data/talaulikar_family.py | **FAIL** | 6 findings |

## Findings accepted as benign (examined, not suppressed)

- **check_geometry2 / disclaimer colophon** — the disclaimer page's own colophon sits at 6.90-7.20 by design on a dark terminal page; the gate exempts by y-position, not by role, so it reads as a spill
- **tellscan / genuine** — 'genuine deleveraging' is ordinary English; tellscan's AI-tell list flags the word itself
