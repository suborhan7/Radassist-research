"""
app/models/report.py
====================================================================
reports: one row per POST /generate-report call (Phase 8 DB scope -- see
the frozen architecture's "Database (new reports table)" section).

Naming note: this ORM model is named `ReportRecord`, not `Report` --
`Report` is already the frozen domain entity in app/domain/entities.py,
and silently colliding two same-named classes across the domain/
infrastructure boundary is a real correctness risk (an import alias only
protects call sites that remember to use it), not a cosmetic one. The
newly-introduced infrastructure class is renamed instead of the frozen,
foundational domain concept. The table name itself, "reports", is
unaffected -- only the Python class name differs from the filename-to-
classname convention every other model in this package otherwise follows.

Phase 17: `ai_content` renamed to `ai_draft_content` -- it already WAS
the immutable AI draft (nothing ever updated it post-insert); this names
it correctly rather than adding a duplicate column (see phase17_finalize_
edit_architecture.md Decision 3 and the Step 2 migration). `final_content`
is new, mutable via PATCH /reports/{id}, starts as a deep copy of
ai_draft_content. `finalized_at`/`finalized_by` are new, both nullable
(only set once, by PATCH /reports/{id}/finalize -- see that route for
why a denormalized finalized_by is worth keeping despite always equaling
session.doctor_id under the current ownership model).

Phase 19 Decision 4's resolution: `questionnaire_answers`/`clinical_notes`
are new, both nullable, with a deliberate NULL-vs-empty distinction --
NULL means "this report predates context capture, the real original
value is genuinely unknown" (every row that existed before this
migration, backfilled as NULL on purpose, not a placeholder); an empty
`{}`/`""` means "we know for a fact nothing was provided." Going
forward, `ReportGenerationService.generate()` always writes a real
value (never NULL) for every newly-generated report -- see that
service for why this was previously accepted as a request-body-only
parameter with no persistence at all, which made an existing report's
original generation context impossible to fully reconstruct.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, Enum, Float, ForeignKey, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.domain.entities import ReportStatus

if TYPE_CHECKING:
    from app.models.retrieval_session import RetrievalSession


class ReportRecord(Base):
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("retrieval_sessions.id"), nullable=False, index=True
    )
    language: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[ReportStatus] = mapped_column(
        Enum(ReportStatus), nullable=False, default=ReportStatus.AI_DRAFT
    )
    ai_draft_content: Mapped[dict] = mapped_column(JSON, nullable=False)
    final_content: Mapped[dict] = mapped_column(JSON, nullable=False)
    validation_warnings: Mapped[list] = mapped_column(JSON, nullable=False)
    report_date: Mapped[str] = mapped_column(String, nullable=False)
    llm_model: Mapped[str] = mapped_column(String, nullable=False)
    llm_temperature: Mapped[float] = mapped_column(Float, nullable=False)
    embedding_model: Mapped[str] = mapped_column(String, nullable=False)
    embedding_version: Mapped[str] = mapped_column(String, nullable=False)
    collection_name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finalized_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("doctors.id"), nullable=True
    )
    questionnaire_answers: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    clinical_notes: Mapped[str | None] = mapped_column(String, nullable=True)

    # Input Admission and Modality Gate §7.3 (S5): the retrieval support
    # category and the top-1 similarity it was derived from, both stored
    # WITH the report and both written at generation time.
    #
    # S5's Note gives the reason, and it is the same reason decision D4
    # gives for storing voted_labels/agreement at generation time: the
    # evidence state must not change after the report exists. A category
    # recomputed at read time would drift the moment the ChromaDB
    # collection is rebuilt or RETRIEVAL_FLOOR is recalibrated, and a
    # finalized report would then start describing its own evidence
    # differently than it did when the radiologist signed it.
    #
    # top1_similarity is stored alongside the category, not just the
    # category, so a stored report can still say WHAT was measured and not
    # only which side of the floor it fell on -- §7.2's Rule requires the
    # disclaimer to state the measurement, and re-deriving it later from
    # retrieved_evidence would reintroduce exactly the drift above.
    #
    # Both nullable: every report generated before this migration has no
    # recorded support state, and NULL says that honestly. It does not mean
    # BELOW_FLOOR, and no read path may treat it as a category.
    retrieval_support: Mapped[str | None] = mapped_column(String, nullable=True)
    top1_similarity: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Requirement S7 / decision D4 (migration c3d81b6a4f27): the other two
    # fields of the evidence snapshot. Stored at generation time for the
    # same reason as the two above -- the evidence state must not change
    # after the report exists.
    #
    # Together with retrieval_support/top1_similarity these four columns
    # are what makes a finalized report reconstructable. §7.3's Warning
    # describes the half-written state this completes: with only one of
    # the disclaimer's two signals stored, the report appeared
    # reproducible and was not.
    #
    # `agreement` is stored beside `voted_labels` rather than left to be
    # dug out of voted_labels[0] at read time -- see the migration's
    # docstring; the frontend's known re-derivation defect is what that
    # costs.
    #
    # Both nullable: NULL means "this report predates the snapshot", never
    # "no labels were voted".
    voted_labels: Mapped[list | None] = mapped_column(JSON, nullable=True)
    agreement: Mapped[float | None] = mapped_column(Float, nullable=True)

    # --- Phase 22 v1.2: report self-consistency (migration 7f2a91c4d6e8) ---
    # Frozen architecture: docs/phase22/fix_architecture_v1.2_FROZEN.md §5
    # (frozen at docs commit 810240ea).
    #
    # NULL AND [] ARE NOT INTERCHANGEABLE, and no read path may treat them
    # as such. This is the whole reason these columns exist in this shape:
    #
    #   NULL  -> NO RECORDED CONSISTENCY STATE. Either the report predates
    #            v1.2, or the checks did not run for it. It does NOT mean
    #            the report is clean; nothing was assessed.
    #   []    -> the checks RAN and found nothing. The report is clean, and
    #            `consistency_checks_run` names which checks earned that.
    #
    # Rendering the two identically would turn an acknowledged coverage gap
    # into an affirmative false assurance, which is a worse failure than the
    # gap itself -- see §3.4/§8.8 on Bengali reports, where all three checks
    # are English-only and every `bn` report therefore stores
    # `consistency_checks_run == []` and must display "consistency checks
    # not run", never a clean state.
    #
    # Same JSON column type and nullable-with-no-backfill discipline as
    # voted_labels above (migration c3d81b6a4f27, whose declaration reads
    # `voted_labels: Mapped[list | None] = mapped_column(JSON, nullable=True)`)
    # and the two migrations before it. No server_default and no Python
    # default, deliberately: a default would manufacture a recorded state
    # for rows that never had one, which is exactly the NULL-vs-[] collapse
    # the paragraph above forbids.
    #
    # `consistency_retry_count` counts THIS service's semantic retry (0 or 1,
    # frozen §4). It is NOT D5's structural/content retry count, which counts
    # a different mechanism with a different budget and is deliberately not
    # implemented in v1.2 -- see docs/decisions/decision_log.md. The two must
    # never share a column.
    consistency_violations: Mapped[list | None] = mapped_column(JSON, nullable=True)
    consistency_checks_run: Mapped[list | None] = mapped_column(JSON, nullable=True)
    consistency_retry_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    session: Mapped["RetrievalSession"] = relationship()
