import { useMutation, useQuery } from "@tanstack/react-query";
import { useAuth } from "react-oidc-context";
import {
  makeApi,
  type CandidateHomeResponse,
  type InstructorHomeResponse,
  type MeResponse,
  type MissionTemplateResponse,
} from "./api/client";
import { CandidateHome } from "./components/CandidateHome";
import { InstructorHome } from "./components/InstructorHome";
import {
  MissionWorkspace,
  type MissionCatalogItem,
  type MissionInstance,
} from "./components/MissionWorkspace";
import {
  AcademyStudio,
  type CapabilityOption,
  type MissionAssignmentCandidate,
  type MissionAssignmentSummary,
  type MissionCreateInput,
} from "./components/AcademyStudio";

function Loading({ text = "در حال بارگذاری..." }: { text?: string }) {
  return <div className="center-state">{text}</div>;
}

type RefetchResult<T> = { data?: T };

async function refreshProjectionUntil<T>(
  refetch: () => Promise<RefetchResult<T>>,
  predicate: (data: T | undefined) => boolean,
  attempts = 16,
  intervalMs = 400,
) {
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    const result = await refetch();
    if (predicate(result.data)) return;
    if (attempt < attempts - 1) {
      await new Promise((resolve) => window.setTimeout(resolve, intervalMs));
    }
  }
  throw new Error("به‌روزرسانی نمای خواندنی هنوز تکمیل نشده است؛ دوباره تلاش کنید.");
}

export default function App() {
  const auth = useAuth();

  if (auth.isLoading) return <Loading />;
  if (auth.error) return <div className="center-state error">{auth.error.message}</div>;
  if (!auth.isAuthenticated || !auth.user?.access_token) {
    return (
      <div className="login-shell">
        <p className="eyebrow">FLAG ACADEMY</p>
        <h1>پرچم</h1>
        <p>کلاس، تمرین، شبیه‌سازی و اثبات شایستگی در یک مسیر واحد.</p>
        <button onClick={() => void auth.signinRedirect()}>ورود به آکادمی</button>
      </div>
    );
  }

  return (
    <AuthenticatedApp
      accessToken={auth.user.access_token}
      onLogout={() => void auth.removeUser()}
    />
  );
}

function AuthenticatedApp({
  accessToken,
  onLogout,
}: {
  accessToken: string;
  onLogout: () => void;
}) {
  const api = makeApi(accessToken);
  const me = useQuery({
    queryKey: ["me"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/me");
      if (error || !data) throw new Error("دریافت هویت کاربر ناموفق بود.");
      return data as MeResponse;
    },
  });

  const isCandidate = me.data?.roles.includes("CANDIDATE") ?? false;
  const isInstructor = me.data?.roles.includes("INSTRUCTOR") ?? false;
  const isAdmin = me.data?.roles.includes("ACADEMY_ADMIN") ?? false;

  const capabilities = useQuery({
    queryKey: ["capabilities"],
    enabled: isAdmin,
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/capabilities");
      if (error || !data) throw new Error("دریافت Capabilityها ناموفق بود.");
      return data as CapabilityOption[];
    },
  });

  const missionTemplates = useQuery({
    queryKey: ["mission-templates"],
    enabled: isAdmin,
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/studio/mission-templates");
      if (error || !data) throw new Error("دریافت مأموریت‌ها ناموفق بود.");
      return data as MissionTemplateResponse[];
    },
  });

  const assignmentCandidates = useQuery({
    queryKey: ["mission-assignment-candidates"],
    enabled: isAdmin,
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/studio/mission-assignment-candidates");
      if (error || !data) throw new Error("دریافت Candidateهای قابل Assignment ناموفق بود.");
      return data as MissionAssignmentCandidate[];
    },
  });

  const missionAssignments = useQuery({
    queryKey: ["mission-assignments"],
    enabled: isAdmin,
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/studio/mission-assignments");
      if (error || !data) throw new Error("دریافت Mission Assignmentها ناموفق بود.");
      return data as MissionAssignmentSummary[];
    },
  });

  const candidate = useQuery({
    queryKey: ["candidate-home"],
    enabled: isCandidate,
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/me/candidate-home");
      if (error || !data) throw new Error("دریافت صفحه فراگیر ناموفق بود.");
      return data as CandidateHomeResponse;
    },
  });

  const activeMissions = useQuery({
    queryKey: ["active-missions"],
    enabled: isCandidate,
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/missions/active");
      if (error || !data) throw new Error("دریافت مأموریت‌های فعال ناموفق بود.");
      return data as MissionCatalogItem[];
    },
  });

  const missionInstances = useQuery({
    queryKey: ["mission-instances"],
    enabled: isCandidate,
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/me/mission-instances");
      if (error || !data) throw new Error("دریافت اجرای مأموریت‌ها ناموفق بود.");
      return data as MissionInstance[];
    },
  });

  const instructor = useQuery({
    queryKey: ["instructor-home"],
    enabled: isInstructor && !isCandidate && !isAdmin,
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/me/instructor-home");
      if (error || !data) throw new Error("دریافت صفحه مدرس ناموفق بود.");
      return data as InstructorHomeResponse;
    },
  });

  const createMission = useMutation({
    mutationFn: async (input: MissionCreateInput) => {
      const { error } = await api.POST("/api/v1/studio/mission-templates", {
        body: input,
      });
      if (error) throw new Error("ساخت مأموریت ناموفق بود.");
    },
    onSuccess: async () => {
      await missionTemplates.refetch();
    },
  });

  const validateMission = useMutation({
    mutationFn: async (versionId: string) => {
      const { data, error } = await api.POST(
        "/api/v1/studio/mission-versions/{version_id}/validate-definition",
        { params: { path: { version_id: versionId } } },
      );
      if (error || !data) throw new Error("اعتبارسنجی مأموریت ناموفق بود.");
      return data as { valid: boolean; errors: string[]; warnings: string[] };
    },
  });

  const transitionMission = useMutation({
    mutationFn: async ({
      versionId,
      expectedVersion,
      action,
    }: {
      versionId: string;
      expectedVersion: number;
      action: "pilot" | "mark-validated" | "activate";
    }) => {
      const body = { expected_version: expectedVersion };
      if (action === "pilot") {
        const { error } = await api.POST("/api/v1/studio/mission-versions/{version_id}/pilot", {
          params: { path: { version_id: versionId } },
          body,
        });
        if (error) throw new Error("ورود مأموریت به Pilot ناموفق بود.");
      } else if (action === "mark-validated") {
        const { error } = await api.POST(
          "/api/v1/studio/mission-versions/{version_id}/mark-validated",
          { params: { path: { version_id: versionId } }, body },
        );
        if (error) throw new Error("تأیید مأموریت ناموفق بود.");
      } else {
        const { error } = await api.POST("/api/v1/studio/mission-versions/{version_id}/activate", {
          params: { path: { version_id: versionId } },
          body,
        });
        if (error) throw new Error("فعال‌سازی مأموریت ناموفق بود.");
      }
    },
    onSuccess: async () => {
      await missionTemplates.refetch();
    },
  });

  const startMission = useMutation({
    mutationFn: async ({
      versionId,
      assignmentId,
    }: {
      versionId: string;
      assignmentId: string;
    }) => {
      const { data, error } = await api.POST("/api/v1/missions/{version_id}/instances", {
        params: { path: { version_id: versionId } },
        body: {
          assignment_id: assignmentId,
          idempotency_key: crypto.randomUUID(),
        },
      });
      if (error || !data) throw new Error("شروع مأموریت ناموفق بود.");
      return data as MissionInstance;
    },
    onSuccess: async () => {
      await Promise.all([missionInstances.refetch(), activeMissions.refetch()]);
    },
  });

  const submitMissionAction = useMutation({
    mutationFn: async ({
      instanceId,
      worldVersion,
      actionType,
      target,
      actorVersion,
      payload,
      reasoning,
    }: {
      instanceId: string;
      worldVersion: number;
      actionType:
        | "REQUEST_INFORMATION"
        | "COMMUNICATE"
        | "ESCALATE"
        | "DELEGATE"
        | "CHANGE_SCOPE"
        | "NO_ACTION"
        | "DECIDE";
      target?: string;
      actorVersion?: number;
      payload: Record<string, unknown>;
      reasoning: string;
    }) => {
      const { data, error } = await api.POST(
        "/api/v1/mission-instances/{instance_id}/actions",
        {
          params: { path: { instance_id: instanceId } },
          body: {
            action_type: actionType,
            target: target ?? null,
            payload,
            reasoning,
            confidence: 80,
            expected_world_version: worldVersion,
            expected_actor_version: actorVersion ?? null,
            idempotency_key: crypto.randomUUID(),
            resource_cost: {},
            mode: "CANDIDATE",
            provenance: { surface: "WEB" },
          },
        },
      );
      if (error || !data) throw new Error("ثبت اقدام مأموریت ناموفق بود.");
      return data as MissionInstance;
    },
    onSuccess: async () => {
      await Promise.all([missionInstances.refetch(), activeMissions.refetch()]);
    },
  });

  const advanceMissionWorld = useMutation({
    mutationFn: async ({
      instanceId,
      worldVersion,
    }: {
      instanceId: string;
      worldVersion: number;
    }) => {
      const { data, error } = await api.POST(
        "/api/v1/mission-instances/{instance_id}/advance-to-next-event",
        {
          params: { path: { instance_id: instanceId } },
          body: {
            expected_world_version: worldVersion,
            idempotency_key: crypto.randomUUID(),
          },
        },
      );
      if (error || !data) throw new Error("پیشروی زمان شبیه‌سازی ناموفق بود.");
      return data as MissionInstance;
    },
    onSuccess: async () => {
      await missionInstances.refetch();
    },
  });

  const assignMission = useMutation({
    mutationFn: async ({
      versionId,
      candidateId,
    }: {
      versionId: string;
      candidateId: string;
    }) => {
      const { data, error } = await api.POST("/api/v1/mission-assignments", {
        body: {
          candidate_id: candidateId,
          mission_version_id: versionId,
          assignment_reason: "Assigned from Academy Studio",
          idempotency_key: crypto.randomUUID(),
        },
      });
      if (error || !data) throw new Error("اختصاص مأموریت ناموفق بود.");
      return data as MissionAssignmentSummary;
    },
    onSuccess: async () => {
      await missionAssignments.refetch();
    },
  });

  const updateLearningUnit = useMutation({
    mutationFn: async ({
      learningUnitId,
      action,
    }: {
      learningUnitId: string;
      action: "start" | "complete";
    }) => {
      if (action === "start") {
        const { error } = await api.POST("/api/v1/learning-units/{learning_unit_id}/start", {
          params: { path: { learning_unit_id: learningUnitId } },
        });
        if (error) throw new Error("شروع فعالیت یادگیری ناموفق بود.");
      } else {
        const { error } = await api.POST("/api/v1/learning-units/{learning_unit_id}/complete", {
          params: { path: { learning_unit_id: learningUnitId } },
        });
        if (error) throw new Error("تکمیل فعالیت یادگیری ناموفق بود.");
      }
    },
    onSuccess: async (_data, variables) => {
      await refreshProjectionUntil(
        candidate.refetch,
        (data) =>
          data?.learning_tasks?.some(
            (item) =>
              item.id === variables.learningUnitId &&
              item.status === (variables.action === "start" ? "IN_PROGRESS" : "COMPLETED"),
          ) ?? false,
      );
    },
  });

  const submitPracticeAttempt = useMutation({
    mutationFn: async ({
      learningUnitId,
      response,
    }: {
      learningUnitId: string;
      response: string;
    }) => {
      const { data, error } = await api.POST("/api/v1/practice-units/{learning_unit_id}/attempts", {
        params: { path: { learning_unit_id: learningUnitId } },
        body: { response_text: response },
      });
      if (error || !data) throw new Error("ثبت تمرین ناموفق بود.");
      return data as { id: string };
    },
    onSuccess: async (created, variables) => {
      await refreshProjectionUntil(
        candidate.refetch,
        (data) =>
          data?.learning_tasks
            ?.find((item) => item.id === variables.learningUnitId)
            ?.practice_attempts?.some((attempt) => attempt.id === created.id) ?? false,
      );
    },
  });

  const submitAssignment = useMutation({
    mutationFn: async ({
      assignmentId,
      content,
    }: {
      assignmentId: string;
      content: string;
    }) => {
      const { data, error } = await api.POST("/api/v1/assignments/{assignment_id}/submissions", {
        params: { path: { assignment_id: assignmentId } },
        body: { content_text: content },
      });
      if (error || !data) throw new Error("ثبت تکلیف ناموفق بود.");
      return data as { id: string };
    },
    onSuccess: async (created, variables) => {
      await refreshProjectionUntil(
        candidate.refetch,
        (data) =>
          data?.learning_tasks?.some(
            (item) =>
              item.id === variables.assignmentId &&
              item.submission_id === created.id,
          ) ?? false,
      );
    },
  });

  const recordPracticeFeedback = useMutation({
    mutationFn: async ({
      practiceAttemptId,
      feedback,
    }: {
      practiceAttemptId: string;
      feedback: string;
    }) => {
      const { data, error } = await api.POST(
        "/api/v1/practice-attempts/{practice_attempt_id}/feedback",
        {
          params: { path: { practice_attempt_id: practiceAttemptId } },
          body: { feedback_text: feedback },
        },
      );
      if (error || !data) throw new Error("ثبت بازخورد تمرین ناموفق بود.");
      return data as { id: string; practice_attempt_id: string };
    },
    onSuccess: async (created) => {
      await refreshProjectionUntil(
        instructor.refetch,
        (data) =>
          data?.practice_attempts
            ?.find((item) => item.id === created.practice_attempt_id)
            ?.feedback_history?.some((feedback) => feedback.id === created.id) ?? false,
      );
    },
  });

  const recordFeedback = useMutation({
    mutationFn: async ({
      submissionId,
      feedback,
    }: {
      submissionId: string;
      feedback: string;
    }) => {
      const { error } = await api.POST("/api/v1/submissions/{submission_id}/feedback", {
        params: { path: { submission_id: submissionId } },
        body: { feedback_text: feedback },
      });
      if (error) throw new Error("ثبت بازخورد ناموفق بود.");
    },
    onSuccess: async (_data, variables) => {
      await refreshProjectionUntil(
        instructor.refetch,
        (data) =>
          data?.submissions?.some(
            (item) => item.id === variables.submissionId && Boolean(item.feedback_text),
          ) ?? false,
      );
    },
  });

  if (
    me.isLoading ||
    candidate.isLoading ||
    instructor.isLoading ||
    capabilities.isLoading ||
    missionTemplates.isLoading ||
    assignmentCandidates.isLoading ||
    missionAssignments.isLoading ||
    activeMissions.isLoading ||
    missionInstances.isLoading
  ) return <Loading />;
  const error =
    me.error ||
    candidate.error ||
    instructor.error ||
    capabilities.error ||
    missionTemplates.error ||
    assignmentCandidates.error ||
    missionAssignments.error ||
    activeMissions.error ||
    missionInstances.error ||
    createMission.error ||
    validateMission.error ||
    transitionMission.error ||
    assignMission.error ||
    advanceMissionWorld.error ||
    startMission.error ||
    submitMissionAction.error ||
    updateLearningUnit.error ||
    submitPracticeAttempt.error ||
    submitAssignment.error ||
    recordPracticeFeedback.error ||
    recordFeedback.error;
  if (error) return <div className="center-state error">{error.message}</div>;

  return (
    <>
      <header className="topbar">
        <span className="brand">پرچم</span>
        <button className="ghost" onClick={onLogout}>
          خروج
        </button>
      </header>
      {isAdmin &&
      capabilities.data &&
      missionTemplates.data &&
      assignmentCandidates.data &&
      missionAssignments.data ? (
        <AcademyStudio
          capabilities={capabilities.data}
          templates={missionTemplates.data}
          assignmentCandidates={assignmentCandidates.data}
          assignments={missionAssignments.data}
          onCreate={async (input) => {
            await createMission.mutateAsync(input);
          }}
          onValidate={async (versionId) => validateMission.mutateAsync(versionId)}
          onTransition={async (versionId, expectedVersion, action) => {
            await transitionMission.mutateAsync({ versionId, expectedVersion, action });
          }}
          onAssign={async (versionId, candidateId) => {
            await assignMission.mutateAsync({ versionId, candidateId });
          }}
          busy={
            createMission.isPending ||
            validateMission.isPending ||
            transitionMission.isPending ||
            assignMission.isPending
          }
        />
      ) : null}
      {!isAdmin &&
      isCandidate &&
      candidate.data &&
      activeMissions.data &&
      missionInstances.data ? (
        <>
          <CandidateHome
            data={candidate.data}
            onUpdateLearningUnit={async (learningUnitId, action) => {
              await updateLearningUnit.mutateAsync({ learningUnitId, action });
            }}
            updatingLearningUnitId={
              updateLearningUnit.isPending
                ? updateLearningUnit.variables?.learningUnitId
                : undefined
            }
            onSubmitPracticeAttempt={async (learningUnitId, response) => {
              await submitPracticeAttempt.mutateAsync({ learningUnitId, response });
            }}
            submittingPracticeUnitId={
              submitPracticeAttempt.isPending
                ? submitPracticeAttempt.variables?.learningUnitId
                : undefined
            }
            onSubmitAssignment={async (assignmentId, content) => {
              await submitAssignment.mutateAsync({ assignmentId, content });
            }}
            submittingAssignmentId={
              submitAssignment.isPending ? submitAssignment.variables?.assignmentId : undefined
            }
          />
          <main className="page-shell mission-shell">
            <MissionWorkspace
              missions={activeMissions.data}
              instances={missionInstances.data}
              onStart={async (versionId, assignmentId) => {
                await startMission.mutateAsync({ versionId, assignmentId });
              }}
              onRequestInformation={async (instanceId, worldVersion, label) => {
                await submitMissionAction.mutateAsync({
                  instanceId,
                  worldVersion,
                  actionType: "REQUEST_INFORMATION",
                  payload: { label },
                  reasoning: `Request canonical information: ${label}`,
                });
              }}
              onCommunicate={async (
                instanceId,
                worldVersion,
                actorKey,
                actorVersion,
                communicationCode,
                utterance,
              ) => {
                await submitMissionAction.mutateAsync({
                  instanceId,
                  worldVersion,
                  actionType: "COMMUNICATE",
                  target: actorKey,
                  actorVersion,
                  payload: {
                    communication_code: communicationCode,
                    utterance,
                  },
                  reasoning: utterance,
                });
              }}
              onEscalate={async (
                instanceId,
                worldVersion,
                actorKey,
                actorVersion,
                escalationCode,
                rationale,
              ) => {
                await submitMissionAction.mutateAsync({
                  instanceId,
                  worldVersion,
                  actionType: "ESCALATE",
                  target: actorKey,
                  actorVersion,
                  payload: {
                    escalation_code: escalationCode,
                    rationale,
                  },
                  reasoning: rationale,
                });
              }}
              onDelegate={async (
                instanceId,
                worldVersion,
                actorKey,
                actorVersion,
                delegationCode,
                rationale,
              ) => {
                await submitMissionAction.mutateAsync({
                  instanceId,
                  worldVersion,
                  actionType: "DELEGATE",
                  target: actorKey,
                  actorVersion,
                  payload: {
                    delegation_code: delegationCode,
                    rationale,
                  },
                  reasoning: rationale,
                });
              }}
              onChangeScope={async (
                instanceId,
                worldVersion,
                scopeChangeCode,
                rationale,
              ) => {
                await submitMissionAction.mutateAsync({
                  instanceId,
                  worldVersion,
                  actionType: "CHANGE_SCOPE",
                  payload: {
                    scope_change_code: scopeChangeCode,
                    rationale,
                  },
                  reasoning: rationale,
                });
              }}
              onAdvanceWorld={async (instanceId, worldVersion) => {
                await advanceMissionWorld.mutateAsync({
                  instanceId,
                  worldVersion,
                });
              }}
              onNoAction={async (
                instanceId,
                worldVersion,
                noActionCode,
                rationale,
              ) => {
                await submitMissionAction.mutateAsync({
                  instanceId,
                  worldVersion,
                  actionType: "NO_ACTION",
                  payload: {
                    no_action_code: noActionCode,
                  },
                  reasoning: rationale,
                });
              }}
              onDecide={async (instanceId, worldVersion, decisionCode, reasoning) => {
                await submitMissionAction.mutateAsync({
                  instanceId,
                  worldVersion,
                  actionType: "DECIDE",
                  payload: {
                    decision_code: decisionCode,
                    options_considered: [decisionCode],
                    available_evidence: [],
                    assumptions: [],
                    expected_outcome: "کاهش ریسک و آغاز بازیابی کنترل‌شده",
                    revisit_trigger: "عدم بهبود وضعیت پس از اجرای تصمیم",
                    reversibility: "REVERSIBLE_WITH_COST",
                  },
                  reasoning,
                });
              }}
              busy={
                startMission.isPending ||
                submitMissionAction.isPending ||
                advanceMissionWorld.isPending
              }
            />
          </main>
        </>
      ) : null}
      {!isAdmin && !isCandidate && isInstructor && instructor.data ? (
        <InstructorHome
          data={instructor.data}
          onRecordPracticeFeedback={async (practiceAttemptId, feedback) => {
            await recordPracticeFeedback.mutateAsync({ practiceAttemptId, feedback });
          }}
          submittingPracticeFeedbackId={
            recordPracticeFeedback.isPending
              ? recordPracticeFeedback.variables?.practiceAttemptId
              : undefined
          }
          onRecordFeedback={async (submissionId, feedback) => {
            await recordFeedback.mutateAsync({ submissionId, feedback });
          }}
          submittingFeedbackId={
            recordFeedback.isPending ? recordFeedback.variables?.submissionId : undefined
          }
        />
      ) : null}
      {!isAdmin && !isCandidate && !isInstructor ? (
        <div className="center-state">برای این حساب Workspace فعالی تعریف نشده است.</div>
      ) : null}
    </>
  );
}
