# syntax=docker/dockerfile:1.7
# PARTIALLY VERIFIED on 2026-10-04 (Docker Desktop 4.91.0 / Engine 29.8.0, linux/amd64, Windows host):
# `docker build --target verify` is GREEN: npm ci, pip --require-hashes from python/requirements-lpbf-linux-py312.lock,
# 'npm run lint', unit tests (tests/*.test.ts(x) minus scripts/ci-unit-tests.txt, guarded below), 'npm run build',
# and the three CPU meltpool scripts. python/test_goldak_fabbro.py skips its NIST width check here (it needs the GPU warp
# ray tracer; the CPU flat-plate fallback gives 81.7 um vs NIST 136.3 um) and pins the fallback instead. The image is
# CPU-only, so Goldak results served by it always use the flat-plate width.
# Runtime image checked on 2026-10-04 at commit 9ea3493 (`docker run --cap-drop ALL --security-opt no-new-privileges
# -p 127.0.0.1:38080:3000`): /api/health 200 from the host, unauthenticated /api/lpbf/capabilities 401, absolute-form
# request target 400, one-time login link in `docker logs`, login 303, HEALTHCHECK healthy, no writes outside /tmp and
# /data. Not GitHub CI; `docker compose up` not run. See docs/APPLICATION_PACKAGING_NOTES.md.

FROM node:24-bookworm-slim AS node-src

# Base: CPython 3.12 with the Node 24 runtime copied in.
FROM python:3.12-slim-bookworm AS base
COPY --from=node-src /usr/local/bin/node /usr/local/bin/node
COPY --from=node-src /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
 && ln -s ../lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx
ENV PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

# Node dependencies (all, for build and test).
FROM base AS node-deps
COPY package.json package-lock.json ./
RUN npm ci

# Python environment from the hash-locked Linux CPU lock.
FROM base AS py-deps
COPY python/requirements-lpbf-linux-py312.lock /tmp/requirements.lock
RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install --no-cache-dir --require-hashes -r /tmp/requirements.lock

# Verification target: docker build --target verify .
# The unit test list is the tests/*.test.ts(x) glob minus scripts/ci-unit-tests.txt,
# the same rule as .github/workflows/ci.yml.
FROM base AS verify
# AIRGAPPED is deliberately NOT set here: .github/workflows/ci.yml does not set it, and 12 unit tests
# (GPT-6 service/route, route input-limit validation, workstation literature query) assume it is unset.
# The runtime stage below keeps AIRGAPPED=1.
ENV METALLIX_PYTHON=/opt/venv/bin/python CI=1
COPY --from=py-deps /opt/venv /opt/venv
COPY --from=node-deps /app/node_modules ./node_modules
COPY . .
RUN <<'EOF' bash -e
npm run lint
excluded="$(grep -v '^#' scripts/ci-unit-tests.txt | grep -v '^$' || true)"
files="$(ls tests/*.test.ts tests/*.test.tsx | { grep -vxF "$excluded" || true; })"
# Guard (same as ci.yml): every listed exclusion must be one of the unit-test glob's files and absent
# from the run list. A CRLF copy of the list makes the grep above exclude nothing; this re-reads the list with
# CRs stripped and fails instead. Here-strings, not pipes: with pipefail a grep -q that exits early could
# SIGPIPE its writer and turn a match into a false negative.
all="$(ls tests/*.test.ts tests/*.test.tsx)"
for ex in $(grep -v '^#' scripts/ci-unit-tests.txt | tr -d '\r' | grep -v '^$' || true); do
  grep -qxF -- "$ex" <<<"$all" \
    || { echo "scripts/ci-unit-tests.txt lists a file outside the unit test glob (missing or renamed): $ex" >&2; exit 1; }
  if grep -qxF -- "$ex" <<<"$files"; then echo "scripts/ci-unit-tests.txt exclusion not applied: $ex" >&2; exit 1; fi
done
echo "Running $(printf '%s\n' "$files" | wc -l) test files"
node_modules/.bin/tsx --test $files
npm run build
/opt/venv/bin/python python/test_eagar_tsai.py
/opt/venv/bin/python python/test_goldak_fabbro.py
/opt/venv/bin/python python/test_lpbf_meltpool_accuracy.py
/opt/venv/bin/python python/test_gpu_capability.py
EOF

# Production dependencies only.
FROM base AS prod-deps
COPY package.json package-lock.json ./
RUN npm ci --omit=dev

# Runtime image (default target). Runs as a non-root user (uid 10001).
# Code trees (dist, node_modules, python, data, docs/sources/in625) are root-owned
# and read-only for that user. It can write only to:
#  - /data (the volume): every root below is redirected there by environment variables;
#  - the WORKDIR-relative default data directories, created and chowned below so the server also works
#    when those variables are unset;
#  - /tmp: Python temporary directories (tempfile), including the IPC daemon's private 0700 socket directory
#    (/tmp/metallix-ipc-*/ipc.sock; the daemon refuses a socket placed directly in /tmp).
# PYTHONDONTWRITEBYTECODE=1 (base stage) keeps Python from writing __pycache__ into python/.
FROM base AS runtime
# METALLIKSA_HOST=0.0.0.0: the server binds 127.0.0.1 by default (server/security.ts resolveBindConfig), which a
# published port cannot reach. A non-loopback bind turns the login flow ON (the intended secure default): without
# METALLIKSA_TOKEN a random one-time login link is printed at start (`docker logs <container>`; it shows
# http://localhost:3000/..., so replace the port with the published host port). With METALLIKSA_TOKEN set, API clients
# send 'Authorization: Bearer <token>' and browsers enter it on /login. Every /api route except /api/health needs login.
ENV NODE_ENV=production \
    METALLIKSA_HOST=0.0.0.0 \
    PORT=3000 \
    AIRGAPPED=1 \
    METALLIX_PYTHON=/opt/venv/bin/python \
    METALLIKSA_LPBF_SOURCE_ROOT=/data/lpbf-sources \
    METALLIKSA_LPBF_RUN_ROOT=/data/lpbf-runs \
    METALLIKSA_LPBF_BUNDLE_ROOT=/data/lpbf-run-bundles \
    METALLIKSA_JOB_ROOT=/data/lpbf-jobs \
    RESEARCH_REGISTRY_DIR=/data/research-registry
COPY --from=py-deps /opt/venv /opt/venv
COPY --from=prod-deps /app/node_modules ./node_modules
# dist comes from the verify stage so an image is only produced from a verified build.
COPY --from=verify /app/dist ./dist
COPY package.json ./
COPY python ./python
ARG INSTALL_GPU=0
# Opt-in only: verification above always exercises the unchanged CPU environment.
RUN if [ "$INSTALL_GPU" = "1" ]; then \
      /opt/venv/bin/pip install --no-cache-dir --require-hashes -r python/requirements-gpu-linux-py312.lock \
      && mkdir -p /app/.cache && chown 10001 /app/.cache; \
    elif [ "$INSTALL_GPU" != "0" ]; then echo "INSTALL_GPU must be 0 or 1" >&2; exit 1; fi
COPY data ./data
# docs/sources/in625 is read at run time (server/lpbfPropertySourceCatalog.ts resolves it
# against the working directory; lpbfSourceArchiveService archives from it).
COPY docs/sources/in625 ./docs/sources/in625
RUN useradd --system --uid 10001 --no-create-home --home-dir /app metalliksa \
 && chmod -R go-w /app \
 && mkdir -p /data/lpbf-sources /data/lpbf-runs /data/lpbf-run-bundles /data/lpbf-jobs /data/research-registry \
      /app/.lpbf-sources /app/.lpbf-runs /app/.lpbf-run-bundles /app/.lpbf-jobs /app/.research-registry /app/.runtime \
 && chown -R metalliksa /data \
      /app/.lpbf-sources /app/.lpbf-runs /app/.lpbf-run-bundles /app/.lpbf-jobs /app/.research-registry /app/.runtime
USER metalliksa
VOLUME ["/data"]
EXPOSE 3000
# /api/health is the only unauthenticated /api route (server/security.ts tokenAuth), so this check works in login mode
# without a credential. It connects over container loopback, which a 0.0.0.0 bind accepts; override it if
# METALLIKSA_HOST is set to one specific interface address. It does not probe the Python worker
# (/api/python/status needs login).
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=5 \
  CMD ["node", "-e", "fetch('http://127.0.0.1:'+(process.env.PORT||3000)+'/api/health').then(r=>process.exit(r.ok?0:1),()=>process.exit(1))"]
CMD ["node", "dist/server.cjs"]
