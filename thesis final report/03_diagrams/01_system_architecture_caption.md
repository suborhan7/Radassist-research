# Figure 1 — System architecture, as implemented

**Source:** `01_system_architecture.mmd` · **Render:** `01_system_architecture.png`,
2325 × 2100 px, 300 dpi metadata. Natural size 7.75 × 7.00 in; **recommended
print width 6.5 in** (portrait text block), at which body text sets at
**11.1 pt** and effective resolution is **358 dpi**.

## What it shows

Every component of the running system and every connection between them. Read
it as four rings: the browser, the FastAPI process (API → services → domain →
infrastructure), the `shared/` package, and the external processes and stores.

**The one structural claim the figure makes** is the direction of the dashed
arrows: `app/services/` and `app/infrastructure/` both point *inward* at
`app/domain/`, which depends on nothing. That is clean architecture as it is
actually realised here — 21 `@runtime_checkable` Protocols in
`domain/interfaces.py`, with services depending on the Protocol and adapters
satisfying it, never the reverse.

`shared/` is drawn as a dotted box because it is a **deliberate one-off
exception** to the frozen rule that `ml/` and `backend/` never import each
other. `BiomedCLIPEmbedder` lives there so the offline research pipeline and
the live query path use one implementation — two copies would risk silent
drift between the knowledge base's embeddings and a live query's, without ever
erroring.

`chexbert.pth` is drawn outside every other boundary because it genuinely is:
Stanford Docket S20-295 forbids redistribution, so it lives in the HuggingFace
cache and must never enter this repository.

## Greyscale key

| treatment | meaning |
|---|---|
| white fill, heavy solid border | the frontend |
| light grey fill, thin border | a backend layer |
| white fill, heavy **dashed** border | the domain layer — depends on nothing |
| mid grey fill | infrastructure adapters |
| light grey, **dotted** border | `shared/`, the deliberate exception |
| **cylinder**, dark grey | an external process or persistent store |

No claim depends on hue. Every distinction is carried by shape, fill lightness
or stroke style.

## Derived from

- `backend/app/main.py:106-269` — the lifespan, which is where every edge inside
  the API box is actually wired
- `backend/app/domain/interfaces.py` — the 21 Protocols
- `backend/app/api/` — 12 routers (counted); 26 operations (counted from the
  live `/openapi.json` of a running instance)
- `backend/app/services/` — 36 modules (counted)
- `backend/app/infrastructure/` — 7 adapters (counted)
- `backend/app/core/config.py:29-124` — ports, collection name, CORS origin
- `shared/embeddings/biomedclip_embedder.py`, `shared/phi_masking/masker.py`
- `CLAUDE.md`, section "shared/ vs ml/ boundary" — why `shared/` exists
- Live readings taken for this packet: `ollama list`; `collection.count()` =
  2,462; alembic head `7f2a91c4d6e8`
