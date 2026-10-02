FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive TZ=America/Los_Angeles
RUN apt-get update && apt-get install -y openjdk-11-jdk git subversion perl cpanminus curl unzip build-essential python3 python3-pip \
    && rm -rf /var/lib/apt/lists/*
RUN git clone --depth 1 -b v3.0.1 https://github.com/rjust/defects4j /defects4j \
    && cd /defects4j && cpanm --installdeps . && ./init.sh
ENV PATH=/defects4j/framework/bin:$PATH
COPY download_dependencies.sh /tmp/
RUN bash /tmp/download_dependencies.sh /defects4j
# authors' env is python 3.12 (notebooks use PEP 701 f-strings)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
RUN uv venv -p 3.12 /venv && uv pip install -p /venv tree-sitter==0.21.3 javalang tqdm google-genai numpy chardet setuptools
ENV PATH=/venv/bin:$PATH
WORKDIR /repo
