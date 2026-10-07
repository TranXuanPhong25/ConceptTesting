import glob, os, sys
os.makedirs("/tmp/ccp", exist_ok=True)
assert os.system("tar xzf %s -C /tmp/ccp" % glob.glob("/kaggle/input/**/ccp.tgz", recursive=True)[0]) == 0
sys.path.insert(0, "/tmp/ccp/ConceptCoder_placebo")
from kaggle_run import run
run(["placebo", "regular_paperhead"], extra="--max_train 64 --max_eval 32 --fit_n 16")
