# Offline deployment (enterprise profile)

For hosts with no internet access. Metalliksa is a research workstation, not a qualification tool; nothing here changes that.

## 1. Profile

Set `METALLIKSA_PROFILE=enterprise` in the environment (or `.env`). Effects:

- Air-gap is forced on, with or without `AIRGAPPED=1`. Crossref search and any cloud AI or external API stay refused.
- The server refuses to start if `AIRGAPPED=0` is also set, or if `OPENAI_API_KEY` is set.
- Startup logs `METALLIKSA_PROFILE=enterprise: air-gap forced on ...`. Check for this line after every start.

The Docker image and `docker-compose.yml` already set `AIRGAPPED=1`; add `METALLIKSA_PROFILE: "enterprise"` to the `environment` block to get the startup refusal as well.

## 2. Prepare on a connected build host

Do these once on a machine with internet, then carry the results over on approved media.

```bash
# Node: fill the npm cache, then copy ~/.npm (or the cache dir from `npm config get cache`) and the repo
npm ci
npm run build
npm run sbom

# Python: wheelhouse from the hash-locked file (pick the lock for the target OS)
pip download --require-hashes -r python/requirements-lpbf-linux-py312.lock -d wheelhouse/ \
  --platform manylinux_2_28_x86_64 --python-version 3.12 --implementation cp --only-binary=:all:
# Windows target: python/requirements-lpbf-win-py312.lock with --platform win_amd64.
# Without the platform flags pip fetches wheels for the build host, which fail the
# hash check or do not install when the build host differs from the target.

# Docker (optional): build and export the runtime image
docker build -t metalliksa:offline .
docker save metalliksa:offline -o metalliksa-offline.tar

# Checksums for dist/ and sbom/*.json
npm run release:checksums
```

`SHA256SUMS` is written to the repo root in `sha256sum` format. Also hash the wheelhouse and the image tar yourself (`sha256sum wheelhouse/* metalliksa-offline.tar >> SHA256SUMS`) if you ship them.

## 3. Install on the offline host

```bash
sha256sum -c SHA256SUMS                      # or: node scripts/release-checksums.mjs --verify
npm ci --offline --cache <path-to-copied-npm-cache>
python -m venv .venv
.venv/bin/pip install --no-index --find-links wheelhouse --require-hashes -r python/requirements-lpbf-linux-py312.lock
# Docker route instead:
docker load -i metalliksa-offline.tar
```

Inspect `sbom/node-cyclonedx.json` and `sbom/python-cyclonedx.json` (CycloneDX 1.5) against your approved-component list. The SBOMs list declared dependencies; they are not a vulnerability scan.

## 4. Run

```bash
METALLIKSA_PROFILE=enterprise npm start      # binds 127.0.0.1:3000 by default
```

- Bind address: the server binds `127.0.0.1` unless `METALLIKSA_HOST` is set. Keep it that way, or front it with a TLS reverse proxy on the same host.
- Docker: `docker-compose.yml` publishes `127.0.0.1:3000:3000` only. Do not change it to `3000:3000` without a TLS proxy and `METALLIKSA_TRUST_PROXY`. The container binds `0.0.0.0` internally, which turns the login flow on; take the one-time link from `docker compose logs app` or set `METALLIKSA_TOKEN`.
- `GET /api/health` is the only unauthenticated API route.

## 5. Data to back up

Bare install (relative to the working directory):

- `.lpbf-jobs`, `.lpbf-runs`, `.lpbf-run-bundles`, `.lpbf-sources`, `.research-registry`, `.runtime`

Docker: the `metalliksa-data` volume mounted at `/data` holds `lpbf-sources`, `lpbf-runs`, `lpbf-run-bundles`, `lpbf-jobs` and `research-registry`. Back it up with the container stopped:

```bash
docker run --rm -v metalliksa-data:/data -v "$PWD":/backup busybox tar czf /backup/metalliksa-data.tgz -C /data .
```

Machine calibration data is not in that volume: it goes to `/app/.runtime/machine-calibration` inside the container unless `LPBF_MACHINE_CALIBRATION_DIR` points elsewhere. Set `LPBF_MACHINE_CALIBRATION_DIR=/data/machine-calibration` so a container recreate keeps it and the backup above covers it, or back up `/app/.runtime` separately.

The browser-side research registry (`metalliksa-research-registry-v1`) lives in each user's browser storage and is not in these directories.

## Not verified

The offline install sequence above has not been run end to end on a disconnected host, and no wheels or images were downloaded for this document.
