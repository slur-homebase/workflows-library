<!--
Quote template for the rate-quote skill, v0.4 (owner decision 2026-10-14, option A: no "Item N" numbering; each item is headed by what the rate is for, e.g. "USD drawdown"; "Amount:" replaces "Currency and amount:").
v0.3 (owner review 2026-10-13: tenor in calendar days; no margin-source sentence; no basis line).

scripts/quote.py reads this file, strips this comment, splits it into the
sections marked "=== name ===" and fills the {placeholders}. Step 11 then
checks every number and date in the finished draft against the computed
values, so the fixed wording must not contain digits of its own (write
"two business days", not "2 business days").

Sections:
  header             once per draft
  quoted_item        once per drawdown or rollover item
  acknowledged_item  once per repayment item
  adjustment_line    once per date adjustment, inserted into {adjustment_lines}
  footer             once per draft
-->
=== header ===
Subject: Rate quote - {request_id}

Dear customer,

Thank you for your request. Our indication is set out below.

=== quoted_item ===
{currency} {purpose}
Amount: {currency} {amount}
Value date: {value_date_long}
End date: {end_date_long}
Tenor: {tenor_calendar_days} days
All-in rate: {customer_rate}% per annum
{adjustment_lines}
=== acknowledged_item ===
{currency} repayment
We note your repayment of {currency} {amount} on {value_date_long}. No rate applies to this item.

=== adjustment_line ===
Please note: {reason}

=== footer ===
This indication is for information only and is not a commitment until confirmed in writing.

Kind regards,
[SIGN-OFF]
