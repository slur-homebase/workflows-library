# Step-1 forms (hand-written stand-ins)

These JSON files are the fixed form that step 1 of the route (`docs/route-option-script-first.md`) is meant to produce by having a cheap model read the request text. Until Week 3 there is no model call, so each form here was typed by hand from the matching `fixtures/requests/<id>.txt`.

They stand in for the model extraction step only. Steps 2 to 9 and 11 run on them exactly as they will run on model output, including the grounding check (step 3), which compares every amount and date in the form with the request text.

Shape:

```json
{
  "request_id": "REQ-001",
  "items": [
    {
      "item_type": "drawdown | rollover | repayment",
      "currency": "USD",
      "amount": 5000000,
      "value_date": "2026-09-30",
      "tenor_business_days": 30,
      "facility_ref": "FAC-SYN-0001"
    }
  ]
}
```

A drawdown or rollover item gives exactly one of `tenor_business_days` or `end_date`. A repayment item gives neither.

Synthetic only. Every value comes from the invented request texts in `fixtures/requests/`.
