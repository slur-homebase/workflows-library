#!/usr/bin/env python3
"""rate-quote v0.2: the deterministic core of the rate-quoting skill.

Runs steps 2 to 9 and 11 of docs/route-option-script-first.md on a step-1
form. Python 3 standard library only. No network, no mailbox, no send
capability, no writes outside --out.

v0.2 adds the forward rate path (value date later than T+2 reads
forward_rate_calculator.csv in the sheet folder), bundled requests with a
repayment and a quoted item in one draft, and end dates given directly that
fall on a holiday (moved, quoted on the moved date, customer told).

Usage:
  python3 skills/rate-quote/scripts/quote.py \
      --form fixtures/forms/REQ-001.json --received 2026-09-28 \
      --sheet-dir fixtures/rate_sheets --calendars fixtures/calendars \
      --margins fixtures/margins.csv --out /tmp/req001

Exit codes: 0 = run completed with a draft or an acknowledgement;
            2 = run completed with outcome hand_back;
            1 = the script itself could not run (bad arguments, unreadable input).
"""

import argparse
import csv
import json
import re
import sys
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_DOWN
from pathlib import Path

SKILL_VERSION = "0.2"

# ---------------------------------------------------------------------------
# Fixed rules
# ---------------------------------------------------------------------------

ALLOWED_CURRENCIES = ("USD",)                    # the sheet can answer these
HAND_BACK_CURRENCIES = ("AUD",)                  # named hand-back path
CALENDARS_BY_CURRENCY = {"USD": ("US", "SG"), "JPY": ("JP", "SG")}
ITEM_TYPES = ("drawdown", "rollover", "repayment")
QUOTED_ITEM_TYPES = ("drawdown", "rollover")
SPOT_BUSINESS_DAYS = 2                           # value date must be T+2
OUTCOMES = ("quote_draft", "revision_draft", "hand_back", "acknowledge")

FOUR_DP = Decimal("0.0001")
TWO_DP = Decimal("0.01")

TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "references" / "quote-template.md"


class HandBack(Exception):
    """The request (or one item of it) goes back to the human. Never guess."""

    def __init__(self, step, reason):
        super().__init__("step %s: %s" % (step, reason))
        self.step = step
        self.reason = reason


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def parse_iso_date(text, label):
    try:
        return date.fromisoformat(str(text).strip())
    except (TypeError, ValueError):
        raise HandBack(2, "%s is not a date in YYYY-MM-DD form: %r" % (label, text))


def parse_decimal(text, label):
    try:
        value = Decimal(str(text).replace(",", "").strip())
    except InvalidOperation:
        raise HandBack(2, "%s is not a number: %r" % (label, text))
    if not value.is_finite():
        raise HandBack(2, "%s is not a finite number: %r" % (label, text))
    return value


def round_half_down_2dp(value):
    """Customer figure: 2 decimals, an exact 5 in the third decimal rounds down.

    Owner decision 2026-10-05. Decimal only; never float.
    """
    return Decimal(value).quantize(TWO_DP, rounding=ROUND_HALF_DOWN)


def format_amount(amount):
    """5000000 -> '5,000,000'; 1234.5 -> '1,234.50'."""
    amount = Decimal(amount)
    if amount == amount.to_integral_value():
        return "{:,}".format(int(amount))
    return "{:,.2f}".format(amount)


def long_date(d):
    """2026-09-30 -> '30 September 2026'. No leading zero."""
    return "%d %s %d" % (d.day, d.strftime("%B"), d.year)


def ordinal(n):
    if 10 <= n % 100 <= 20:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")


# ---------------------------------------------------------------------------
# Calendars and business days
# ---------------------------------------------------------------------------

def load_calendar(path):
    holidays = set()
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            holidays.add(date.fromisoformat(line))
    return holidays


def load_holidays(calendar_dir, currency):
    names = CALENDARS_BY_CURRENCY[currency]
    holidays = set()
    for name in names:
        holidays |= load_calendar(Path(calendar_dir) / ("%s.txt" % name))
    return holidays, names


def is_business_day(d, holidays):
    return d.weekday() < 5 and d not in holidays


def next_business_day(d, holidays):
    while not is_business_day(d, holidays):
        d += timedelta(days=1)
    return d


def add_business_days(start, n, holidays):
    """Count n business days forward from start; start itself is day zero."""
    d = start
    counted = 0
    while counted < n:
        d += timedelta(days=1)
        if is_business_day(d, holidays):
            counted += 1
    return d


def business_days_between(start, end, holidays):
    """Business days after start up to and including end."""
    d = start
    counted = 0
    while d < end:
        d += timedelta(days=1)
        if is_business_day(d, holidays):
            counted += 1
    return counted


def holiday_reason(d, calendar_dir, names):
    if d.weekday() >= 5:
        return "a %s" % d.strftime("%A")
    for name in names:
        if d in load_calendar(Path(calendar_dir) / ("%s.txt" % name)):
            return "a %s holiday" % name
    return "not a business day"


# ---------------------------------------------------------------------------
# Step 2: validate the form
# ---------------------------------------------------------------------------

def validate_form(form):
    """Return a normalised copy of the form. Raise HandBack naming the field."""
    if not isinstance(form, dict):
        raise HandBack(2, "form is not a JSON object")
    request_id = form.get("request_id")
    if not request_id or not isinstance(request_id, str):
        raise HandBack(2, "missing field: request_id")
    items = form.get("items")
    if not isinstance(items, list) or not items:
        raise HandBack(2, "missing field: items (need at least one item)")

    out_items = []
    for i, item in enumerate(items, start=1):
        label = "item %d" % i
        if not isinstance(item, dict):
            raise HandBack(2, "%s is not an object" % label)
        for field in ("item_type", "currency", "amount", "value_date", "facility_ref"):
            if item.get(field) in (None, ""):
                raise HandBack(2, "%s: missing field: %s" % (label, field))
        item_type = str(item["item_type"]).strip().lower()
        if item_type not in ITEM_TYPES:
            raise HandBack(2, "%s: item_type must be one of %s, got %r"
                           % (label, ", ".join(ITEM_TYPES), item["item_type"]))
        currency = str(item["currency"]).strip().upper()
        if not re.fullmatch(r"[A-Z]{3}", currency):
            raise HandBack(2, "%s: currency must be a three-letter code, got %r"
                           % (label, item["currency"]))
        amount = parse_decimal(item["amount"], "%s: amount" % label)
        if amount <= 0:
            raise HandBack(2, "%s: amount must be positive, got %s" % (label, amount))
        value_date = parse_iso_date(item["value_date"], "%s: value_date" % label)

        tenor = item.get("tenor_business_days")
        end_date = item.get("end_date")
        norm = {
            "item_no": i,
            "item_type": item_type,
            "currency": currency,
            "amount": str(amount),
            "value_date": value_date.isoformat(),
            "facility_ref": str(item["facility_ref"]).strip(),
        }
        if item_type in QUOTED_ITEM_TYPES:
            has_tenor = tenor not in (None, "")
            has_end = end_date not in (None, "")
            if has_tenor == has_end:
                raise HandBack(2, "%s: give exactly one of tenor_business_days or end_date" % label)
            if has_tenor:
                try:
                    tenor_int = int(str(tenor).strip())
                except ValueError:
                    raise HandBack(2, "%s: tenor_business_days is not a whole number: %r" % (label, tenor))
                if tenor_int <= 0:
                    raise HandBack(2, "%s: tenor_business_days must be positive" % label)
                norm["tenor_business_days"] = tenor_int
            else:
                end = parse_iso_date(end_date, "%s: end_date" % label)
                if end <= value_date:
                    raise HandBack(2, "%s: end_date must be after value_date" % label)
                norm["end_date"] = end.isoformat()
        out_items.append(norm)

    return {"request_id": request_id.strip(), "items": out_items}


# ---------------------------------------------------------------------------
# Step 3: grounding against the request text
# ---------------------------------------------------------------------------

CURRENCY_AMOUNT_RE = re.compile(r"\b[A-Z]{3}\s?\d[\d,]*(?:\.\d+)?\b")
# Form-style layout (BH, 2026-10-13: loosen the item-count check): a currency on
# its own labelled line ("Ccy: USD") and the amount on another ("Amount:
# 10,000,000.00"). A labelled amount line counts as one currency amount only
# when the same message also has a labelled currency line. An amount line that
# already carries its currency ("Amount: USD 5,000,000") is counted once, by
# CURRENCY_AMOUNT_RE.
LABELLED_CURRENCY_RE = re.compile(r"^\s*(?:ccy|currency)\s*[:=]\s*[A-Z]{3}\b", re.IGNORECASE | re.MULTILINE)
LABELLED_AMOUNT_RE = re.compile(
    r"^\s*(?:[A-Za-z]+\s+)?(?:amount|principal|notional)\s*[:=]\s*\d[\d,]*(?:\.\d+)?\s*$",
    re.IGNORECASE | re.MULTILINE)


def count_currency_amounts(message):
    """Currency amounts named in the message: 'USD 5,000,000' style, plus
    labelled amount lines when the message has a labelled currency line."""
    adjacent = len(CURRENCY_AMOUNT_RE.findall(re.sub(r"\s+", " ", message)))
    labelled = len(LABELLED_AMOUNT_RE.findall(message)) if LABELLED_CURRENCY_RE.search(message) else 0
    return adjacent + labelled
# A number token: digits with optional thousands commas and decimals. A full stop
# that ends a sentence ("USD 1,500,000.") is not part of the number.
NUMBER_RE = re.compile(r"(?<![\w.])\d[\d,]*(?:\.\d+)?(?!\w)(?!\.\d)")
MULTIPLIER_RE = re.compile(
    r"(?<![\w.])(\d[\d,]*(?:\.\d+)?)\s*(million|mio|mn|m|thousand|k)\b", re.IGNORECASE)
MULTIPLIERS = {"million": 1_000_000, "mio": 1_000_000, "mn": 1_000_000, "m": 1_000_000,
               "thousand": 1_000, "k": 1_000}


def numbers_in_text(text):
    found = set()
    for token in NUMBER_RE.findall(text):
        try:
            found.add(Decimal(token.replace(",", "")))
        except InvalidOperation:
            pass
    for token, unit in MULTIPLIER_RE.findall(text):
        try:
            found.add(Decimal(token.replace(",", "")) * MULTIPLIERS[unit.lower()])
        except InvalidOperation:
            pass
    return found


def date_variants(d):
    """The ways a customer might write a date. Matched case-insensitively."""
    mon, mon3 = d.strftime("%B"), d.strftime("%b")
    day, dd, mm, y = d.day, "%02d" % d.day, "%02d" % d.month, d.year
    suf = ordinal(day)
    return {
        d.isoformat(),
        "%d %s %d" % (day, mon, y), "%d %s %d" % (day, mon3, y),
        "%d%s %s %d" % (day, suf, mon, y), "%d%s %s %d" % (day, suf, mon3, y),
        "%d %s, %d" % (day, mon, y), "%d of %s %d" % (day, mon, y),
        "%s %d, %d" % (mon, day, y), "%s %d %d" % (mon, day, y),
        "%s %d, %d" % (mon3, day, y), "%s %d%s, %d" % (mon, day, suf, y),
        "%s/%s/%d" % (dd, mm, y), "%s/%s/%d" % (mm, dd, y),
        "%d/%d/%d" % (day, d.month, y), "%d/%d/%d" % (d.month, day, y),
        "%s.%s.%d" % (dd, mm, y), "%s-%s-%d" % (dd, mm, y),
        # day and month without the year: customers often drop it
        "%d %s" % (day, mon), "%d %s" % (day, mon3),
        "%d%s %s" % (day, suf, mon), "%s %d" % (mon, day),
    }


def date_in_text(d, text):
    for variant in date_variants(d):
        pattern = r"(?<!\w)" + re.escape(variant) + r"(?!\w)"
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


# Thread rule (BH, 2026-10-13): ground the form against the newest message only,
# and hand back any thread whose newest message corrects or changes an earlier one.
# Reason: in a reply thread the old values sit in the quoted message, so a model
# that copied the old value would still pass a check against the whole text.
QUOTE_START_RE = re.compile(
    r"^\s*(>|-{2,}\s*Original Message|From:|Sent:|On .{1,200} wrote:\s*$)", re.IGNORECASE)
CORRECTION_RE = re.compile(
    r"\b(correct(ion|ed|ing)?|amend(ed|ment|ing)?|revis(e|ed|ion|ing)|updat(e|ed|ing)"
    r"|chang(e|ed|es|ing)|instead|rather than|please ignore|disregard|replac(e|es|ed|ing))\b",
    re.IGNORECASE)


def split_request(request_text):
    """Split the request into the newest message and any quoted earlier messages.

    The header block (lines up to the first blank line) is left out, except the
    Subject line, which the sender wrote. Header lines such as Received: and the
    fixture's Case: note can never ground a value."""
    lines = request_text.splitlines()
    body_start = next((i for i, l in enumerate(lines) if not l.strip()), len(lines))
    subject = [l.split(":", 1)[1] for l in lines[:body_start]
               if l.lower().startswith("subject:")]
    body = lines[body_start:]
    cut = next((i for i, l in enumerate(body) if QUOTE_START_RE.match(l)), len(body))
    newest = "\n".join(subject + body[:cut])
    quoted = "\n".join(body[cut:])
    return newest, quoted


def ground_form(form, request_text):
    """Every amount, date and tenor in the form must appear in the newest message."""
    newest, quoted = split_request(request_text)
    if quoted.strip():
        hit = CORRECTION_RE.search(newest)
        if hit:
            raise HandBack(3, "the newest message in this thread corrects or changes an earlier message "
                              "(it says %r); threads with a correction go to BH, never quoted from the form"
                           % hit.group(0))
    text = re.sub(r"\s+", " ", newest)
    numbers = numbers_in_text(text)
    report = {"status": "ok", "items": [], "currency_amounts_in_text": count_currency_amounts(newest),
              "grounded_on": "newest message only (header lines and quoted earlier messages left out)",
              "quoted_text_ignored": bool(quoted.strip())}
    for item in form["items"]:
        checks = {}
        amount = Decimal(item["amount"])
        checks["amount"] = amount in numbers
        checks["value_date"] = date_in_text(date.fromisoformat(item["value_date"]), text)
        if "tenor_business_days" in item:
            checks["tenor_business_days"] = Decimal(item["tenor_business_days"]) in numbers
        if "end_date" in item:
            checks["end_date"] = date_in_text(date.fromisoformat(item["end_date"]), text)
        checks["currency"] = re.search(r"\b%s\b" % re.escape(item["currency"]), text) is not None
        report["items"].append({"item_no": item["item_no"], "found_in_text": checks})
        missing = [k for k, v in checks.items() if not v]
        if missing:
            raise HandBack(3, "item %d: %s in the form not found in the newest message of the request (%s)"
                           % (item["item_no"], ", ".join(missing),
                              ", ".join("%s=%s" % (k, item[k]) for k in missing)))
    if report["currency_amounts_in_text"] < len(form["items"]):
        raise HandBack(3, "form has %d items but the newest message names only %d currency amounts"
                       % (len(form["items"]), report["currency_amounts_in_text"]))
    return report


# ---------------------------------------------------------------------------
# Step 5: rate sheet
# ---------------------------------------------------------------------------

def resolve_sheet_folder(sheet_dir, received):
    """Step 5: the sheet folder dated the received date, or stop and name the date."""
    sheet_dir = Path(sheet_dir)
    candidates = [sheet_dir / ("rate_sheet_%s" % received.strftime("%Y%m%d")),
                  sheet_dir / received.isoformat()]
    for folder in candidates:
        if (folder / "transfer_pricing.csv").is_file():
            return folder
    if (sheet_dir / "transfer_pricing.csv").is_file():
        # --sheet-dir points at one sheet folder, not at the folder of dated sheets
        dates = sorted({r["sheet_date"] for r in read_csv(sheet_dir / "transfer_pricing.csv")})
        raise HandBack(5, "no rate sheet dated %s: --sheet-dir %s is itself a single sheet folder dated %s, not a folder of dated sheets. Stop and wait for the %s sheet."
                       % (received.isoformat(), sheet_dir, ", ".join(dates) or "unknown", received.isoformat()))
    available = sorted(p.name for p in sheet_dir.iterdir()
                       if p.is_dir() and (p / "transfer_pricing.csv").is_file())
    raise HandBack(5, "no rate sheet dated %s in %s (looked for %s); sheets present: %s. Stop and wait for the %s sheet."
                   % (received.isoformat(), sheet_dir, candidates[0].name,
                      ", ".join(available) or "none", received.isoformat()))


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def load_sheet(folder, received, currency):
    regular = [r for r in read_csv(folder / "transfer_pricing.csv") if r["currency"] == currency]
    odd_path = folder / "odd_dates.csv"
    odd = [r for r in read_csv(odd_path) if r["currency"] == currency] if odd_path.is_file() else []
    if not regular:
        raise HandBack(5, "sheet %s has no %s rows" % (folder.name, currency))
    sheet_dates = {r["sheet_date"] for r in regular + odd}
    if sheet_dates != {received.isoformat()}:
        raise HandBack(5, "sheet folder %s carries sheet_date %s, not the received date %s"
                       % (folder.name, ", ".join(sorted(sheet_dates)), received.isoformat()))
    start_dates = {r["start_date"] for r in regular + odd}
    if len(start_dates) != 1:
        raise HandBack(5, "sheet %s has more than one start_date for %s: %s"
                       % (folder.name, currency, ", ".join(sorted(start_dates))))
    return {
        "folder": folder,
        "sheet_date": received,
        "start_date": date.fromisoformat(start_dates.pop()),
        "regular": regular,
        "odd": odd,
    }


# ---------------------------------------------------------------------------
# Step 7: maturity row lookup
# ---------------------------------------------------------------------------

def lookup_row(sheet, end_date, num_days):
    for r in sheet["regular"]:
        if date.fromisoformat(r["mat_date"]) == end_date:
            if int(r["num_days"]) != num_days:
                raise HandBack(7, "transfer_pricing.csv row %s says %s days but start_date to %s is %d days"
                               % (r["tenor"], r["num_days"], end_date.isoformat(), num_days))
            return {
                "table": "transfer_pricing",
                "file": "transfer_pricing.csv",
                "tenor": r["tenor"],
                "mat_date": r["mat_date"],
                "num_days": int(r["num_days"]),
                "tp_pct": r["tp_pct"],
                "description": "transfer_pricing.csv regular tenor %s, maturity %s (%s days)"
                               % (r["tenor"], r["mat_date"], r["num_days"]),
            }
    for r in sheet["odd"]:
        lo, hi = date.fromisoformat(r["maturity_from"]), date.fromisoformat(r["maturity_to"])
        if lo <= end_date <= hi:
            d_lo, d_hi = int(r["num_days_from"]), int(r["num_days_to"])
            if not d_lo <= num_days <= d_hi:
                raise HandBack(7, "odd_dates.csv row %s to %s covers %d-%d days but start_date to %s is %d days"
                               % (r["maturity_from"], r["maturity_to"], d_lo, d_hi,
                                  end_date.isoformat(), num_days))
            return {
                "table": "odd_dates",
                "file": "odd_dates.csv",
                "maturity_from": r["maturity_from"],
                "maturity_to": r["maturity_to"],
                "num_days_from": d_lo,
                "num_days_to": d_hi,
                "tp_pct": r["tp_pct"],
                "description": "odd_dates.csv range %s to %s (%d-%d days)"
                               % (r["maturity_from"], r["maturity_to"], d_lo, d_hi),
            }
    raise HandBack(7, "no row in transfer_pricing.csv or odd_dates.csv covers end date %s (%d days)"
                   % (end_date.isoformat(), num_days))


# ---------------------------------------------------------------------------
# Step 7, forward path: value date earlier or later than T+2 reads the forward rate file
# ---------------------------------------------------------------------------

FORWARD_FILE = "forward_rate_calculator.csv"


def lookup_forward_rate(sheet, currency, value_date, end_date, t_plus_2):
    """The row of forward_rate_calculator.csv for this currency, value date and
    maturity date. Its fwd_fwd_pct stands in for TP. No row = hand back naming
    exactly what was looked for and what the file holds."""
    folder = sheet["folder"]
    path = folder / FORWARD_FILE
    why = ("value date %s is %s than T+2 (%s), so the forward rate is needed"
           % (value_date.isoformat(), "later" if value_date > t_plus_2 else "earlier", t_plus_2.isoformat()))
    if not path.is_file():
        raise HandBack(7, "%s; sheet folder %s has no %s" % (why, folder.name, FORWARD_FILE))
    rows = read_csv(path)
    wanted = (currency, value_date.isoformat(), end_date.isoformat())
    matches = [(n, r) for n, r in enumerate(rows, start=2)
               if (r.get("currency"), r.get("value_date"), r.get("maturity_date")) == wanted]
    if not matches:
        present = ["value_date %s to maturity_date %s" % (r.get("value_date"), r.get("maturity_date"))
                   for r in rows if r.get("currency") == currency]
        raise HandBack(7, "%s; %s in %s has no row for currency %s, value_date %s, maturity_date %s. Rows present for %s: %s"
                       % (why, FORWARD_FILE, folder.name, currency, value_date.isoformat(), end_date.isoformat(),
                          currency, "; ".join(present) or "none"))
    if len(matches) > 1:
        raise HandBack(7, "%s; %s in %s has %d rows for currency %s, value_date %s, maturity_date %s (rows %s)"
                       % (why, FORWARD_FILE, folder.name, len(matches), currency, value_date.isoformat(),
                          end_date.isoformat(), ", ".join(str(n) for n, _ in matches)))
    line_no, row = matches[0]
    if row.get("sheet_date") != sheet["sheet_date"].isoformat():
        raise HandBack(7, "%s row %d carries sheet_date %s, not the received date %s"
                       % (FORWARD_FILE, line_no, row.get("sheet_date"), sheet["sheet_date"].isoformat()))
    rate = parse_decimal(row.get("fwd_fwd_pct"), "%s row %d fwd_fwd_pct" % (FORWARD_FILE, line_no))
    return {
        "table": "forward_rate_calculator",
        "file": FORWARD_FILE,
        "folder": folder.name,
        "row": line_no,
        "currency": currency,
        "value_date": row["value_date"],
        "maturity_date": row["maturity_date"],
        "fwd_fwd_pct": str(rate),
        "description": "%s row %d: currency %s, value_date %s, maturity_date %s, fwd_fwd_pct %s (folder %s)"
                       % (FORWARD_FILE, line_no, currency, row["value_date"], row["maturity_date"], rate, folder.name),
    }


# ---------------------------------------------------------------------------
# Step 8: margin
# ---------------------------------------------------------------------------

def load_margin(margins_path, request_id):
    rows = [r for r in read_csv(margins_path) if r["request_id"] == request_id]
    if not rows:
        raise HandBack(8, "no margin supplied for %s in %s" % (request_id, margins_path))
    if len(rows) > 1:
        raise HandBack(8, "more than one margin row for %s in %s" % (request_id, margins_path))
    margin = parse_decimal(rows[0]["margin_pct"], "margin_pct")
    return {"margin_pct": rows[0]["margin_pct"], "margin_decimal": margin,
            "supplied_by": rows[0].get("supplied_by", "")}


# ---------------------------------------------------------------------------
# Steps 4, 6, 7, 8 per item
# ---------------------------------------------------------------------------

def process_item(item, received, calendar_dir, sheet_cache, sheet_dir, margin):
    """Return the item result dict. Raises HandBack when the item cannot be quoted;
    the values computed before the stop travel with the exception as .partial."""
    result = dict(item)
    try:
        return _process_item(item, result, received, calendar_dir, sheet_cache, sheet_dir, margin)
    except HandBack as exc:
        exc.partial = result
        raise


def _process_item(item, result, received, calendar_dir, sheet_cache, sheet_dir, margin):
    result["purpose"] = item["item_type"]
    result["forward_rate_used"] = False
    currency = item["currency"]

    # Step 4: route
    if currency in HAND_BACK_CURRENCIES:
        raise HandBack(4, "item %d is %s: the rate sheet cannot answer %s, so no rate is computed; hand back for the Treasury/BBSW path"
                       % (item["item_no"], currency, currency))
    if currency not in ALLOWED_CURRENCIES:
        raise HandBack(4, "item %d is %s: not in the allowed list (%s) for v%s"
                       % (item["item_no"], currency, ", ".join(ALLOWED_CURRENCIES), SKILL_VERSION))
    if item["item_type"] == "repayment":
        result["item_outcome"] = "acknowledge"
        result["note"] = "repayment: acknowledged, no quote"
        return result

    holidays, calendar_names = load_holidays(calendar_dir, currency)
    result["calendars"] = list(calendar_names)

    # Step 5: sheet for this currency (folder already resolved for the received date)
    if currency not in sheet_cache:
        sheet_cache[currency] = load_sheet(sheet_dir, received, currency)
    sheet = sheet_cache[currency]

    # Step 6: date checks
    t_plus_2 = add_business_days(received, SPOT_BUSINESS_DAYS, holidays)
    result["t_plus_2"] = t_plus_2.isoformat()
    if sheet["start_date"] != t_plus_2:
        raise HandBack(6, "sheet %s start_date %s is not T+2 (%s) from the received date"
                       % (sheet["folder"].name, sheet["start_date"].isoformat(), t_plus_2.isoformat()))
    requested_vd = date.fromisoformat(item["value_date"])
    vd = requested_vd
    adjustments = []
    # Owner correction 2026-10-14 (acceptance rule v1.1): a value date before
    # the received date goes back to BH; a weekend or holiday value date moves
    # to the next business day; a value date earlier than T+2 is NOT moved to
    # T+2 but priced from the forward rate, like a value date later than T+2.
    if requested_vd < received:
        raise HandBack(6, "item %d: value date %s is before the received date %s"
                       % (item["item_no"], requested_vd.isoformat(), received.isoformat()))
    if not is_business_day(vd, holidays):
        moved = next_business_day(vd, holidays)
        adjustments.append({
            "field": "value_date", "from": vd.isoformat(), "to": moved.isoformat(),
            "reason": "The value date you asked for, %s, is %s, so this quote uses the next business day, %s."
                      % (long_date(vd), holiday_reason(vd, calendar_dir, calendar_names), long_date(moved)),
        })
        vd = moved
    forward = vd != t_plus_2
    side = "later" if vd > t_plus_2 else "earlier"
    result["value_date_requested"] = requested_vd.isoformat()
    result["value_date"] = vd.isoformat()
    result["value_date_basis"] = ("%s than T+2: forward rate path" % side if forward else "T+2: rate sheet tables")

    if "tenor_business_days" in item:
        tenor = item["tenor_business_days"]
        end = add_business_days(vd, tenor, holidays)
        result["end_date_requested"] = None
        result["end_date_basis"] = "%d business days counted forward from the value date" % tenor
    else:
        requested_end = date.fromisoformat(item["end_date"])
        end = requested_end
        if not is_business_day(end, holidays):
            moved = next_business_day(end, holidays)
            adjustments.append({
                "field": "end_date", "from": end.isoformat(), "to": moved.isoformat(),
                "reason": "The end date you asked for, %s, is %s, so this quote runs to the next business day, %s."
                          % (long_date(end), holiday_reason(end, calendar_dir, calendar_names), long_date(moved)),
            })
            end = moved
        tenor = business_days_between(vd, end, holidays)
        result["end_date_requested"] = requested_end.isoformat()
        result["end_date_basis"] = "end date as requested" if end == requested_end else "end date moved to the next business day"
    if end <= vd:
        raise HandBack(6, "item %d: end date %s is not after value date %s"
                       % (item["item_no"], end.isoformat(), vd.isoformat()))
    result["end_date"] = end.isoformat()
    result["tenor_business_days"] = tenor
    result["adjustments"] = adjustments

    # Step 7: maturity and row lookup
    if forward:
        # Value date earlier or later than T+2: the sheet tables start at T+2,
        # so the forward rate for this exact value date and maturity stands in for TP.
        fwd = lookup_forward_rate(sheet, currency, vd, end, t_plus_2)
        result["forward_rate_used"] = True
        result["forward_rate_pct"] = fwd["fwd_fwd_pct"]
        result["lookup"] = fwd
        result["num_days"] = (end - sheet["start_date"]).days
        result["num_days_basis"] = ("sheet start_date %s to end date; FORWARD RATE PATH: requested value date %s is %s than T+2"
                                    % (sheet["start_date"].isoformat(), vd.isoformat(), side))
        result["forward_tenor_days"] = (end - vd).days  # the forward rate's own period: requested value date to end date
        result["tenor_calendar_days"] = (end - vd).days  # what the customer sees
        result["tp_pct"] = None
        cost_of_funds = parse_decimal(fwd["fwd_fwd_pct"], "fwd_fwd_pct")
        result["cost_of_funds_source"] = "%s fwd_fwd_pct, in place of TP" % FORWARD_FILE
    else:
        num_days = (end - sheet["start_date"]).days
        result["num_days"] = num_days
        result["num_days_basis"] = "sheet start_date to end date"
        result["tenor_calendar_days"] = (end - vd).days  # what the customer sees
        row = lookup_row(sheet, end, num_days)
        result["lookup"] = row
        result["forward_rate_pct"] = None
        result["tp_pct"] = row["tp_pct"]
        cost_of_funds = parse_decimal(row["tp_pct"], "tp_pct")
        result["cost_of_funds_source"] = "%s tp_pct" % row["file"]
    result["cost_of_funds_pct"] = str(cost_of_funds)

    # Step 8: rate
    all_in_4dp = (cost_of_funds + margin["margin_decimal"]).quantize(FOUR_DP)
    customer_2dp = round_half_down_2dp(all_in_4dp)
    result["margin_pct"] = margin["margin_pct"]
    result["margin_supplied_by"] = margin["supplied_by"]
    result["all_in_4dp"] = str(all_in_4dp)
    result["customer_rate_2dp"] = str(customer_2dp)
    result["customer_rate"] = "%s%%" % customer_2dp
    result["rounding"] = "half down (exact 5 in the third decimal rounds down)"
    result["item_outcome"] = "quote"
    return result


# ---------------------------------------------------------------------------
# Step 9: fill the template
# ---------------------------------------------------------------------------

def load_template(path=TEMPLATE_PATH):
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"<!--.*?-->\s*", "", text, flags=re.DOTALL)
    sections = {}
    name = None
    for line in text.splitlines():
        m = re.fullmatch(r"=== (\w+) ===", line.strip())
        if m:
            name = m.group(1)
            sections[name] = []
        elif name is not None:
            sections[name].append(line)
    out = {k: "\n".join(v).strip("\n") for k, v in sections.items()}
    for required in ("header", "quoted_item", "acknowledged_item", "adjustment_line", "footer"):
        if required not in out:
            raise HandBack(9, "quote template is missing the %s section" % required)
    return out


def fill_draft(request_id, items, sheet_date, template):
    parts = [template["header"].format(request_id=request_id)]
    for it in items:
        if it["item_outcome"] == "acknowledge":
            parts.append(template["acknowledged_item"].format(
                item_no=it["item_no"], purpose=it["purpose"], currency=it["currency"], amount=format_amount(it["amount"]),
                value_date_long=long_date(date.fromisoformat(it["value_date"]))))
        else:
            notes = "\n".join(template["adjustment_line"].format(reason=a["reason"])
                              for a in it["adjustments"])
            parts.append(template["quoted_item"].format(
                item_no=it["item_no"], purpose=it["purpose"], purpose_title=it["purpose"].capitalize(),
                currency=it["currency"], amount=format_amount(it["amount"]),
                value_date_long=long_date(date.fromisoformat(it["value_date"])),
                end_date_long=long_date(date.fromisoformat(it["end_date"])),
                tenor_calendar_days=it["tenor_calendar_days"],
                customer_rate=it["customer_rate_2dp"],
                adjustment_lines=notes).rstrip("\n"))
    parts.append(template["footer"])
    return "\n\n".join(parts) + "\n"


# ---------------------------------------------------------------------------
# Step 11: draft check
# ---------------------------------------------------------------------------

MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
DRAFT_DATE_RE = re.compile(
    r"\b(\d{4}-\d{2}-\d{2})\b"
    r"|\b(\d{1,2})(?:st|nd|rd|th)?\s+(%s)\s+(\d{4})\b"
    r"|\b(%s)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b" % (MONTHS, MONTHS))


def dates_and_numbers_in_draft(text, identifiers):
    for ident in identifiers:
        text = text.replace(ident, " ")
    dates = []
    spans = []
    for m in DRAFT_DATE_RE.finditer(text):
        if m.group(1):
            d = date.fromisoformat(m.group(1))
        elif m.group(2):
            d = date(int(m.group(4)), MONTHS.split("|").index(m.group(3)) + 1, int(m.group(2)))
        else:
            d = date(int(m.group(7)), MONTHS.split("|").index(m.group(5)) + 1, int(m.group(6)))
        dates.append(d)
        spans.append(m.span())
    for start, end in reversed(spans):
        text = text[:start] + " " + text[end:]
    numbers = [Decimal(t.replace(",", "")) for t in NUMBER_RE.findall(text)]
    return dates, numbers


def check_draft(draft, items, sheet_date, request_id):
    """Every number and date in the draft must equal a computed value, and the
    computed values that matter must all be present. Any mismatch = reject."""
    allowed_dates = set()   # owner decision 2026-10-13: the draft does not name the sheet date
    allowed_numbers = set()
    required_dates = set()
    required_numbers = set()
    identifiers = {request_id}
    for it in items:
        identifiers.add(it["facility_ref"])
        allowed_numbers.add(Decimal(it["item_no"]))
        amount = Decimal(it["amount"])
        allowed_numbers.add(amount)
        required_numbers.add(amount)
        vd = date.fromisoformat(it["value_date"])
        allowed_dates.add(vd)
        required_dates.add(vd)
        if it["item_outcome"] == "quote":
            end = date.fromisoformat(it["end_date"])
            allowed_dates.add(end)
            required_dates.add(end)
            for a in it["adjustments"]:
                allowed_dates.add(date.fromisoformat(a["from"]))
            for key in ("tenor_calendar_days", "customer_rate_2dp"):
                allowed_numbers.add(Decimal(it[key]))
                required_numbers.add(Decimal(it[key]))

    found_dates, found_numbers = dates_and_numbers_in_draft(draft, sorted(identifiers, key=len, reverse=True))
    problems = []
    for d in found_dates:
        if d not in allowed_dates:
            problems.append("date %s in draft is not a computed value" % d.isoformat())
    for n in found_numbers:
        if n not in allowed_numbers:
            problems.append("number %s in draft is not a computed value" % n)
    for d in required_dates:
        if d not in found_dates:
            problems.append("computed date %s is missing from the draft" % d.isoformat())
    for n in required_numbers:
        if n not in found_numbers:
            problems.append("computed value %s is missing from the draft" % n)
    return {
        "status": "pass" if not problems else "reject",
        "dates_checked": len(found_dates),
        "numbers_checked": len(found_numbers),
        "problems": problems,
    }


# ---------------------------------------------------------------------------
# Pre-send check: source values, not ticks (owner decision 2026-10-08)
# ---------------------------------------------------------------------------

def pre_send_check_text(result):
    lines = ["PRE-SEND CHECK: %s (source values, not ticks)" % result["request_id"],
             "outcome: %s" % result["outcome"],
             "received: %s" % result["received"]]
    sheet = result.get("sheet")
    if sheet:
        lines.append("sheet date used: %s (folder %s, start_date %s, T+2 from received %s)"
                     % (sheet["sheet_date"], sheet["folder"], sheet["start_date"], sheet.get("t_plus_2", "n/a")))
    else:
        lines.append("sheet date used: none (stopped before the sheet was read)")
    for it in result["items"]:
        lines.append("")
        lines.append("item %d: %s %s %s" % (it["item_no"], it["item_type"], it["currency"], format_amount(it["amount"])))
        outcome = it.get("item_outcome", "hand_back")
        lines.append("  item outcome: %s" % outcome)
        if outcome == "hand_back":
            lines.append("  reason: %s" % it.get("hand_back_reason", ""))
            continue
        if outcome == "acknowledge":
            lines.append("  repayment acknowledged on %s; no rate" % it["value_date"])
            continue
        row = it["lookup"]
        lines.append("  table and row read: %s" % row["description"])
        if it["forward_rate_used"]:
            lines.append("  TP value: none; the forward rate stands in for TP")
            lines.append("  forward rate (fwd_fwd_pct): %s" % it["forward_rate_pct"])
        else:
            lines.append("  TP value: %s" % it["tp_pct"])
        lines.append("  margin: %s (supplied by %s; REVIEWER CONFIRMS the margin before send)" % (it["margin_pct"], it["margin_supplied_by"]))
        lines.append("  all-in 4 dp: %s" % it["all_in_4dp"])
        lines.append("  customer figure 2 dp, rounded half down: %s" % it["customer_rate"])
        vd_note = "as requested" if it["value_date"] == it["value_date_requested"] else "requested %s" % it["value_date_requested"]
        if it["forward_rate_used"]:
            vd_note += "; %s than T+2, forward rate path" % ("later" if it["value_date"] > it["t_plus_2"] else "earlier")
        lines.append("  value date: %s (%s; T+2 = %s)" % (it["value_date"], vd_note, it["t_plus_2"]))
        if it["end_date_requested"] and it["end_date_requested"] != it["end_date"]:
            end_note = "requested %s; moved" % it["end_date_requested"]
        else:
            end_note = it["end_date_basis"]
        lines.append("  end date: %s (%s)" % (it["end_date"], end_note))
        for a in it["adjustments"]:
            lines.append("  adjustment: %s %s -> %s: %s" % (a["field"], a["from"], a["to"], a["reason"]))
        lines.append("  tenor in business days: %d" % it["tenor_business_days"])
        lines.append("  num_days (%s): %d" % (it["num_days_basis"], it["num_days"]))
        if it["forward_rate_used"]:
            lines.append("  forward rate used: yes, %s (%s row %d in folder %s)"
                         % (it["forward_rate_pct"], row["file"], row["row"], row["folder"]))
            lines.append("  forward rate tenor: %d calendar days (requested value date %s to end date %s)"
                         % (it["forward_tenor_days"], it["value_date"], it["end_date"]))
        else:
            lines.append("  forward rate used: no")
    lines.append("")
    dc = result.get("draft_check")
    if dc:
        lines.append("draft check (step 11): %s; %d dates and %d numbers in the draft compared with computed values"
                     % (dc["status"], dc["dates_checked"], dc["numbers_checked"]))
        for p in dc["problems"]:
            lines.append("  problem: %s" % p)
    else:
        lines.append("draft check (step 11): not run (no quote draft)")
    if result.get("hand_back_reason"):
        lines.append("hand back: %s" % result["hand_back_reason"])
    lines.append("send capability: none. Nothing was sent, connected or looked up outside the fixture files.")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Main run
# ---------------------------------------------------------------------------

def run(form_path, received, sheet_dir, calendar_dir, margins_path, out_dir, requests_dir=None):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    form_path = Path(form_path)
    if requests_dir is None:
        requests_dir = form_path.resolve().parent.parent / "requests"
    requests_dir = Path(requests_dir)

    result = {
        "skill": "rate-quote",
        "skill_version": SKILL_VERSION,
        "route": "A script-first (steps 2-9 and 11 by code, forward rate path included; step 10 skipped)",
        "form_file": str(form_path),
        "received": received.isoformat(),
        "request_id": None,
        "outcome": None,
        "hand_back_reason": None,
        "hand_back_step": None,
        "sheet": None,
        "grounding": None,
        "items": [],
        "draft_check": None,
        "outputs": {},
        "send_attempted": False,
    }
    draft = None
    items = []

    try:
        with open(form_path, encoding="utf-8") as fh:
            raw_form = json.load(fh)
    except (OSError, ValueError) as exc:
        raise SystemExit("cannot read form %s: %s" % (form_path, exc))

    try:
        # Step 2
        try:
            form = validate_form(raw_form)
        except HandBack as exc:
            write_json(out_dir / "form-validated.json",
                       {"status": "invalid", "error": exc.reason, "form": raw_form})
            raise
        result["request_id"] = form["request_id"]
        write_json(out_dir / "form-validated.json", dict(form, status="valid"))

        # Step 3
        request_file = requests_dir / ("%s.txt" % form["request_id"])
        if not request_file.is_file():
            raise HandBack(3, "request text %s not found; cannot ground the form" % request_file)
        result["request_file"] = str(request_file)
        result["grounding"] = ground_form(form, request_file.read_text(encoding="utf-8"))

        # Step 4 (currency route) runs per item; step 5 (sheet) only if any item needs a quote
        needs_sheet = any(it["item_type"] in QUOTED_ITEM_TYPES
                          and it["currency"] in ALLOWED_CURRENCIES for it in form["items"])
        sheet_folder = None
        margin = None
        if needs_sheet:
            sheet_folder = resolve_sheet_folder(sheet_dir, received)
            margin = load_margin(margins_path, form["request_id"])

        sheet_cache = {}
        for item in form["items"]:
            try:
                items.append(process_item(item, received, calendar_dir, sheet_cache, sheet_folder, margin))
            except HandBack as exc:
                failed = dict(getattr(exc, "partial", None) or item,
                              item_outcome="hand_back", hand_back_reason=exc.reason)
                items.append(failed)
                result["items"] = items
                result["sheet"] = sheet_summary(sheet_cache, items)
                raise
        result["items"] = items
        result["sheet"] = sheet_summary(sheet_cache, items)

        quoted = [it for it in items if it["item_outcome"] == "quote"]
        if not quoted:
            result["outcome"] = "acknowledge"
            draft = fill_draft(form["request_id"], items, received, load_template())
        else:
            # Step 9
            draft = fill_draft(form["request_id"], items, received, load_template())
            # Step 11
            result["draft_check"] = check_draft(draft, items, received, form["request_id"])
            if result["draft_check"]["status"] != "pass":
                raise HandBack(11, "draft check rejected the draft: " + "; ".join(result["draft_check"]["problems"]))
            result["outcome"] = "quote_draft"
    except HandBack as exc:
        result["outcome"] = "hand_back"
        result["hand_back_reason"] = exc.reason
        result["hand_back_step"] = exc.step
        result["items"] = items
        if draft is None:
            draft = ("No quote drafted for %s.\nHand back at step %s: %s\n"
                     % (result["request_id"] or form_path.name, exc.step, exc.reason))

    pre_send = pre_send_check_text(result)
    (out_dir / "quote-draft.txt").write_text(draft, encoding="utf-8")
    (out_dir / "pre-send-check.txt").write_text(pre_send, encoding="utf-8")
    result["outputs"] = {name: str(out_dir / name) for name in
                         ("form-validated.json", "result.json", "quote-draft.txt", "pre-send-check.txt")}
    write_json(out_dir / "result.json", result)
    print(pre_send, end="")
    print("outputs written to %s" % out_dir)
    return result


def sheet_summary(sheet_cache, items):
    if not sheet_cache:
        return None
    sheet = next(iter(sheet_cache.values()))
    t_plus_2 = next((it["t_plus_2"] for it in items if it.get("t_plus_2")), None)
    return {
        "sheet_date": sheet["sheet_date"].isoformat(),
        "folder": sheet["folder"].name,
        "start_date": sheet["start_date"].isoformat(),
        "t_plus_2": t_plus_2,
    }


def write_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2, default=str) + "\n", encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--form", required=True, help="step-1 form JSON, e.g. fixtures/forms/REQ-001.json")
    parser.add_argument("--received", required=True, help="date the request was received, YYYY-MM-DD")
    parser.add_argument("--sheet-dir", required=True,
                        help="folder holding one rate_sheet_YYYYMMDD folder per sheet date "
                             "(each with transfer_pricing.csv, odd_dates.csv and, when needed, forward_rate_calculator.csv)")
    parser.add_argument("--calendars", required=True, help="folder holding US.txt, SG.txt, ... holiday lists")
    parser.add_argument("--margins", required=True, help="margins.csv with request_id, margin_pct, supplied_by")
    parser.add_argument("--out", required=True, help="output folder; the only place the script writes")
    parser.add_argument("--requests", default=None,
                        help="folder holding <request_id>.txt (default: the requests folder beside the form's folder)")
    args = parser.parse_args(argv)
    try:
        received = date.fromisoformat(args.received)
    except ValueError:
        parser.error("--received must be YYYY-MM-DD")
    for label, path in (("--sheet-dir", args.sheet_dir), ("--calendars", args.calendars)):
        if not Path(path).is_dir():
            parser.error("%s %s is not a folder" % (label, path))
    if not Path(args.margins).is_file():
        parser.error("--margins %s is not a file" % args.margins)
    result = run(args.form, received, args.sheet_dir, args.calendars, args.margins, args.out, args.requests)
    return 2 if result["outcome"] == "hand_back" else 0


if __name__ == "__main__":
    sys.exit(main())
