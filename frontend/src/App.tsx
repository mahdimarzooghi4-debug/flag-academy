import { useQuery } from "@tanstack/react-query";
import { useAuth } from "react-oidc-context";
import { makeApi, type CandidateHomeResponse, type InstructorHomeResponse, type MeResponse } from "./api/client";
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

  return <AuthenticatedApp accessToken={auth.user.access_token} onLogout={() => void auth.removeUser()} />;
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

  if (me.isLoading || candidate.isLoading || instructor.isLoading) return <Loading />;
  const error = me.error || candidate.error || instructor.error;
  if (error) return <div className="center-state error">{error.message}</div>;

  return (
    <>
      <header className="topbar">
        <span className="brand">پرچم</span>
        <button className="ghost" onClick={onLogout}>خروج</button>
      </header>
      {isCandidate && candidate.data ? <CandidateHome data={candidate.data} /> : null}
      {!isCandidate && isInstructor && instructor.data ? <InstructorHome data={instructor.data} /> : null}
      {!isCandidate && !isInstructor ? (
        <div className="center-state">برای این حساب Workspace فعالی تعریف نشده است.</div>
      ) : null}
    </>
  );
}
