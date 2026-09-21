"""
app/infrastructure/chexbert_labeler.py
====================================================================
Satisfies domain.interfaces.ISectionLabeler: CheXbert over report TEXT,
returning the RAW 4-class index per condition. Phase 22 v1.2, frozen
architecture §3.3 and §7 (docs/phase22/fix_architecture_v1.2_FROZEN.md,
frozen at docs commit 810240ea).

WHY THIS DOES NOT IMPORT ml/evaluation/score_chexbert.py
--------------------------------------------------------
Two independent reasons, both from the frozen document §7.1:

1. `ml/` and `backend/` never import each other (CLAUDE.md's frozen
   boundary). `shared/` is the one deliberate exception and holds the
   embedder only; a second exception would erode the rule it exists to state.
2. `score_chexbert.tokenize_texts()` calls `BertTokenizer.encode_plus()`,
   removed in transformers 5.x. The frozen document chose to PORT the
   tokenisation rather than pin the backend below 5.x, because a pin binds
   the production dependency graph to one model's tokenizer call and is
   invisible at the point it breaks.

The frozen script is therefore READ AS A SPECIFICATION and reimplemented
here, never imported and never modified. That makes equivalence something to
be PROVEN rather than assumed, which is what
scratch/phase22_diagnosis/verify_chexbert_equivalence.py exists to do: token
identity on all 954 real sections, then raw-label identity on CPU and on GPU
against the labels the frozen venv produced for diagnosis.md §2c. Those three
layers are the contract this module is held to.

WHAT IS COPIED VERBATIM AND WHY
-------------------------------
`CONDITIONS` and the class mapping are copied verbatim from
stanfordmlgroup/CheXbert's own `src/constants.py` -- the same provenance
score_chexbert.py used, and for the same reason: the order IS the order of
the model's 14 linear heads, and getting it wrong silently mislabels every
condition rather than failing. `conditions_match()` below exists so the order
can be asserted against the frozen evaluation's own list at test time instead
of trusted.

The 14th head ("No Finding") has 2 outputs, not 4, in the real architecture.
That is preserved exactly: it can emit only Blank(0) or Positive(1), never
Negative(2), which is why the contradiction check excludes it entirely
(frozen document §3.3).
"""
from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

# Verbatim from stanfordmlgroup/CheXbert src/constants.py. Order matters: it
# is the real order of the model's 14 linear heads.
CONDITIONS: tuple[str, ...] = (
    "Enlarged Cardiomediastinum",
    "Cardiomegaly",
    "Lung Opacity",
    "Lung Lesion",
    "Edema",
    "Consolidation",
    "Pneumonia",
    "Atelectasis",
    "Pneumothorax",
    "Pleural Effusion",
    "Pleural Other",
    "Fracture",
    "Support Devices",
    "No Finding",
)

CLASS_MAPPING = {0: "Blank", 1: "Positive", 2: "Negative", 3: "Uncertain"}

# The 14th head is binary in the real checkpoint. Named rather than written
# as a bare 13/1 split so the asymmetry is visible where it is relied upon.
N_HEADS = 14
N_FOUR_CLASS_HEADS = 13
BINARY_HEAD_INDEX = 13  # "No Finding"

_BERT_BASE = "bert-base-uncased"


class ChexbertUnavailableError(RuntimeError):
    """Raised at CONSTRUCTION when the labeler cannot be made ready --
    missing checkpoint, unreadable file, absent torch/transformers, or a
    state-dict that does not match the architecture.

    Typed, and raised at construction rather than at first use, so the
    failure is visible at wiring time instead of surfacing inside a report
    request. Step A4's contract on catching it is explicit in the frozen
    document §3.3: treat it as "labeler unavailable", omit "contradiction"
    from `checks_run`, and carry on. Generation is NEVER blocked by it, and a
    missing labeler is NEVER reported as a clean contradiction check -- an
    unavailable check and a passed check are different states.

    Lives in this module rather than app/services/exceptions.py because Step
    A2's scope is the adapter; if A4 needs it in the service layer it can be
    relocated there then, with its importers updated in the same change.
    """


class ChexbertLabeler:
    """Satisfies domain.interfaces.ISectionLabeler."""

    def __init__(
        self,
        checkpoint_path: str,
        device: str = "auto",
        max_length: int = 512,
        batch_size: int = 16,
    ) -> None:
        # Imported inside __init__, not at module import time: torch and
        # transformers are heavy, and this module is imported by tests that
        # mock the model and must not pay a multi-second import to do so.
        try:
            import torch
            from transformers import BertTokenizer
        except ImportError as exc:  # pragma: no cover - environment-dependent
            raise ChexbertUnavailableError(
                f"torch/transformers are required by the CheXbert labeler: {exc}"
            ) from exc

        path = Path(checkpoint_path)
        if not checkpoint_path or not path.is_file():
            raise ChexbertUnavailableError(
                f"CheXbert checkpoint not found at {checkpoint_path!r}. Set "
                f"CHEXBERT_CHECKPOINT_PATH, or run without a labeler -- the "
                f"contradiction check is then omitted from checks_run rather "
                f"than reported as passing."
            )

        self._torch = torch
        self._max_length = max_length
        self._batch_size = batch_size
        self._device = torch.device(self._resolve_device(device, torch))

        try:
            self._tokenizer = BertTokenizer.from_pretrained(_BERT_BASE)
            self._model = self._load_model(path, self._device, torch)
        except ChexbertUnavailableError:
            raise
        except Exception as exc:
            raise ChexbertUnavailableError(
                f"CheXbert labeler failed to load from {checkpoint_path!r}: "
                f"{type(exc).__name__}: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # ISectionLabeler
    # ------------------------------------------------------------------

    @property
    def conditions(self) -> tuple[str, ...]:
        return CONDITIONS

    def label(self, texts: Sequence[str]) -> tuple[tuple[int, ...], ...]:
        """One row per text, in the same order, each row one RAW class index
        per entry of `conditions`.

        Raw, not binarised: the contradiction check needs Negative(2)
        distinguishable from Blank(0), and `to_present_binary()`'s
        {Blank, Negative} -> 0 collapse destroys exactly that distinction.
        """
        texts = list(texts)
        if not texts:
            return ()

        torch = self._torch
        token_ids = [self._encode(t) for t in texts]
        rows: list[tuple[int, ...]] = []

        with self._inference_context():
            for start in range(0, len(token_ids), self._batch_size):
                batch = token_ids[start:start + self._batch_size]
                max_len = max(len(ids) for ids in batch)
                padded = torch.zeros((len(batch), max_len), dtype=torch.long)
                attention = torch.zeros((len(batch), max_len), dtype=torch.long)
                for i, ids in enumerate(batch):
                    padded[i, : len(ids)] = torch.tensor(ids, dtype=torch.long)
                    attention[i, : len(ids)] = 1
                padded = padded.to(self._device)
                attention = attention.to(self._device)

                logits = self._model(padded, attention)
                # argmax per head, then transpose to one row per text.
                per_head = [head.argmax(dim=1).tolist() for head in logits]
                for i in range(len(batch)):
                    rows.append(tuple(int(per_head[h][i]) for h in range(N_HEADS)))

        return tuple(rows)

    # ------------------------------------------------------------------
    # tokenisation -- the ported half of the equivalence contract
    # ------------------------------------------------------------------

    def _encode(self, text: str) -> list[int]:
        """Ported from the frozen `tokenize_texts()` using the tokenizer's
        `__call__` API, which exists in both transformers 4.x and 5.x.

        The frozen implementation was:

            tokenized = tokenizer.tokenize(text)
            if tokenized:
                ids = tokenizer.encode_plus(tokenized)["input_ids"]
                if len(ids) > 512:
                    ids = ids[:511] + [tokenizer.sep_token_id]
            else:
                ids = [cls_token_id, sep_token_id]

        Three equivalences make the one-liner below identical to it, each
        checked rather than assumed:

        1. `tokenize()` then `encode_plus(<token list>)` applies WordPiece and
           then adds [CLS]/[SEP]; `__call__(text, add_special_tokens=True)`
           does the same two steps in one call over the same WordPiece
           vocabulary.
        2. Empty/whitespace-only text tokenises to [] in both, and both then
           yield exactly [CLS, SEP] -- so the frozen version's explicit empty
           branch needs no counterpart here.
        3. Truncation coincides. The frozen code keeps `ids[:511] + [SEP]`,
           i.e. [CLS] + first 510 content tokens + [SEP] = 512.
           `truncation=True, max_length=512` keeps [CLS] + first 510 content
           tokens + [SEP] = 512. Same sequence.

        NOTE ON WHAT THE EQUIVALENCE GATE ACTUALLY COVERS. Across all 954
        real Arm C sections the longest sequence is 298 tokens, so **the
        truncation branch is never exercised by the corpus**. Equivalence (3)
        is therefore established by a dedicated synthetic over-length case in
        the verification script and in the unit tests, not by the corpus run.
        Recorded here because "954/954 identical" would otherwise be read as
        covering a path it does not reach.
        """
        encoded = self._tokenizer(
            text,
            add_special_tokens=True,
            truncation=True,
            max_length=self._max_length,
        )
        return list(encoded["input_ids"])

    # ------------------------------------------------------------------
    # inference context
    # ------------------------------------------------------------------

    def _inference_context(self):
        """`torch.no_grad()` plus TF32 explicitly OFF.

        TF32 is not a performance preference here, it is a correctness
        requirement for the equivalence gate. On Ampere and later, PyTorch may
        execute fp32 matmuls and cuDNN convolutions in TF32, which keeps only
        10 explicit mantissa bits. That perturbs logits in the last few
        decimal places -- harmless for a loss curve, but this labeler's output
        is an ARGMAX over 4 classes, and a perturbed logit flips the argmax
        whenever the top two classes are nearly tied. A single flipped cell
        fails layer (c) of the equivalence gate.

        The frozen evaluation ran on CPU (torch 2.6.0+cpu), where TF32 does
        not exist, so CPU-vs-GPU agreement is only expected if the GPU path is
        held to the same fp32 arithmetic. Setting these two flags is what
        makes "same checkpoint, same tokens, same labels" true on CUDA rather
        than merely likely.

        Restored afterwards rather than set globally: this process may host
        BiomedCLIP and other models whose own precision choices are not this
        module's to change.
        """
        torch = self._torch
        labeler = self

        class _Context:
            def __enter__(self):
                self._prev_matmul = torch.backends.cuda.matmul.allow_tf32
                self._prev_cudnn = torch.backends.cudnn.allow_tf32
                torch.backends.cuda.matmul.allow_tf32 = False
                torch.backends.cudnn.allow_tf32 = False
                self._no_grad = torch.no_grad()
                self._no_grad.__enter__()
                labeler._model.eval()
                return self

            def __exit__(self, *exc):
                self._no_grad.__exit__(*exc)
                torch.backends.cuda.matmul.allow_tf32 = self._prev_matmul
                torch.backends.cudnn.allow_tf32 = self._prev_cudnn
                return False

        return _Context()

    # ------------------------------------------------------------------
    # model construction
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_device(device: str, torch) -> str:
        """"auto" resolves to cuda when available, else cpu -- the same
        convention BiomedCLIPEmbedder already uses, so a deployment sets one
        mental model, not two."""
        if device and device != "auto":
            return device
        return "cuda" if torch.cuda.is_available() else "cpu"

    @staticmethod
    def _load_model(path: Path, device, torch):
        """Reconstructs stanfordmlgroup/CheXbert's `bert_labeler` and
        strict-loads the real checkpoint.

        `strict=True` is deliberate. A partially-matching state dict would
        leave randomly-initialised heads producing plausible-looking garbage
        labels; failing loudly at construction is the only safe behaviour for
        a component whose output feeds a clinical warning.
        """
        import torch.nn as nn
        from transformers import BertModel

        class _BertLabeler(nn.Module):
            def __init__(self, p: float = 0.1) -> None:
                super().__init__()
                self.bert = BertModel.from_pretrained(_BERT_BASE)
                self.dropout = nn.Dropout(p)
                hidden = self.bert.pooler.dense.in_features
                self.linear_heads = nn.ModuleList(
                    [nn.Linear(hidden, 4, bias=True) for _ in range(N_FOUR_CLASS_HEADS)]
                )
                # The 14th head is binary in the real architecture.
                self.linear_heads.append(nn.Linear(hidden, 2, bias=True))

            def forward(self, source_padded, attention_mask):
                hidden = self.bert(source_padded, attention_mask=attention_mask)[0]
                cls_hidden = hidden[:, 0, :].squeeze(dim=1)
                cls_hidden = self.dropout(cls_hidden)
                return [self.linear_heads[i](cls_hidden) for i in range(N_HEADS)]

        model = _BertLabeler()
        checkpoint = torch.load(str(path), map_location="cpu", weights_only=True)
        state_dict = checkpoint["model_state_dict"]
        # Checkpoint was saved from a DataParallel-wrapped model.
        stripped = {
            (k[len("module."):] if k.startswith("module.") else k): v
            for k, v in state_dict.items()
        }
        model.load_state_dict(stripped, strict=True)
        model.to(device)
        model.eval()
        return model


def conditions_match(other: Sequence[str]) -> bool:
    """True when `other` is this module's condition order exactly.

    Exists so the equivalence script can assert the adapter's order against
    the order the FROZEN evaluation actually used -- exported from the frozen
    venv rather than retyped -- instead of two copies being trusted to agree.
    An order mismatch mislabels every condition without erroring, so it is
    checked, not assumed.
    """
    return tuple(other) == CONDITIONS
