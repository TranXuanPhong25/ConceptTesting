"""Paper-style M/E summary (Tables 6/8/9) from the evaluation logs. usage: python3 run/summarize.py [log...]"""
import glob, re, sys

KEYS = {"M": "reported test passed on buggy but failed on fixed", "E": "reported test passed on fixed but failed on buggy",
        "TN": "reported test passed on both", "FP": "reported test failed on both"}


def summarize(log):
    prev = dict.fromkeys(KEYS, 0)
    per_method = []
    for block in open(log).read().split("INFO - Processing Project:")[1:]:
        cur = dict(prev)
        for k, text in KEYS.items():
            found = re.findall(re.escape(text) + r": (\d+)", block)
            if found:
                cur[k] = int(found[-1])  # counters in the log are cumulative
        ran = re.search(r"buggy passed (\w+), fixed passed (\w+)", block)
        # a run that failed but produced an empty error report: its per-test outcomes are unknown, yet the
        # upstream counters then score every test passing on the other version as M (or E) -> exclude it
        glitch = bool(ran) and any(ran.group(j) == "False" and f"{s} error empty" in block for j, s in ((1, "buggy"), (2, "fixed")))
        per_method.append({**{k: cur[k] - prev[k] for k in KEYS}, "glitch": glitch})
        prev = cur
    def line(ms, label):
        t = {k: sum(m[k] for m in ms) for k in KEYS}
        n = sum(t.values())
        pct = lambda x: f"{x} ({100 * x / n:.2f}%)" if n else str(x)
        return (f"{label}: methods={len(ms)} compiled_tests={n} | M={pct(t['M'])} E={pct(t['E'])} FP={pct(t['FP'])} "
                f"red-precision={t['E'] / max(1, t['E'] + t['FP']):.3f} | methods with >=1 M: {sum(m['M'] > 0 for m in ms)}, "
                f">=1 E: {sum(m['E'] > 0 for m in ms)}")
    clean = [m for m in per_method if not m["glitch"]]
    return line(per_method, "raw  ") + "\n   " + line(clean, f"clean (excl. {len(per_method) - len(clean)} glitched)")


if __name__ == "__main__":
    for log in sys.argv[1:] or sorted(glob.glob("data/rq1/logs/*.log")):
        print(log.split("non_private_or_default_")[-1], "\n  ", summarize(log))
