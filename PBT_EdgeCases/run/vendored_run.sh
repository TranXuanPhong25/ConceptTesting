#!/usr/bin/env bash
# Authors' own runner (`pbteval run pbt|ebt --canonical`, file-level: a file "detects" if it fails on the HumanEval
# canonical solution; no validity filter) over every generated dir. Runs inside the exec container:
#   MODE=exec bash run/dock.sh bash vendored_run.sh
# One scratch cwd per dir (the runner keeps a cache file in its cwd).
set -u
mkdir -p /out/vendored
for d in /work/gen/*/k*; do
  arm=$(basename "$(dirname "$d")"); k=$(basename "$d"); t=pbt; [ "$arm" = ebt ] && t=ebt
  log=/out/vendored/${arm}_${k}.log
  [ -s "$log" ] && grep -q "Pass rate" "$log" && continue
  w=/tmp/w_${arm}_${k}; mkdir -p $w/output/$t/gemini
  ln -sfn /work/data $w/dataset; ln -sfn /vendor/prompts $w/prompts; ln -sfn "$d" $w/output/$t/gemini/${arm}_${k}
  echo "cd $w && python -m pbteval.cli run $t --canonical --model gemini/${arm}_${k} > $log 2>&1"
done | xargs -P "${WORKERS:-6}" -I{} bash -c '{}'
echo vendored done
