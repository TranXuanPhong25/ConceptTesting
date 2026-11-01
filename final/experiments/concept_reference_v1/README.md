# Concept benchmark với reference oracle

User đã làm rõ mục tiêu: đo **concept giúp sinh input bắt lỗi như thế nào**, giữ
oracle cố định và giữ nguyên bộ PUT. Bản này ở folder riêng; bản plain ban đầu và
v7/v11 không bị sửa.

```text
164 HumanEval specs → 10 PUT/task → base tests → frozen cohort.json
                                                ↓ tái sử dụng mọi lần sau
base traces + PUT → boundary / partition / CFG / def-use → concept cards
                                                     ↘ cross-PUT contrast
plain / classical / contrastive / placebo / toolinput → INPUTS ONLY
                      → freeze inputs → reference outputs → chạy trên tất cả PUT
```

- `CoreModel`: dùng chung interface ở `final/core_model.py`; `model.py` là adapter
  context-aware cho model người dùng chọn. Không ghi endpoint/key vào artifacts.
- `python-graphs`: CFG và static def-use graph; `coverage.py`: base lines/arcs;
  `NetworkX`: xử lý CFG; `Hypothesis`: pool input từ các base values.
- Reference oracle cung cấp expected output. EvalPlus contracts lọc input domain;
  tolerance và polynomial property xử lý float/non-unique roots.
- So sánh chính `classical` vs `plain` cùng valid input budget/task; placebo,
  toolinput, witness-only và contrastive là control/secondary. Không dùng số lượng
  test khác nhau hoặc chất lượng LLM expected output làm lý do cho gain.

`cohort.json` được sinh và đóng băng **một lần** tại
`final/out/cohorts/qwen35_27b_humaneval164/`. Chạy concept experiment mới chỉ đổi
`--out`, giữ nguyên `--cohort`. Source/tester thay đổi không buộc sinh lại PUT.

```bash
uv pip install --python final/.venv/bin/python -r final/experiments/concept_reference_v1/requirements.lock.txt
final/.venv/bin/python -m pytest final/tests final/experiments/concept_reference_v1/tests -q
bash final/experiments/concept_reference_v1/launch.sh
```

Launcher source `scripts/research_env.sh` im lặng và nạp endpoint từ env file riêng
ngoài repo, rồi chạy detached. Kiểm tra `final/out/concept_reference_v1/status.json`
và `run.log`. Resume bằng cùng launcher; có exclusive locks và checkpoints, không
gọi lại request có usage unknown. Chỉ score có thể dùng `--phase score` sau khi
input generation freeze hoàn tất. Run mặc định đầy đủ **164 task**, 2 workers.

`packet.json` lưu concept/CFG/DFG/base evidence; `inputs.json` lưu các arm; sau
generation freeze mới có `oracle_valid.json`, per-PUT `evaluation/`, `result.json`,
`summary.json`, `REPORT.md`. Xem [PREREG.md](PREREG.md) và [RESEARCH.md](RESEARCH.md).
