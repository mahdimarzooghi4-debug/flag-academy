import { useMutation, useQuery } from "@tanstack/react-query";
import { useAuth } from "react-oidc-context";
import {
  makeApi,
  type CandidateHomeResponse,
  type InstructorHomeResponse,
  type MeResponse,
} from "./api/client";
import { CandidateHome } from "./components/CandidateHome";
import { InstructorHome } from "./components/InstructorHome";

function Loading({ text = "در حال بارگذاری..." }: { text?: string }) {
  return <div className="center-state">{text}</div>;
}

async function refreshProjectionEventually(
  refetch: () => Promise<unknown>,
  attempts = 12,
  intervalMs = 500,
) {
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    await refetch();
    if (attempt < attempts - 1) {
      await new Promise((resolve) => window.setTimeout(resolve, intervalMs));
    }
  }
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

  const candidate = useQuery({
    queryKey: ["candidate-home"],
    enabled: isCandidate,
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/me/candidate-home");
      if (error || !data) throw new Error("دریافت صفحه فراگیر ناموفق بود.");
      return data as CandidateHomeResponse;
    },
  });

  const instructor = useQuery({
    queryKey: ["instructor-home"],
    enabled: isInstructor && !isCandidate,
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/me/instructor-home");
      if (error || !data) throw new Error("دریافت صفحه مدرس ناموفق بود.");
      return data as InstructorHomeResponse;
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
    onSuccess: () => {
      void refreshProjectionEventually(candidate.refetch);
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
      const { error } = await api.POST("/api/v1/practice-units/{learning_unit_id}/attempts", {
        params: { path: { learning_unit_id: learningUnitId } },
        body: { response_text: response },
      });
      if (error) throw new Error("ثبت تمرین ناموفق بود.");
    },
    onSuccess: () => {
      void refreshProjectionEventually(candidate.refetch);
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
      const { error } = await api.POST("/api/v1/assignments/{assignment_id}/submissions", {
        params: { path: { assignment_id: assignmentId } },
        body: { content_text: content },
      });
      if (error) throw new Error("ثبت تکلیف ناموفق بود.");
    },
    onSuccess: () => {
      void refreshProjectionEventually(candidate.refetch);
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
      const { error } = await api.POST(
        "/api/v1/practice-attempts/{practice_attempt_id}/feedback",
        {
          params: { path: { practice_attempt_id: practiceAttemptId } },
          body: { feedback_text: feedback },
        },
      );
      if (error) throw new Error("ثبت بازخورد تمرین ناموفق بود.");
    },
    onSuccess: () => {
      void refreshProjectionEventually(instructor.refetch);
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
    onSuccess: () => {
      void refreshProjectionEventually(instructor.refetch);
    },
  });

  if (me.isLoading || candidate.isLoading || instructor.isLoading) return <Loading />;
  const error =
    me.error ||
    candidate.error ||
    instructor.error ||
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
      {isCandidate && candidate.data ? (
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
      ) : null}
      {!isCandidate && isInstructor && instructor.data ? (
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
      {!isCandidate && !isInstructor ? (
        <div className="center-state">برای این حساب Workspace فعالی تعریف نشده است.</div>
      ) : null}
    </>
  );
}
