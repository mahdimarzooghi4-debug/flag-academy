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
    onSuccess: async () => {
      await new Promise((resolve) => window.setTimeout(resolve, 800));
      await candidate.refetch();
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
    onSuccess: async () => {
      await new Promise((resolve) => window.setTimeout(resolve, 800));
      await instructor.refetch();
    },
  });

  if (me.isLoading || candidate.isLoading || instructor.isLoading) return <Loading />;
  const error =
    me.error ||
    candidate.error ||
    instructor.error ||
    submitAssignment.error ||
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
