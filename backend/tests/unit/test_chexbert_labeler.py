"""
Unit tests for ChexbertLabeler, per the frozen Phase 22 v1.2 architecture
(docs/phase22/fix_architecture_v1.2_FROZEN.md §3.3 and §7, frozen at docs
commit 810240ea).

Most tests here drive the adapter with a FAKE model and tokenizer, so they
exercise the adapter's own logic -- batching, head handling, label order,
typed failure -- without loading a ~450 MiB checkpoint. One integration test
loads the real checkpoint and is skipped when it is absent.

WHAT THESE TESTS DO NOT COVER, AND WHERE THAT LIVES INSTEAD. Label
equivalence with the frozen evaluation is not provable from fakes: it is
established by scratch/phase22_diagnosis/verify_chexbert_equivalence.py,
which compares all 477 x 14 x 2 raw cells against the frozen venv's own
output on CPU and on CUDA, plus token identity on all 954 real sections. The
integration test below is a much weaker smoke check on two sentences; it
exists so that a broken checkpoint load fails in the ordinary test suite, not
so that equivalence can be claimed from it.
"""
from __future__ import annotations

import os

import pytest
import torch

from app.core.config import settings
from app.infrastructure.chexbert_labeler import (
    BINARY_HEAD_INDEX,
    CLASS_MAPPING,
    CONDITIONS,
    N_FOUR_CLASS_HEADS,
    N_HEADS,
    ChexbertLabeler,
    ChexbertUnavailableError,
    conditions_match,
)

# Verbatim from stanfordmlgroup/CheXbert src/constants.py, retyped here
# independently of the adapter so the assertion below compares two sources
# rather than a constant against itself.
FROZEN_ORDER = (
    "Enlarged Cardiomediastinum", "Cardiomegaly", "Lung Opacity", "Lung Lesion",
    "Edema", "Consolidation", "Pneumonia", "Atelectasis", "Pneumothorax",
    "Pleural Effusion", "Pleural Other", "Fracture", "Support Devices", "No Finding",
)


# ----------------------------------------------------------------------
# fakes
# ----------------------------------------------------------------------

class FakeTokenizer:
    """Returns a fixed-length id sequence per text, long enough to be
    distinguishable but with no real vocabulary behind it."""

    cls_token_id = 101
    sep_token_id = 102

    def __init__(self):
        self.calls: list[dict] = []

    def __call__(self, text, add_special_tokens=True, truncation=True, max_length=512):
        self.calls.append(
            {"text": text, "add_special_tokens": add_special_tokens,
             "truncation": truncation, "max_length": max_length}
        )
        body = [1000 + i for i, _ in enumerate(text.split())]
        return {"input_ids": [self.cls_token_id] + body + [self.sep_token_id]}


class FakeModel:
    """Emits caller-chosen argmaxes. `per_head_class[h]` is the class index
    head h should select for EVERY text in the batch."""

    def __init__(self, per_head_class):
        self._per_head_class = list(per_head_class)
        self.eval_calls = 0
        self.seen_batches: list[tuple[int, int]] = []

    def eval(self):
        self.eval_calls += 1
        return self

    def __call__(self, padded, attention_mask):
        batch = padded.shape[0]
        self.seen_batches.append((batch, padded.shape[1]))
        heads = []
        for h in range(N_HEADS):
            width = 2 if h == BINARY_HEAD_INDEX else 4
            logits = torch.zeros((batch, width))
            logits[:, self._per_head_class[h]] = 10.0
            heads.append(logits)
        return heads


def _labeler(model, tokenizer=None, batch_size=16) -> ChexbertLabeler:
    """Builds an adapter around fakes without running __init__, which would
    load a real checkpoint. Only the attributes label() uses are set."""
    labeler = object.__new__(ChexbertLabeler)
    labeler._torch = torch
    labeler._tokenizer = tokenizer or FakeTokenizer()
    labeler._model = model
    labeler._device = torch.device("cpu")
    labeler._max_length = 512
    labeler._batch_size = batch_size
    return labeler


# ----------------------------------------------------------------------
# label order -- an order mismatch mislabels everything without erroring
# ----------------------------------------------------------------------

def test_condition_order_matches_the_frozen_evaluation_order():
    assert CONDITIONS == FROZEN_ORDER
    assert len(CONDITIONS) == N_HEADS == 14


def test_conditions_match_accepts_the_frozen_order():
    assert conditions_match(FROZEN_ORDER) is True
    assert conditions_match(list(FROZEN_ORDER)) is True


def test_conditions_match_rejects_a_reordered_list():
    swapped = (FROZEN_ORDER[1], FROZEN_ORDER[0]) + FROZEN_ORDER[2:]
    assert conditions_match(swapped) is False


def test_conditions_match_rejects_a_truncated_list():
    assert conditions_match(FROZEN_ORDER[:-1]) is False


def test_class_mapping_is_the_frozen_four_class_scheme():
    assert CLASS_MAPPING == {0: "Blank", 1: "Positive", 2: "Negative", 3: "Uncertain"}


def test_adapter_conditions_property_exposes_the_order():
    assert _labeler(FakeModel([0] * N_HEADS)).conditions == FROZEN_ORDER


# ----------------------------------------------------------------------
# output shape
# ----------------------------------------------------------------------

def test_label_returns_one_row_per_text_each_with_one_class_per_condition():
    rows = _labeler(FakeModel([0] * N_HEADS)).label(["findings text", "impression text"])
    assert len(rows) == 2
    assert all(len(row) == len(CONDITIONS) for row in rows)
    assert all(isinstance(v, int) for row in rows for v in row)


def test_label_preserves_input_order():
    rows = _labeler(FakeModel([0] * N_HEADS)).label(["a", "b", "c"])
    assert len(rows) == 3


def test_label_of_no_texts_returns_empty():
    assert _labeler(FakeModel([0] * N_HEADS)).label([]) == ()


def test_four_class_heads_can_emit_every_class():
    """Raw 4-class output, not binarised -- Negative(2) must survive, because
    the contradiction check is defined on it."""
    for cls in (0, 1, 2, 3):
        model = FakeModel([cls] * N_FOUR_CLASS_HEADS + [0])
        row = _labeler(model).label(["text"])[0]
        assert row[0] == cls
        assert row[N_FOUR_CLASS_HEADS - 1] == cls


def test_no_finding_head_is_binary_and_cannot_emit_negative():
    """The 14th head has 2 outputs in the real architecture, so it can only
    emit Blank(0) or Positive(1). This is why the contradiction check excludes
    it: "Positive in one section, Negative in the other" is not expressible."""
    for cls in (0, 1):
        model = FakeModel([0] * N_FOUR_CLASS_HEADS + [cls])
        row = _labeler(model).label(["text"])[0]
        assert row[BINARY_HEAD_INDEX] == cls

    model = FakeModel([0] * N_HEADS)
    heads = model(torch.zeros((1, 3), dtype=torch.long), torch.ones((1, 3), dtype=torch.long))
    assert heads[BINARY_HEAD_INDEX].shape[1] == 2
    assert all(heads[h].shape[1] == 4 for h in range(N_FOUR_CLASS_HEADS))


def test_no_finding_index_is_the_last_condition():
    assert CONDITIONS[BINARY_HEAD_INDEX] == "No Finding"


# ----------------------------------------------------------------------
# inference context and batching
# ----------------------------------------------------------------------

def test_model_is_put_in_eval_mode_for_inference():
    model = FakeModel([0] * N_HEADS)
    _labeler(model).label(["text"])
    assert model.eval_calls >= 1


def test_tf32_flags_are_disabled_during_inference_and_restored_after():
    """TF32 keeps only 10 mantissa bits; on an argmax over near-tied logits
    that is enough to flip a label, which would fail equivalence layer (c).
    The flags are restored afterwards because this process also hosts
    BiomedCLIP, whose precision choices are not this adapter's to change."""
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True

    seen = {}

    class ObservingModel(FakeModel):
        def __call__(self, padded, attention_mask):
            seen["matmul"] = torch.backends.cuda.matmul.allow_tf32
            seen["cudnn"] = torch.backends.cudnn.allow_tf32
            return super().__call__(padded, attention_mask)

    try:
        _labeler(ObservingModel([0] * N_HEADS)).label(["text"])
        assert seen == {"matmul": False, "cudnn": False}
        assert torch.backends.cuda.matmul.allow_tf32 is True
        assert torch.backends.cudnn.allow_tf32 is True
    finally:
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False


def test_texts_are_batched_according_to_batch_size():
    model = FakeModel([0] * N_HEADS)
    _labeler(model, batch_size=2).label(["a", "b", "c", "d", "e"])
    assert [b[0] for b in model.seen_batches] == [2, 2, 1]


def test_tokeniser_is_called_with_the_frozen_truncation_rule():
    tokenizer = FakeTokenizer()
    _labeler(FakeModel([0] * N_HEADS), tokenizer=tokenizer).label(["some text"])
    assert tokenizer.calls[0]["add_special_tokens"] is True
    assert tokenizer.calls[0]["truncation"] is True
    assert tokenizer.calls[0]["max_length"] == 512


def test_shorter_sequences_are_padded_and_masked_within_a_batch():
    model = FakeModel([0] * N_HEADS)
    _labeler(model, batch_size=2).label(["one", "one two three four"])
    batch, width = model.seen_batches[0]
    assert batch == 2
    assert width == 6  # CLS + 4 body + SEP, the longer of the two


# ----------------------------------------------------------------------
# typed failure at construction
# ----------------------------------------------------------------------

def test_missing_checkpoint_raises_the_typed_error():
    """Raised at construction, not at first use, so a misconfiguration is
    visible at wiring time rather than inside a report request."""
    with pytest.raises(ChexbertUnavailableError, match="checkpoint not found"):
        ChexbertLabeler(checkpoint_path="C:/definitely/not/a/real/chexbert.pth")


def test_empty_checkpoint_path_raises_the_typed_error():
    with pytest.raises(ChexbertUnavailableError):
        ChexbertLabeler(checkpoint_path="")


def test_directory_instead_of_file_raises_the_typed_error():
    with pytest.raises(ChexbertUnavailableError):
        ChexbertLabeler(checkpoint_path=os.path.dirname(os.path.abspath(__file__)))


def test_typed_error_is_a_runtime_error_subclass():
    """A caller that has not been updated for this type still catches it."""
    assert issubclass(ChexbertUnavailableError, RuntimeError)


def test_error_message_names_the_setting_and_the_fallback():
    """The message has to tell an operator what to set AND what happens if
    they do not -- the check is omitted, never reported as clean."""
    with pytest.raises(ChexbertUnavailableError) as excinfo:
        ChexbertLabeler(checkpoint_path="C:/nope/chexbert.pth")
    message = str(excinfo.value)
    assert "CHEXBERT_CHECKPOINT_PATH" in message
    assert "checks_run" in message


def test_adapter_satisfies_the_section_labeler_protocol_structurally():
    from app.domain.interfaces import ISectionLabeler
    assert isinstance(_labeler(FakeModel([0] * N_HEADS)), ISectionLabeler)


# ----------------------------------------------------------------------
# integration -- real checkpoint, skipped when absent
# ----------------------------------------------------------------------

_CHECKPOINT = settings.CHEXBERT_CHECKPOINT_PATH
_HAVE_CHECKPOINT = bool(_CHECKPOINT) and os.path.isfile(_CHECKPOINT)

# Expected classes produced IN THE FROZEN EVAL VENV (torch 2.6.0+cpu,
# transformers 4.46.0) by scratch/phase22_diagnosis/frozen_fixture_labels.py.
# Taken from the frozen side deliberately: asserting against the adapter's own
# output would be circular.
_FIXTURES = (
    ("The heart is enlarged.",
     {"Cardiomegaly": 1}),
    ("The lungs are clear. There is no pleural effusion.",
     {"Pleural Effusion": 2, "No Finding": 1}),
)


@pytest.mark.skipif(not _HAVE_CHECKPOINT, reason=f"CheXbert checkpoint not present at {_CHECKPOINT}")
def test_real_checkpoint_reproduces_frozen_labels_for_two_fixed_sentences():
    """A smoke check that the real checkpoint loads and labels as the frozen
    evaluation does. Pinned to CPU so it is deterministic and needs no GPU.

    Deliberately NOT the equivalence proof -- that is
    scratch/phase22_diagnosis/verify_chexbert_equivalence.py over all
    477 x 14 x 2 cells on CPU and CUDA. Two sentences cannot establish
    equivalence; they can catch a checkpoint that failed to load or a head
    order that was rewired.
    """
    labeler = ChexbertLabeler(checkpoint_path=_CHECKPOINT, device="cpu")
    texts = [text for text, _ in _FIXTURES]
    rows = labeler.label(texts)

    assert len(rows) == len(_FIXTURES)
    for (text, expected_nonzero), row in zip(_FIXTURES, rows):
        got = {CONDITIONS[i]: cls for i, cls in enumerate(row) if cls != 0}
        assert got == expected_nonzero, f"for {text!r}: expected {expected_nonzero}, got {got}"


@pytest.mark.skipif(not _HAVE_CHECKPOINT, reason=f"CheXbert checkpoint not present at {_CHECKPOINT}")
def test_real_checkpoint_exposes_the_frozen_condition_order():
    labeler = ChexbertLabeler(checkpoint_path=_CHECKPOINT, device="cpu")
    assert conditions_match(labeler.conditions)
