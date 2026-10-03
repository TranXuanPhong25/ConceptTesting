# Native arm64, CPU only. Build from repo root:
#   docker build -t dfuzz:arm64 -f DFUZZ/docker/Dockerfile DFUZZ
FROM ubuntu:22.04
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY requirements.txt /tmp/requirements.txt
# README env: python 3.8 + requirements.txt as-is (torch==2.2.0).
# networkx: imported by gen_program/gen_prompts_for_mutators.py but missing from requirements.txt.
RUN uv venv -p 3.8 /opt/py38 && uv pip install -p /opt/py38 -r /tmp/requirements.txt networkx
# Paper's bug-hunting TensorFlow is "v2.15" (not in requirements.txt); TF 2.15 needs python>=3.9, so 3.9 is the closest to the README's 3.8.
RUN uv venv -p 3.9 /opt/tf215 && uv pip install -p /opt/tf215 tensorflow==2.15.0 -r /tmp/requirements.txt networkx
RUN /opt/py38/bin/python -c "import torch,platform;print(torch.__version__,platform.machine())" \
 && /opt/tf215/bin/python -c "import tensorflow as tf,platform;print(tf.__version__,platform.machine())"
WORKDIR /dfuzz
