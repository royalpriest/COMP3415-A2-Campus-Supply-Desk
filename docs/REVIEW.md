# Assignment 2 implementation review

Status: implementation organized into six commits on a2-assignment. No PR is required for the instructor repository. Task 6 decisions are confirmed: ACCEPT, MODIFY, ACCEPT.

Base: royalpriest/COMP3415-A2-Campus-Supply-Desk, main, 82ed75e0714e50c086a13ee491f51b349814d8a4.

## Task 2: testing safety net

The four starter tests pass. Added service tests cover normal orders and quotes, the exact student-discount boundary, standard delivery thresholds, integer half-up rounding, stock exhaustion, quantity 99 using a controlled stock fixture, invalid types and partial requests, combined quantities, valid duplicate lines, repeated cancellation, history, unknown IDs, and malformed saves. Adapter tests cover menu confirmation, defaults, all operations, input recovery, EOF/interrupt exits, and CLI JSON/error statuses. All files use temporary state paths.

| Stage | Tests | Result |
|---|---:|---|
| Original suite | 4 | Pass |
| Added safety net on original code | 22 | Four failed subtests across three test methods |
| Structural refactoring only | 22 | Same failures |
| Separate defect fixes | 22 | Pass |
| CR-01 acceptance tests before express | 6 | Expected failure: express unsupported |
| Final complete suite | 28 | Pass |

The four baseline subtest failures are: exact-$50 student discount; duplicate quantities in quote; duplicate quantities in placement; second cancellation. Expected values were not weakened or marked expectedFailure.

## Task 4: three selected code smells

1. Duplicated service logic: extracted _prepare_request(). quote() loads and returns its result; place_order() adds ID/status and applies stock/history changes to the same loaded state. Quote/placement equality, invalid-state atomicity and history tests verify the behavior.
2. Long run_menu(): extracted handlers for catalog, quote, placement, history, lookup and cancellation; dispatch retains the central error/exit behavior. Menu tests cover confirmations, defaults, all choices, bad inputs and exits.
3. Magic numbers: replaced quantity and money-policy literals with constants, preserving integer rounding. Threshold and rounding tests guard interpretation. The structural-stage snapshot still used the original strict > discount comparison; changing it to >= happened in the separate correction stage.

Evidence: evidence/03-refactoring.patch captures the structural source changes before behavioral fixes and express. This patch is a historical snapshot, not something to apply on top of the finished working tree. Tests were untracked at snapshot time and are provided separately in tests/.

## Separate behavioral corrections

- Student discount starts at 5,000 cents inclusive, as specified (previously strict >).
- Both quote and placement accumulate quantities per product before permitting a request. Valid duplicate lines remain separate. Failed placement makes no save or numbering change.
- cancel_order() returns an already cancelled order without adding stock or rewriting the save.

These corrections are not claimed as behavior-preserving refactorings. They enforce the existing functional specification before CR-01; CR-01 does not introduce new discount or cancellation policy.

## Task 5: CR-01

Prediction: docs/CR-01-prediction.md was written before express implementation.

Actual source changes: service.py adds express validation and an unconditional 1,200-cent fee in the shared calculation; cli.py exposes express in choices/help; menu.py exposes express and its price in the prompt. README.md and FUNCTIONAL_SPEC.md document the new choice. tests/test_express.py contains six acceptance test methods with additional subcases.

The prediction was correct: storage.py and catalog.json required no changes. Existing persisted order dictionaries already retain fulfillment and price snapshots. Shared request preparation made the client change easier: express pricing and validation needed one service implementation instead of two copies.

Acceptance mapping:
- Service, CLI and menu support: test_cr_examples_and_thresholds, test_cli_express_quote_place_and_help, test_menu_express_quote_and_placement.
- Fixed fee and student rounding: test_cr_examples_and_thresholds and test_express_half_cent_rounding_and_fee_not_discounted.
- Persistence, cancellation and numbering: test_express_lifecycle_preserves_snapshots_and_numbering.
- Existing behavior and invalid operations: full safety net plus test_express_validation_and_atomicity.
- Help/prompts: CLI help assertions and recorded input-prompt assertion.

## Task 6 and remaining review

See docs/AI-RECORD.md for recommendation excerpts, confirmed ACCEPT/MODIFY/ACCEPT decisions, and supporting evidence.

Before submission, review the three behavioral corrections, the menu handlers, and express pricing. Run `python -m unittest discover -s tests -v` and try `python -m supplydesk quote --customer student --fulfillment express --item hoodie:2` (expected 8400 cents). Use a separate --data path before trying placement or cancellation.

The implementation was first prepared uncommitted, then reconstructed and reverified in ordered commits on user request. Original stage logs are preserved; evidence/08-commit-verification.md records the rechecks. Commit timestamps represent that reconstruction, not the earlier work. docs/Assignment2_Report.pdf summarizes Tasks 1-6; Task 6 records the student's confirmed decisions.
