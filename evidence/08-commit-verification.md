# Commit-stage verification

The changes were initially developed without commits at the user's request. After authorization, stages were reconstructed from the saved structural patch and final files and each was rerun before committing. No dates were backdated.

| Commit | Stage | Recheck |
|---|---|---|
| 3440201 | Added safety net on original code | 22 tests; four expected failed subtests across three defects |
| 202cce3 | Structural refactoring | 22 tests; same four failed subtests |
| 206ebcf | Existing defect corrections | 22 tests; all pass |
| fcadf6e | CR-01 prediction and acceptance tests | Six express methods; expected failure while express unsupported |
| 39058aa | Express implementation | 28 tests; all pass |
| Final documentation commit | Report, AI record and verification | 28 tests; all pass; git diff --check clean |

Original outputs remain in evidence/01 through 07. Early failing commits deliberately expose requirements not met by the starter; final tests have no skipped/expected-failure markers. The final documentation commit contains the report and this table, avoiding a self-referential commit SHA.
