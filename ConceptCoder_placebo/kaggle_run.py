"""Kaggle entry (imported by kernels/*/run.py after it untars ccp.tgz into /tmp/ccp).
machine_shape NvidiaTeslaT4 = 2x T4 -> up to 2 arms run in parallel, one per GPU, same session quota."""
import os, sys, json, time, subprocess

T, W = "/tmp/ccp", "/kaggle/working"


def sh(cmd, check=False):
    print("$", cmd, flush=True)
    return subprocess.run(cmd, shell=True, check=check)


def run(arms, extra="", suffix=""):
    assert 1 <= len(arms) <= 2
    sh("%s -m pip uninstall -y -q torchao" % sys.executable)            # peft vs Kaggle's torchao (KAGGLE_CLI.md)
    sh("%s -m pip install -q peft" % sys.executable, check=True)
    sh("nvidia-smi --query-gpu=name,memory.total --format=csv; free -g | head -2; nproc")
    sh("%s -c 'import torch,transformers,peft;print(torch.__version__,transformers.__version__,peft.__version__)'" % sys.executable)
    sh("sha256sum %s/data/VD/*.jsonl" % T)
    from huggingface_hub import snapshot_download
    snapshot_download("Qwen/Qwen2.5-Coder-3B")                          # once, before the parallel loads
    procs, t0 = [], time.time()
    for gpu, arm in enumerate(arms):
        out = "%s/out/%s%s" % (W, arm, suffix)
        os.makedirs(out, exist_ok=True)
        cmd = ("%s %s/ConceptCoder_placebo/train_arm.py --arm %s --cc_vd %s/ConceptCoder_org/code/concept_learning/VD "
               "--data_dir %s/data/VD --out %s %s" % (sys.executable, T, arm, T, T, out, extra))
        print("GPU%d: %s" % (gpu, cmd), flush=True)
        log = open(out + "/train.log", "w")
        procs.append((arm, out, subprocess.Popen(cmd, shell=True, stdout=log, stderr=subprocess.STDOUT,
                                                 env=dict(os.environ, CUDA_VISIBLE_DEVICES=str(gpu)))))
        time.sleep(90)                                                  # stagger CPU-RAM peak of model load
    while any(p.poll() is None for _, _, p in procs):
        time.sleep(300)
        for arm, out, p in procs:
            lines = [l for l in open(out + "/train.log").read().splitlines() if l.strip() and "Warning" not in l]
            print("[%3.0f min] %-18s %s" % ((time.time() - t0) / 60, arm, lines[-1][:160] if lines else ""), flush=True)
    for arm, out, p in procs:
        print("== %s exit=%s" % (arm, p.returncode), flush=True)
        sh("grep -v Warning %s/train.log | tail -8" % out)
        if os.path.exists(out + "/metrics.json"):
            r = json.load(open(out + "/metrics.json"))
            print(json.dumps({k: r.get(k) for k in ("arm", "train_min", "test", "robust", "linear_probe")})[:1500], flush=True)
