"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  ApiError,
  finalizeReport,
  getCurrentDoctor,
  getPatient,
  getReport,
  regenerateSection,
  updateReport,
} from "@/lib/api-client";
import { computeAgreement } from "@/lib/evidence-agreement";
import { computeReportDiff, type ReportDiffSummary } from "@/lib/report-diff";
import { useDoctorName } from "@/lib/use-doctor-name";
import { useT } from "@/lib/i18n";
import {
  EDITABLE_REPORT_FIELDS,
  type EditableReportField,
  type ReportContentKey,
} from "@/lib/report-fields";
import type { paths } from "@/lib/generated/api";

type ReportDetailResponse =
  paths["/reports/{report_id}"]["get"]["responses"][200]["content"]["application/json"];
type PatientResponse =
  paths["/patients/{patient_id}"]["get"]["responses"][200]["content"]["application/json"];

export type EvidenceTab = "evidence" | "agreement" | "alternatives";

export interface RegenerationResult {
  field: EditableReportField;
  candidate: string;
  contextIncomplete: boolean;
}

export interface WorkspaceValue {
  reportId: string;
  report: ReportDetailResponse | null;
  patient: PatientResponse | null;
  error: string | null;
  currentDoctorId: string | null;

  reportOwnerId: string | null;
  isOwner: boolean;
  canEdit: boolean;
  otherOwnerName: string | null;
  finalizedByName: string | null;

  /** Derived from the report, so the evidence route needs no fetch of its own. */
  agreement: ReturnType<typeof computeAgreement> | null;
  diffSummary: ReportDiffSummary | null;

  savingField: ReportContentKey | null;
  restoring: boolean;
  actionError: string | null;
  dirtyFields: Set<ReportContentKey>;
  editingFields: Set<ReportContentKey>;
  hasUnsavedChanges: boolean;

  regeneratingField: EditableReportField | null;
  regenerationResult: RegenerationResult | null;
  regenerationError: string | null;
  regenerationErrorField: EditableReportField | null;

  /** Survives navigation between the report and evidence routes. */
  railTab: EvidenceTab;
  setRailTab: (tab: EvidenceTab) => void;
  showDiff: boolean;
  setShowDiff: (next: boolean) => void;
  showPreview: boolean;
  setShowPreview: (next: boolean) => void;
  printing: boolean;

  handleCommit: (key: ReportContentKey, nextValue: string) => Promise<void>;
  handleRestoreAiDraft: () => Promise<void>;
  handleRegenerate: (field: EditableReportField) => Promise<void>;
  handleAcceptRegeneration: () => Promise<void>;
  handleDiscardRegeneration: () => void;
  handleFinalizeConfirm: () => Promise<void>;
  handleDirtyChange: (key: ReportContentKey, dirty: boolean) => void;
  handleEditingChange: (key: ReportContentKey, editing: boolean) => void;
  /** Attach to any in-app link that leaves unsaved work behind. */
  guardedNavigate: (e: { preventDefault: () => void }) => void;
}

const WorkspaceContext = createContext<WorkspaceValue | null>(null);

/**
 * The one owner of a report, for as long as the reader is anywhere in its
 * workspace.
 *
 * WHY THIS EXISTS AT ALL. The workspace used to be one route that fetched the
 * report in its own effect. Splitting it into Generate / Report / Evidence
 * pages would have meant three routes each fetching their own copy -- which is
 * exactly what `/explain` and `/compare` already do today, and exactly what the
 * brief forbids: moving between the report and its evidence must not refetch
 * anything. A Next segment layout stays mounted while its children change, so
 * hoisting the fetch here makes "no refetch on navigate" a property of where
 * the state lives rather than of a cache that has to be kept correct.
 *
 * It is deliberately a component, not a hook wired into a layout file, so a
 * test can mount it without a router. No test in this repo mounts a route
 * module -- they all avoid `next/navigation` -- so anything that needs
 * asserting has to be reachable from an ordinary render.
 *
 * WHAT HAD TO COME WITH IT. The mutation handlers, because they call
 * `setReport` with the server's response and that response has to be the one
 * every page sees. The dirty/editing sets, because `hasUnsavedChanges` drives
 * both the beforeunload guard and the in-app link guard, and those now have to
 * cover the step indicator too. And `railTab`, because "the active evidence tab
 * is preserved when returning" is only true if the tab is not owned by the
 * route that keeps unmounting.
 */
export function WorkspaceProvider({
  reportId,
  children,
}: {
  reportId: string;
  children: ReactNode;
}) {
  const { t } = useT();

  const [report, setReport] = useState<ReportDetailResponse | null>(null);
  const [patient, setPatient] = useState<PatientResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [currentDoctorId, setCurrentDoctorId] = useState<string | null>(null);

  const [savingField, setSavingField] = useState<ReportContentKey | null>(null);
  const [restoring, setRestoring] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [showPreview, setShowPreview] = useState(false);
  const [showDiff, setShowDiff] = useState(false);
  const [dirtyFields, setDirtyFields] = useState<Set<ReportContentKey>>(new Set());
  const [editingFields, setEditingFields] = useState<Set<ReportContentKey>>(new Set());
  const [printing, setPrinting] = useState(false);
  const [railTab, setRailTab] = useState<EvidenceTab>("evidence");

  const [regeneratingField, setRegeneratingField] = useState<EditableReportField | null>(null);
  const [regenerationResult, setRegenerationResult] = useState<RegenerationResult | null>(null);
  const [regenerationError, setRegenerationError] = useState<string | null>(null);
  const [regenerationErrorField, setRegenerationErrorField] = useState<EditableReportField | null>(null);

  // Keyed on reportId ONLY. Navigating between this workspace's pages does not
  // change it, so this effect does not re-run and nothing is refetched.
  useEffect(() => {
    getReport(reportId)
      .then(async (reportResult) => {
        setReport(reportResult);
        if (reportResult.patient_id) {
          try {
            setPatient(await getPatient(reportResult.patient_id));
          } catch {
            setPatient(null);
          }
        }
      })
      .catch((err) => {
        setError(err instanceof ApiError ? err.message : t("workspace.errLoad"));
      });
    getCurrentDoctor()
      .then((doctor) => setCurrentDoctorId(doctor?.id ?? null))
      .catch(() => setCurrentDoctorId(null));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reportId]);

  const agreement = useMemo(() => {
    if (!report) return null;
    return computeAgreement(report.retrieved_cases);
  }, [report]);

  const diffSummary = useMemo(() => {
    if (!report) return null;
    return computeReportDiff(report.ai_draft_content, report.content);
  }, [report]);

  const reportOwnerId = report?.doctor_id ?? null;
  const isOwner = reportOwnerId !== null && currentDoctorId !== null && reportOwnerId === currentDoctorId;
  const otherOwnerName = useDoctorName(isOwner ? null : reportOwnerId);
  const finalizedByName = useDoctorName(report?.finalized_by ?? null);

  const canEdit = isOwner && report?.status !== "final";
  const hasUnsavedChanges = dirtyFields.size > 0;

  const handleDirtyChange = useCallback((key: ReportContentKey, dirty: boolean) => {
    setDirtyFields((prev) => {
      const next = new Set(prev);
      if (dirty) next.add(key);
      else next.delete(key);
      return next;
    });
  }, []);

  const handleEditingChange = useCallback((key: ReportContentKey, editing: boolean) => {
    setEditingFields((prev) => {
      const next = new Set(prev);
      if (editing) next.add(key);
      else next.delete(key);
      return next;
    });
  }, []);

  // beforeunload -- covers tab close/refresh/typed-URL navigation. This is
  // the one part of the guard the browser itself enforces; guardedNavigate
  // below is a best-effort in-app interception only.
  useEffect(() => {
    function handler(e: BeforeUnloadEvent) {
      if (hasUnsavedChanges) {
        e.preventDefault();
        e.returnValue = "";
      }
    }
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [hasUnsavedChanges]);

  /**
   * Printing counts as "the full report is open", because what the browser
   * puts on paper must be the whole document. There is no in-app PDF view to
   * hook instead; the print path IS that path. matchMedia is checked alongside
   * the events because Safari fires the query but not beforeprint/afterprint.
   */
  useEffect(() => {
    const before = () => setPrinting(true);
    const after = () => setPrinting(false);
    window.addEventListener("beforeprint", before);
    window.addEventListener("afterprint", after);

    const mql = window.matchMedia?.("print");
    const onChange = (e: MediaQueryListEvent) => setPrinting(e.matches);
    mql?.addEventListener?.("change", onChange);

    return () => {
      window.removeEventListener("beforeprint", before);
      window.removeEventListener("afterprint", after);
      mql?.removeEventListener?.("change", onChange);
    };
  }, []);

  const guardedNavigate = useCallback(
    (e: { preventDefault: () => void }) => {
      if (hasUnsavedChanges && !window.confirm(t("workspace.confirmLeave"))) {
        e.preventDefault();
      }
    },
    [hasUnsavedChanges, t],
  );

  const handleCommit = useCallback(
    async (key: ReportContentKey, nextValue: string) => {
      setSavingField(key);
      setActionError(null);
      try {
        const updated = await updateReport(reportId, { [key]: nextValue });
        setReport(updated);
      } catch (err) {
        setActionError(err instanceof ApiError ? err.message : t("workspace.errSave"));
      } finally {
        setSavingField(null);
      }
    },
    [reportId, t],
  );

  const handleRestoreAiDraft = useCallback(async () => {
    if (!report) return;
    if (!window.confirm(t("workspace.confirmRestore"))) return;
    setRestoring(true);
    setActionError(null);
    try {
      const restoreValues = EDITABLE_REPORT_FIELDS.reduce(
        (acc, field) => {
          acc[field] = report.ai_draft_content[field];
          return acc;
        },
        {} as Record<EditableReportField, string>,
      );
      const updated = await updateReport(reportId, restoreValues);
      setReport(updated);
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : t("workspace.errRestore"));
    } finally {
      setRestoring(false);
    }
  }, [report, reportId, t]);

  const handleRegenerate = useCallback(
    async (field: EditableReportField) => {
      setRegeneratingField(field);
      setRegenerationError(null);
      setRegenerationErrorField(null);
      setRegenerationResult(null);
      try {
        const result = await regenerateSection(reportId, field);
        setRegenerationResult({
          field,
          candidate: result.candidate,
          contextIncomplete: result.context_incomplete,
        });
      } catch (err) {
        setRegenerationError(err instanceof ApiError ? err.message : t("workspace.errRegen"));
        setRegenerationErrorField(field);
      } finally {
        setRegeneratingField(null);
      }
    },
    [reportId, t],
  );

  const handleAcceptRegeneration = useCallback(async () => {
    if (!regenerationResult) return;
    await handleCommit(regenerationResult.field, regenerationResult.candidate);
    setRegenerationResult(null);
  }, [regenerationResult, handleCommit]);

  const handleDiscardRegeneration = useCallback(() => {
    // No request fired at all -- Decision 1's entire point.
    setRegenerationResult(null);
  }, []);

  const handleFinalizeConfirm = useCallback(async () => {
    const updated = await finalizeReport(reportId);
    setReport(updated);
    setShowPreview(false);
  }, [reportId]);

  const value = useMemo<WorkspaceValue>(
    () => ({
      reportId,
      report,
      patient,
      error,
      currentDoctorId,
      reportOwnerId,
      isOwner,
      canEdit: !!canEdit,
      otherOwnerName,
      finalizedByName,
      agreement,
      diffSummary,
      savingField,
      restoring,
      actionError,
      dirtyFields,
      editingFields,
      hasUnsavedChanges,
      regeneratingField,
      regenerationResult,
      regenerationError,
      regenerationErrorField,
      railTab,
      setRailTab,
      showDiff,
      setShowDiff,
      showPreview,
      setShowPreview,
      printing,
      handleCommit,
      handleRestoreAiDraft,
      handleRegenerate,
      handleAcceptRegeneration,
      handleDiscardRegeneration,
      handleFinalizeConfirm,
      handleDirtyChange,
      handleEditingChange,
      guardedNavigate,
    }),
    [
      reportId, report, patient, error, currentDoctorId, reportOwnerId, isOwner, canEdit,
      otherOwnerName, finalizedByName, agreement, diffSummary, savingField, restoring,
      actionError, dirtyFields, editingFields, hasUnsavedChanges, regeneratingField,
      regenerationResult, regenerationError, regenerationErrorField, railTab, showDiff,
      showPreview, printing, handleCommit, handleRestoreAiDraft, handleRegenerate,
      handleAcceptRegeneration, handleDiscardRegeneration, handleFinalizeConfirm,
      handleDirtyChange, handleEditingChange, guardedNavigate,
    ],
  );

  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
}

export function useWorkspace(): WorkspaceValue {
  const ctx = useContext(WorkspaceContext);
  if (!ctx) throw new Error("useWorkspace must be used within a WorkspaceProvider");
  return ctx;
}
