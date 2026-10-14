# The route: who runs each step

Principle: code does every check and every number. A cheap model only reads the customer's email into a fixed form. People keep every decision: the credit check, the margin and the send.

The skill has no send capability. All data in this repository is synthetic.

| # | Who | Step | On failure | Status |
|---|---|---|---|---|
| 0 | Human | Check that available credit covers the amount | Stop before any draft | human |
| 1 | Model (cheap) | Read the email into a fixed JSON form: one record per item, with currency, amount, start date, end date or tenor, and item type (drawdown, rollover, repayment) | Form not valid: hand back | built: `scripts/extract_form.py`, Haiku 5.5 |
| 2 | Code | Validate the form: required fields present, currency in the allowed list, dates parse | Hand back and name the missing field | built |
| 3 | Code | Grounding check: every amount and date in the form must appear in the newest message of the email. The item count must match the amounts in the email | Mismatch: hand back, never guess | built |
| 4 | Code | Route: a currency or request the rate sheet cannot answer is handed back. A repayment is acknowledged with no quote | none | built |
| 5 | Code | Sheet freshness: the sheet date must equal the received date | Stop and name the stale date | built |
| 6 | Code | Date checks: weekends, holiday calendars (USD: US and SG), value date before the received date | Move a weekend or holiday date to the next business day and tell the customer; hand back a value date before the received date | built for weekends, holidays and value dates |
| 7 | Code | Compute the end date. Read the regular tenor row on an exact match, else the odd-dates row whose range contains it. A value date earlier or later than T+2 reads the forward rate file | No row: hand back | built |
| 8 | Code | Rate = cost of funds + margin supplied by the relationship manager, rounded to 2 decimals | none | built |
| 9 | Code | Fill the quote template | none | built |
| 10 | Model (optional) | Smooth the wording only | Skip if not needed | not used |
| 11 | Code | Draft check: every number and date in the draft must equal the step 8 and 9 output exactly | Any change: reject the model version, keep the template version | built |
| 12 | Human | Confirm or change the margin; review and send | none | human |

The frozen acceptance rule (`acceptance-rule-v1.1.md`) wins over this table if the two differ.
