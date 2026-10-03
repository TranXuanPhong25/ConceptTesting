"""Join pass 1 (ABIs) + pass 2 (uses-sdk, AVD per bug) + Google's sys-img manifests -> summary.json + stdout."""
import json, re
from collections import Counter, defaultdict
from pathlib import Path

H = Path(__file__).resolve().parent
abis = {r["apk"]: r["abis"] for r in json.load(open(H / "apk_abis.json"))}
p2 = [json.loads(l) for l in open(H / "pass2.jsonl")]
sdk = {r["apk"]: r.get("uses_sdk") for r in p2 if "apk" in r}
AVD_API = {"5.0": 21, "5.1": 22, "6.0": 23, "7.0": 24, "7.1": 25, "8.0": 26, "8.1": 27, "9.0": 28, "10.0": 29}
avd = {}
for r in p2:
    if "script" in r and r["avd"]:
        m = re.match(r"Artifact/(\w+)/(\d+)", r["script"])
        avd[(m.group(1), m.group(2))] = r["avd"][0]


def cls(a):
    if not a: return "pure Java (no lib/*.so)"
    if "arm64-v8a" in a: return "has arm64-v8a"
    if set(a) <= {"armeabi", "armeabi-v7a"}: return "32-bit ARM only"
    if "x86" in a or "x86_64" in a: return "no arm64; x86 (+32-bit ARM/mips)" if set(a) - {"x86", "x86_64"} else "x86 only"
    return "other"


def arm64_images():
    out = {}
    for tag, tid in (("android", "default"), ("google_apis", "google_apis")):
        x = (H / f"sysimg_{tag}.xml").read_text()
        for api in range(21, 30):
            out.setdefault(api, []).extend(
                f"{tid} r{m}" for m in re.findall(
                    rf'path="system-images;android-{api};{tid};arm64-v8a">.*?<major>(\d+)</major>', x, re.S))
    return out


rows = []
for apk, a in abis.items():
    d = apk.split("/")[1]
    m = re.match(r"(\d+)", apk.split("/")[-1])
    bug = m.group(1) if m else None
    av = avd.get((d, bug)) if bug else None
    api = AVD_API.get(av.rsplit("_", 1)[-1]) if av else None
    rows.append({"apk": apk, "dir": d, "bug": bug, "abis": a, "class": cls(a), "uses_sdk": sdk.get(apk),
                 "avd": av, "avd_api": api})

summary = {
    "n_apks": len(rows),
    "abi_class": Counter(r["class"] for r in rows),
    "abi_class_by_dir": {d: Counter(r["class"] for r in rows if r["dir"] == d) for d in sorted({r["dir"] for r in rows})},
    "avd_by_bug_script": Counter(avd.values()),
    "apks_by_avd_api": Counter(r["avd_api"] for r in rows),
    "minSdk": Counter((r["uses_sdk"] or {}).get("minSdkVersion") for r in rows),
    "targetSdk": Counter((r["uses_sdk"] or {}).get("targetSdkVersion") for r in rows),
    "official_arm64_images_api21_29": arm64_images(),
    "no_arm64_native_apks": [r["apk"] for r in rows if r["class"] not in ("pure Java (no lib/*.so)", "has arm64-v8a")],
}
(H / "summary.json").write_text(json.dumps({**summary, "apks": rows}, indent=1, default=str))
print(json.dumps({k: v for k, v in summary.items() if k != "no_arm64_native_apks"}, indent=1, default=str))
print("APKs without an arm64-v8a native lib (of those with native code):", len(summary["no_arm64_native_apks"]))

# bug-level: a failure-based oracle needs BOTH the buggy APK and the fixed APK to run
ok = lambda c: c in ("pure Java (no lib/*.so)", "has arm64-v8a")
buggy = {r["bug"]: r for r in rows if r["dir"] in ("andror2plus_apks", "fbaa_apks", "unseen_data_apks") and r["bug"]}
fixed = {r["bug"]: r for r in rows if r["dir"] == "fixed_apks" and r["bug"]}
pairs = sorted(set(buggy) & set(fixed))
pc = Counter((ok(buggy[b]["class"]) and ok(fixed[b]["class"])) for b in pairs)
print(f"bugs with buggy+fixed APKs: {len(pairs)}; both arm64-runnable ABIs: {pc[True]}; "
      f"at least one APK needs x86 or 32-bit ARM: {pc[False]}; buggy APKs without a fixed APK: {len(set(buggy) - set(fixed))}")
