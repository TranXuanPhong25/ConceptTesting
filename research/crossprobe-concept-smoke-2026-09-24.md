# CrossProbe failure-semantic concept smoke test

## Scope

This is a four-case feasibility check using the released [CrossProbe artifact](https://github.com/CrossProbe2024/CrossProbe) at commit `7a413c2ab34e160f98b3d7751c960f447e9f5717`, not a reproduction of [CrossProbe's ISSTA 2025 results](https://hguandl.github.io/publications/crossprobe/issta25main-p1868-p-cc490847f5-128754-final.pdf). The source cases were chosen because three run on CPU and one has a small CPU-compatible transfer, despite its source MPS bug requiring unavailable hardware.

Both prompts gave Gemini 3 Flash the same released source reproducer and an API correspondence. The `semantic` arm additionally received a manually written card specifying the input edge case and observable relation. The model returned standalone target-framework code. All eight outputs were read before execution and then run in isolated, timed processes with PyTorch `2.4.1+cpu` and TensorFlow CPU `2.17.1`. No GPU was available. This pilot tests transfer fidelity; it does not establish new framework bugs.

| Source case → target | Raw transfer | Semantic transfer | Interpretation |
| --- | --- | --- | --- |
| PyTorch #51866 BCE range → TensorFlow | Runs; prints `1.1920929e-07` | Runs; same result | Both preserve the out-of-range literal. Source PyTorch raises a range error; TensorFlow accepts it. The card added no observable value. |
| TensorFlow #67531 zero-class cross entropy → PyTorch | Runs; catches batch-size error; preserves float64 labels | Runs; catches same error, but changes labels to `long` | The semantic arm violated the original dtype despite the card explicitly requiring float64. |
| TensorFlow `tf-stuck.py` zeros → PyTorch | Correct `(3,4)` int32 and float32 zero tensors | Same | Negative control: no difference. |
| PyTorch #129207 Conv1D CPU/MPS → TensorFlow | Runs with correct `(1,3,65537)` shape, but substitutes CPU for absent GPU and reports `Equal: True` | Runs with the correct shape and explicitly skips the comparison without GPU | Card prevents a false claim of device equivalence. The source MPS fault itself could not be evaluated here. |

The released CrossProbe transfer for TensorFlow #67531 fails to parse because of indentation, whereas both newly generated versions parse and run. The released TensorFlow transfer for PyTorch #51866 reverses `binary_crossentropy` arguments; both new prompts included the correct mapping, so this improvement belongs to the shared API context, not the semantic card.

These four selected examples cannot support an effectiveness percentage. The main result is methodological: syntax and successful execution are too weak as transfer metrics. A useful concept must be checked against preserved trigger fields (shape, dtype, value, layout, state), and the test must not claim an oracle result when required hardware is absent. The next controlled study should add a machine-checkable contract and equal-budget repair to both arms, then evaluate a larger issue set with the required target environments.

## Reproduction

The local artifact checkout is `/tmp/CrossProbe-upstream`. The isolated environment is `/tmp/crossprobe-concept-venv`. Generation code and selected case cards are in `crossprobe_pilot/`. The JSONL outputs are `/tmp/crossprobe_raw_generated.jsonl`, `/tmp/crossprobe_semantic_generated.jsonl`, `/tmp/crossprobe_conv_raw_generated.jsonl`, and `/tmp/crossprobe_conv_semantic_generated.jsonl`.

```bash
source scripts/vertex_env.sh
.venv/bin/python -m crossprobe_pilot.run --arm raw \
  --artifact /tmp/CrossProbe-upstream --out /tmp/crossprobe_raw_generated.jsonl
.venv/bin/python -m crossprobe_pilot.run --arm semantic \
  --artifact /tmp/CrossProbe-upstream --out /tmp/crossprobe_semantic_generated.jsonl
```

Review generated code before running it. The `/tmp` artifacts are ephemeral; this note preserves the observed outcomes and limitations.
