# pbt-edge:arm64 — native arm64. Deps pinned by the authors' uv.lock (vendor/ebt_pbt_test) + google-genai for Vertex.
# Build: docker build -t pbt-edge:arm64 -f run/Dockerfile vendor/ebt_pbt_test   (from PBT_EdgeCases/)
FROM python:3.13-slim
RUN pip install --no-cache-dir uv==0.8.4
COPY pyproject.toml uv.lock /lock/
RUN cd /lock && uv export --frozen --no-dev --no-emit-project --no-hashes -o req.txt \
 && pip install --no-cache-dir -r req.txt google-genai==1.38.0 && pip freeze > /lock/freeze.txt
ENV PYTHONPATH=/vendor/src PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
