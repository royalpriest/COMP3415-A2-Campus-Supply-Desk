# CR-01 prediction (recorded before express implementation)

## Behavior to change
Add `express` to service, CLI and menu fulfillment choices. Its 1,200-cent fee is unconditional. Student discounts still apply only to merchandise. Pickup defaults and standard delivery pricing remain intact. Orders retain express details through history, reopening and cancellation.

## Predicted files
- supplydesk/service.py: shared fulfillment validation and delivery calculation; express fee constant.
- supplydesk/cli.py: fulfillment choices and help.
- supplydesk/menu.py: fulfillment prompt.
- README.md and FUNCTIONAL_SPEC.md: explain express pricing and examples.
- tests/test_express.py: service and adapter acceptance tests.

Storage format and order lookup/cancellation should not need express-specific changes because orders already persist fulfillment and pricing snapshots.

## Planned tests
Check all three CR examples; fixed express fee below, at and above the standard free-delivery threshold; student discount boundary and half-cent rounding; quote/placement equality; reopening and cancellation snapshots; numbering and stock; CLI quote/place/help; interactive quote/place/defaults/confirmation; unsupported fulfillment rejected without mutations. Rerun the existing safety net.

This prediction was written after refactoring and separate baseline-defect fixes, before adding express.
