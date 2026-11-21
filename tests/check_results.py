"""Parse freqtrade lookahead/recursive output. Stdlib only. Exit 1 on failure.

usage: check_results.py lookahead CSV [--freqai]
       check_results.py recursive LOG [--freqai]
"""
import csv
import re
import sys

# docs/recursive-analysis.md gives no pass/fail number ("assess per indicator"),
# so ruling R3 applies: fail when any indicator differs by more than 0.5% at the
# strategy's own startup_candle_count column.
RECURSIVE_MAX_VARIANCE_PCT = 0.5
STRATEGY_COL = "(from strategy)"
# --freqai: besides the docs-named set_freqai_targets() columns (&-prefixed), lookahead-analysis flags FreqAI outputs and the
# signal columns built from them. Observed on 2026.10: do_predict, enter_long, exit_long, enter_tag, exit_tag.
# enter_short, exit_short, DI_values are symmetric but unobserved. Ignored ONLY when at least one & column is also
# flagged (they differ because the model is retrained per slice); biased_entry/exit_signals counts still fail.
FREQAI_DERIVED = {"do_predict", "DI_values", "enter_long", "enter_short", "exit_long", "exit_short", "enter_tag", "exit_tag"}


def lookahead(path, freqai):
    with open(path, newline="") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        return False, "lookahead: FAIL (empty result)"
    row = rows[0]
    inds = [i for i in row["biased_indicators"].split(",") if i]
    if freqai:  # &-prefixed targets: documented false positives; FREQAI_DERIVED: observed, see above
        has_target = any(i.startswith("&") for i in inds)
        inds = [i for i in inds if not i.startswith("&") and not (has_target and i in FREQAI_DERIVED)]
    entry, exit_ = int(row["biased_entry_signals"]), int(row["biased_exit_signals"])
    biased = entry > 0 or exit_ > 0 or (bool(inds) if freqai else row["has_bias"] == "True")
    detail = f"entry={entry} exit={exit_} indicators={','.join(inds) or '-'}"
    return (not biased), f"lookahead: {'BIAS' if biased else 'OK'} ({detail})"


def _cells(line):
    return [c.strip() for c in line.strip().strip("│┃").replace("┃", "│").split("│")]


def recursive(path, freqai=False):
    with open(path, encoding="utf-8") as fh:
        lines = [ln for ln in fh if ln.strip().startswith(("┃", "│"))]
    header = next((_cells(ln) for ln in lines if "Indicators" in ln), None)
    if not header:
        return False, "recursive: FAIL (no result table found)"
    col = next((i for i, h in enumerate(header) if STRATEGY_COL in h), None)
    if col is None:
        return False, "recursive: FAIL (no startup_candle_count column in table)"
    bad = []
    seen = 0
    for ln in lines:
        row = _cells(ln)
        if row == header:
            continue
        if freqai and row[0].startswith("&"):  # model outputs: retrained on different data per startup count, not recursion evidence
            continue
        if len(row) != len(header):
            bad.append(f"malformed row {row[0] if row else '?'}")
            continue
        seen += 1
        raw = row[col]
        if raw == "-":
            continue
        m = re.fullmatch(r"(-?[\d.]+)%", raw)
        if not m or abs(float(m.group(1))) > RECURSIVE_MAX_VARIANCE_PCT:
            bad.append(f"{row[0]}={raw}")
    startup = header[col].split()[0]
    if not seen and freqai and not bad:  # only model outputs listed: nothing to assess, say so instead of passing silently
        return True, "recursive: NOT ASSESSED (--freqai: table lists only &-targets; features are not testable, see freqtrade-freqai)"
    if not seen:
        return False, "recursive: FAIL (table has no indicator rows)"
    if bad:
        return False, f"recursive: FAIL (startup={startup}, >{RECURSIVE_MAX_VARIANCE_PCT}%: {', '.join(bad)})"
    return True, f"recursive: OK (startup={startup}, all indicators <= {RECURSIVE_MAX_VARIANCE_PCT}%)"


if __name__ == "__main__":
    kind, path = sys.argv[1], sys.argv[2]
    try:
        ok, msg = lookahead(path, "--freqai" in sys.argv) if kind == "lookahead" else recursive(path, "--freqai" in sys.argv)
    except (OSError, KeyError, ValueError) as exc:
        ok, msg = False, f"{kind}: FAIL ({type(exc).__name__}: {exc})"
    print(msg)
    sys.exit(0 if ok else 1)
