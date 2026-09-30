#!/usr/bin/env python3
"""Refresh Wise's live fee figures for the Send Money Home app.

Wise is the only provider with a publicly reachable price feed
(wis.com gateway widget API, no token needed). Every other provider
(Remitly, Sendwave, Lemfi, Western Union, MoneyGram) publishes no public
feed, so they stay manually edited in the app.

Writes wise-live.json next to index.html:
  {updated, source, amount, corridors: {CUR: {feeCad, feePct, marginPct, midRate}}}

Safe to run on a schedule: a failed corridor keeps its previous value,
and if every corridor fails the old file is left untouched.
"""
import json, os, sys, urllib.request, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "wise-live.json")
OUT = os.path.normpath(OUT)
AMOUNT = 500
CORRIDORS = ["NGN", "GHS", "KES", "INR", "PHP", "USD", "GBP", "EUR"]
URL = "https://wise.com/gateway/v1/price?sourceAmount={a}&sourceCurrency=CAD&targetCurrency={c}"
UA = {"User-Agent": "Mozilla/5.0 (SendMoneyHome/1.0)"}

def fetch(cur):
    req = urllib.request.Request(URL.format(a=AMOUNT, c=cur), headers=UA)
    with urllib.request.urlopen(req, timeout=25) as r:
        data = json.load(r)
    opts = [o for o in data
            if o.get("payInMethod") == "BANK_TRANSFER"
            and o.get("payOutMethod") == "BANK_TRANSFER"]
    if not opts:
        raise RuntimeError("no BANK_TRANSFER->BANK_TRANSFER option")
    o = opts[0]
    return {
        "feeCad": round(float(o["flatFee"]), 2),
        "feePct": round(float(o.get("variableFeePercent") or 0), 3),
        "marginPct": 0,
        "midRate": float(o["midRate"]),
    }

def main():
    prev = {}
    if os.path.exists(OUT):
        try:
            prev = json.load(open(OUT)).get("corridors", {})
        except Exception:
            prev = {}
    corridors, failed = {}, []
    for cur in CORRIDORS:
        try:
            corridors[cur] = fetch(cur)
            print(f"{cur}: fee CA${corridors[cur]['feeCad']} + {corridors[cur]['feePct']}%")
        except Exception as e:
            failed.append(cur)
            if cur in prev:
                corridors[cur] = prev[cur]
                print(f"{cur}: FAILED ({e}) - kept previous")
            else:
                print(f"{cur}: FAILED ({e}) - no previous data")
    if not corridors:
        print("All corridors failed; leaving old file untouched.")
        return 1
    out = {
        "updated": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source": "Wise (wise.com gateway price feed)",
        "referenceAmountCad": AMOUNT,
        "note": "feeCad = flat fee, feePct = variable %, marginPct = 0 (Wise uses the mid-market rate)",
        "corridors": corridors,
    }
    json.dump(out, open(OUT, "w"), indent=2)
    print(f"Wrote {OUT} ({len(corridors)} corridors, {len(failed)} failed)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
