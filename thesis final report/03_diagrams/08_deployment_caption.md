# Figure 8 — Local deployment

**Source:** `08_deployment.mmd` · **Render:** `08_deployment.png`,
3528 × 4288 px, 300 dpi metadata. Natural size 11.76 × 14.29 in;
**recommended print size 6.5 × 7.90 in**, at which body text sets at
**6.6 pt** and effective resolution is **543 dpi**.

## What it shows

The deployment as it is actually run: **three processes, started by hand, on
one Windows host.** Ports, GPU residency and storage locations are all real
measured or configured values.

| process | runtime | port |
|---|---|---|
| Next.js dev server | node v24.18.0, next 16.2.10 | **3000** |
| FastAPI / uvicorn | python 3.12.3, uvicorn 0.51.0 | **8000** (8011 for this packet's screenshot capture) |
| Ollama | 0.34.3 | **11434** |

The frontend **must** be served from `:3000` — it is the only origin in
`CORS_ALLOWED_ORIGINS` (`config.py:108`), so a browser served from anywhere
else will have every call refused.

**GPU residency is measured, not estimated** (`fix_architecture_v1.2_FROZEN.md`
§7): llama3:8b 5,025 MiB, BiomedCLIP marginal 1,043 MiB, CheXbert marginal 452
MiB, **peak with all three resident plus inference 7,125 MiB of 16,376**,
leaving 9.03 GiB of headroom. Phase 23's peak, with qwen2.5:14b instead, was
11,401 MiB.

**Every path is anchored to its own file's location, never the process CWD**
(`config.py:22-26`), after a real incident: a stray `cd backend` produced an
empty `backend/ml/outputs/retrieval/chroma_db` instead of erroring.

`chexbert.pth` is drawn outside the repository because Stanford Docket S20-295
forbids redistribution. It is never gitignored-and-trusted; it simply lives
somewhere the repository cannot reach.

## What the figure says is absent

The first warning box lists what this deployment does **not** have: no Docker
or compose (the frozen monorepo layout records a `deployment/` directory that
**does not exist in this copy**), no reverse proxy, no TLS, no process manager,
no rate limiting, no secrets management, no CI/CD, and **no recorded Linux
run** — despite `.gitattributes` naming a Linux/RunPod deploy target.
`JWT_SECRET_KEY` still resolves to the literal dev placeholder in every
measurement this project recorded.

The second warning box records the safety rule under which this packet's
screenshots were produced: the e2e harness is **fail-closed** — `E2E_DB` must
name a disposable path and the harness refuses to run if it is unset or equal
to `dev.db`. The screenshots were captured against a **copy** on port 8011, and
`dev.db`'s md5 was verified unchanged afterwards.

## Derived from

- `backend/app/main.py:106-269` — what the lifespan loads, once per process
- `backend/app/core/config.py:22-145` — ports, paths, CORS origin, upload dir
- `backend/app/infrastructure/chroma_store.py:20-32` — the CWD-anchoring incident
- `docs/phase22/fix_architecture_v1.2_FROZEN.md` §7 — the VRAM measurements
- `docs/phase23/step1_measurements.md` §1 — the qwen peak
- `e2e/harness.mjs:37-50` — `assertSafeTarget`, the fail-closed rule
- `.gitattributes` — the stated Linux deploy target
- Live readings: `nvidia-smi`, `ollama --version`, `node -v`, `python -V`
