# environment.md — exact versions to reproduce the system

> Every version below was read from **this machine, by running the command
> named in the "how read" column**, on 2026-09-23, at commit `99f3eab8`
> (branch `final-prep`). Where a value is not recorded anywhere in the
> repository and cannot be read from a real command, the row says
> **NOT RECORDED**. No version is estimated or inferred.

---

## 1. Host

| item | value | how read |
|---|---|---|
| OS | Microsoft Windows 11 Pro, build **10.0.26200.8655** | `cmd /c ver` |
| GPU | **NVIDIA GeForce RTX 4070 Ti SUPER**, 16,376 MiB | `nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv` |
| NVIDIA driver | **591.86** | same |
| CUDA (as torch was built against) | **12.1** (`torch.version.cuda`) | `python -c "import torch; print(torch.version.cuda)"` |
| CUDA available at runtime | **True** | `torch.cuda.is_available()` |
| CUDA toolkit installed system-wide | **NOT RECORDED** — no `nvcc` version is pinned anywhere in the repo; torch ships its own runtime (`2.5.1+cu121`) | — |
| git | 2.54.0.windows.1 | `git --version` |
| interpreter used for the pipeline | `.venv/Scripts/python.exe` | — |

**Deployment-target caveat.** `.gitattributes` normalises line endings to LF
with the comment "Linux/RunPod deploy target" (commit `fcaf9c7c`,
2026-08-08). All measurements in this packet were nonetheless taken on the
Windows host above. No Linux run of this system is recorded.

---

## 2. Runtimes

| item | value | how read |
|---|---|---|
| Python (main venv, `.venv/`) | **3.12.3** | `.venv/Scripts/python.exe -V` |
| Python (frozen evaluation venv, `ml/evaluation/.venv-bertscore/`) | **3.12.3** | that venv's `python -V` |
| Node.js | **v24.18.0** | `node -v` |
| npm | **11.16.0** | `npm -v` |
| Ollama | **0.34.3** | `ollama --version` |

> [`thesis_facts.md`](thesis_facts.md) §1.1 records ollama **0.34.2** — that was
> the version at the Gate A run. The installed version today is **0.34.3**.
> Both are stated; neither is corrected away. Every Phase 22 number was
> produced under 0.34.2.

---

## 3. Models

### 3.1 Generation LLM

| item | value | how read |
|---|---|---|
| model | **`llama3:8b`** | `backend/app/core/config.py:51` (`DEFAULT_OLLAMA_MODEL`) |
| ollama digest | **`365c0bd3c000`** | `ollama list` |
| on-disk size | 4.7 GB | `ollama list` |
| architecture / parameters | llama, **8.0B** | `ollama show llama3:8b` |
| quantisation | **Q4_0** | same |
| model context length | 8192 | same |
| embedding length | 4096 | same |
| licence | META LLAMA 3 COMMUNITY LICENSE AGREEMENT, release date 2024-04-18 — shipped **inside the model**, not stored in this repository | `ollama show llama3:8b` |

Runtime call settings, all from `backend/app/core/config.py`: temperature
**0.0** (`:55`), seed **42** (`:70`), `keep_alive` **30m** (`:94`), request
timeout **120 s** (`:52`). `num_ctx` **4096** is set in
`backend/app/infrastructure/ollama_client.py`.

### 3.2 Phase 23 challenger model (tested, **not adopted**)

| item | value | how read |
|---|---|---|
| model | **`qwen2.5:14b`** | `ollama list` |
| digest | **`7cdf5a0187d5`** | same |
| size | 9.0 GB | same |
| status | **rejected** — lost to `llama3:8b` on all twelve accuracy cells | [`phase23_dev_results.md`](phase23_dev_results.md) §2.1 |

### 3.3 Embedding model

| item | value | how read |
|---|---|---|
| model id | **`hf-hub:microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224`** | `shared/embeddings/biomedclip_embedder.py:38` (`DEFAULT_MODEL_ID`) |
| embedding dimension | **512** | `docs/methodology/development_log.md:451` |
| runtime | `open_clip_torch` **3.3.0** | `importlib.metadata` |
| learned logit scale (reused as the modality gate's softmax temperature) | **85.2322769165039** → temperature `1/85.2322769165039` | `backend/app/core/config.py:344` |
| licence | **NOT RECORDED** — no licence text or citation for BiomedCLIP exists in this repository | — |

### 3.4 Clinical labeler (CheXbert)

| item | value | how read |
|---|---|---|
| checkpoint | `chexbert.pth`, **1,314,414,442 bytes** (1.31 GB) | `ls -la` on the snapshot directory |
| location | `~/.cache/huggingface/hub/models--StanfordAIMI--RRG_scorers/snapshots/6646433b3ad83a10f6e141db76d0ece44312b236/chexbert.pth` | `backend/app/core/config.py:196-199` |
| in the repository? | **No, and must never be** — Stanford Docket S20-295 forbids redistribution | [`thesis_facts.md`](thesis_facts.md) §6.2 |
| heads | 14 conditions | `backend/app/infrastructure/chexbert_labeler.py` |
| device | `auto` (resolves to cuda on this host) | `backend/app/core/config.py:206` |
| max length / batch size | 512 / 16 | `config.py:213`, `config.py:218` |
| licence | **Stanford Academic Software License Agreement**, Docket S20-295, dated 2020-10-15; academic non-commercial only; requires citing Smit et al. 2020; **no redistribution** | [`thesis_facts.md`](thesis_facts.md) §6.2 |

**Two CheXbert runtimes exist and they are not interchangeable.** The frozen
*evaluation* path (`ml/evaluation/score_chexbert.py`, run inside
`ml/evaluation/.venv-bertscore`, **torch 2.6.0** CPU, **transformers 4.46.0**)
produced every Phase 20 / 21 / 22 / 23 number. The *runtime* adapter
(`backend/app/infrastructure/chexbert_labeler.py`, main venv, torch
2.5.1+cu121) serves the live consistency check and disables TF32 on CUDA so
its labels match the frozen path (`config.py:206-212`).

### 3.5 Vector store contents (read live, today)

| item | value | how read |
|---|---|---|
| collection name | **`iu_cxr_biomedclip_v1_train`** | `chromadb.PersistentClient(path=...).list_collections()` |
| collection UUID on this machine | **`1bfce0d7-5894-4edf-88f5-324f1a44e9ee`** | same |
| document count | **2,462** | `collection.count()` |
| persist path | `ml/outputs/retrieval/chroma_db` | `backend/app/infrastructure/chroma_store.py:22-24` |

> `docs/phase22/gate_a_run_plan.md` §1.1 additionally records a **collection ID
> hash** `c6b2ab850fc9b3fb9a1bfc6493cdd52b5322c1d9d47b4d5dba88afeb12ef72f6`,
> used as the Gate A identity check. That is a different artefact from the live
> chromadb UUID above. Both are stated; the repository does **not** record how
> the hash was computed, so the two are not reconciled here.

---

## 4. Backend packages (main venv, read via `importlib.metadata`)

| package | version |
|---|---|
| fastapi | **0.139.0** |
| uvicorn | **0.51.0** |
| pydantic | **2.13.4** |
| pydantic-settings | **2.14.2** |
| SQLAlchemy | **2.0.51** |
| alembic | **1.18.5** |
| chromadb | **1.5.9** |
| torch | **2.5.1+cu121** |
| torchvision | **0.20.1+cu121** |
| open_clip_torch | **3.3.0** |
| transformers | **5.13.0** |
| easyocr | **1.7.2** |
| argon2-cffi | **25.1.0** |
| PyJWT | **2.13.0** |
| numpy | **2.5.1** |
| pandas | **3.0.3** |
| scikit-learn | **1.9.0** |
| scipy | **1.18.0** |
| pillow | **12.2.0** |
| httpx | **0.28.1** |
| requests | **2.34.2** |
| pytest | **9.1.1** |
| python-jose | **not installed** — JWT is PyJWT, not python-jose |

**There is no lockfile for the Python side.** `requirements.txt` exists but
does not pin the backend stack; the table above is the *installed* truth, read
from the running interpreter. A reinstall from `requirements.txt` alone is
**not** guaranteed to reproduce these versions.

### 4.1 Evaluation-metric packages

| package | main venv | frozen eval venv (`.venv-bertscore`) |
|---|---|---|
| torch | 2.5.1+cu121 | **2.6.0** (CPU) |
| transformers | 5.13.0 | **4.46.0** |
| bert-score | 0.3.13 | **0.3.13** |
| rouge-score | 0.1.2 | not installed |
| sacrebleu | 2.6.0 | not installed |
| nltk | 3.10.0 | not installed |
| numpy | 2.5.1 | 2.5.1 |

BERTScore model:
`microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext`, layer 9
([`thesis_facts.md`](thesis_facts.md) §6.1).

---

## 5. Frontend packages (`frontend/package.json`)

| package | version as declared |
|---|---|
| next | **16.2.10** (exact pin) |
| react / react-dom | **19.2.4** (exact pins) |
| clsx | ^2.1.1 |
| diff | ^9.0.0 |
| tailwind-merge | ^3.6.0 |
| tailwindcss | ^4 |
| @tailwindcss/postcss | ^4 |
| typescript | ^5 |
| eslint / eslint-config-next | ^9 / 16.2.10 |
| vitest | ^4.1.10 |
| @testing-library/react | ^16.3.3 |
| @testing-library/dom | ^10.4.2 |
| jsdom | ^30.1.1 |
| openapi-typescript | ^7.13.0 |
| @types/node / @types/react / @types/react-dom | ^20 / ^19 / ^19 |

Everything except `next`, `react` and `react-dom` is a caret range, so a fresh
`npm install` may resolve differently. `frontend/package-lock.json` is the
authority for an exact reinstall.

**No export or PDF library is present.** Printing is the browser's own
`window.print()` (`frontend/src/components/report/print-portal.tsx`), which is
why server-side PDF is listed as not implemented in
[`feature_catalogue.md`](feature_catalogue.md).

---

## 6. Test suites, run on this machine today

| suite | command | result |
|---|---|---|
| backend | `.venv/Scripts/python.exe -m pytest tests -q` (from `backend/`) | **534 passed**, 14 warnings, 213.99 s |
| frontend | `npx vitest run` (from `frontend/`) | **138 passed**, 12 files, 1.57 s |

Both run at commit `99f3eab8` with no source changes. These supersede the
older counts recorded in the development log (194/194 at Phase 19), which were
true for the code as it stood then.

---

## 7. Reproduction order

```bash
# 1. Python environment
python -m venv .venv && .venv/Scripts/activate
pip install -r requirements.txt            # NOTE: unpinned; see §4

# 2. Models
ollama pull llama3:8b                      # digest 365c0bd3c000
#    BiomedCLIP downloads on first embedder construction (open_clip hf-hub).
#    chexbert.pth must be fetched separately from StanfordAIMI/RRG_scorers
#    and placed at CHEXBERT_CHECKPOINT_PATH. It is NOT in this repository
#    and must never be added to it (Stanford Docket S20-295).

# 3. Database
cd backend && alembic upgrade head          # head = 7f2a91c4d6e8

# 4. Backend  (loads BiomedCLIP, EasyOCR and CheXbert at startup)
.venv/Scripts/python.exe -m uvicorn app.main:app --port 8000

# 5. Frontend
cd frontend && npm install && npm run dev   # :3000, the backend's only CORS origin
```

`DEFAULT_CORS_ALLOWED_ORIGINS` is `http://localhost:3000`
(`backend/app/core/config.py:108`), so the frontend must be served from that
origin or the browser will refuse every call.
