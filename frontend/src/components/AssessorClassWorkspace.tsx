import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { makeApi } from "../api/client";
import type {
  InstructorAttendance, InstructorClassActivity, InstructorRoster, InstructorSession,
} from "./InstructorClassWorkspace";
import type { CandidateClassReport } from "./CandidateReportWorkspace";

export type AssignedAssessorClass = {
  class_offering_id: string;
  cohort_id: string;
  title: string;
  grant_id: string;
  grant_version: number;
  starts_at: string;
  ends_at: string;
};
export type AssignedAssessorClassPage = {
  items: AssignedAssessorClass[];
  next_offset: number | null;
};

const PAGE_SIZE = 50;
const READ_REFRESH_MS = 3000;

function attendanceText(value: string | undefined) {
  if (value === "PRESENT") return "حاضر";
  if (value === "ABSENT") return "غایب (ثبت‌شده)";
  if (!value) return "ثبت نشده؛ غیبت محسوب نمی‌شود";
  return "وضعیت حضور نامعتبر";
}
function learningText(value: string | null) {
  if (value === "TO_LEARN") return "هنوز آغاز نشده";
  if (value === "IN_LEARNING") return "در حال یادگیری";
  if (value === "LEARNING_COMPLETED") return "آموزش تکمیل شده؛ اثبات شایستگی نیست";
  return "وضعیت آموزشی نامشخص";
}

export function AssessorClassView({
  classes, classId, onClassChange, pageOffset, onPageOffset,
  roster, sessions, sessionId, onSessionChange, attendance, activity,
  personId, onPersonChange, report, loading = false, error,
}: {
  classes: AssignedAssessorClassPage;
  classId?: string;
  onClassChange: (id: string) => void;
  pageOffset: number;
  onPageOffset: (offset: number) => void;
  roster?: InstructorRoster;
  sessions?: InstructorSession[];
  sessionId?: string;
  onSessionChange: (id: string) => void;
  attendance?: InstructorAttendance;
  activity?: InstructorClassActivity;
  personId?: string;
  onPersonChange: (id: string) => void;
  report?: CandidateClassReport;
  loading?: boolean;
  error?: string;
}) {
  const selected = classes.items.find((item) => item.class_offering_id === classId);
  // Failed/partial class reads are not evidence of a valid ongoing appointment.
  const scoped =
    !loading && !error && selected &&
    roster?.class_offering_id === selected.class_offering_id &&
    roster?.cohort_id === selected.cohort_id &&
    sessions?.every((item) => item.class_offering_id === selected.class_offering_id) &&
    activity?.class_offering_id === selected.class_offering_id;
  const learners = scoped && roster ? roster.members.filter((item) => item.member_type === "CANDIDATE") : [];
  const recorded = new Map(
    attendance && attendance.session_id === sessionId
      ? attendance.items.map((item) => [item.person_id, item.status])
      : [],
  );
  const validReport = scoped && report &&
    report.class_offering_id === classId && report.cohort_id === selected?.cohort_id &&
    report.person_id === personId && learners.some((item) => item.person_id === personId);

  return (
    <main className="page-shell" data-testid="assessor-class-workspace">
      <section className="panel">
        <p className="eyebrow">ACADEMY ASSESSOR</p>
        <h2>کلاس‌های مأموریت‌دار ارزیاب</h2>
        <p className="muted">
          فقط کلاس‌های دارای انتصاب زنده، در سازمان جاری و با دسترسی خواندنی.
          این صفحه مجوز پذیرش Evidence، تغییر Profile یا تصمیم Gate ایجاد نمی‌کند.
        </p>
        {error ? <p role="alert" className="error">{error}</p> : null}
        {loading ? <p role="status">در حال بررسی مجوز زنده کلاس...</p> : null}
        {classes.items.length === 0 && !loading && !error ? (
          <p role="status">اکنون مأموریت معتبر کلاسی ندارید.</p>
        ) : null}
        {classes.items.length > 0 && !error ? (
          <div className="form-stack">
            <label htmlFor="assessor-class-choice">کلاس منصوب‌شده</label>
            <select id="assessor-class-choice" value={selected?.class_offering_id ?? ""}
              disabled={loading}
              onChange={(e) => onClassChange(e.target.value)}>
              {classes.items.map((item) => (
                <option key={item.grant_id} value={item.class_offering_id}>
                  {item.title}
                </option>
              ))}
            </select>
            {selected ? <p className="muted">
              مأموریت: {selected.starts_at} تا {selected.ends_at} · نسخه {selected.grant_version}
            </p> : null}
            <div className="action-row">
              <button type="button" className="ghost" disabled={loading || pageOffset === 0}
                onClick={() => onPageOffset(Math.max(0, pageOffset - PAGE_SIZE))}>کلاس‌های قبل</button>
              {classes.next_offset !== null ? (
                <button type="button" className="ghost" disabled={loading}
                  onClick={() => onPageOffset(classes.next_offset!)}>کلاس‌های بعد</button>
              ) : null}
            </div>
          </div>
        ) : null}
      </section>

      {scoped ? (
        <>
          <section className="panel">
            <h2>افراد و جلسات کلاس مجاز</h2>
            <p className="muted">فقط اعضای همان Cohort و کلاس مأموریت‌دار نمایش داده می‌شوند.</p>
            {learners.map((learner) => (
              <p className="assessor-class-member" key={learner.person_id} dir="ltr">{learner.person_id}</p>
            ))}
            {learners.length === 0 ? <p>فراگیری ثبت نشده است.</p> : null}
            {(sessions ?? []).length > 0 ? (
              <div className="form-stack">
                <label htmlFor="assessor-class-session">جلسه مجاز</label>
                <select id="assessor-class-session" value={sessionId ?? ""}
                  onChange={(e) => onSessionChange(e.target.value)}>
                  {(sessions ?? []).map((item) => (
                    <option key={item.session_id} value={item.session_id}>{item.title}</option>
                  ))}
                </select>
              </div>
            ) : <p>جلسه ثبت نشده است.</p>}
            {sessionId && attendance?.session_id === sessionId ? learners.map((learner) => (
              <div key={learner.person_id} className="assessor-class-attendance">
                <span dir="ltr">{learner.person_id}</span>
                <span>{attendanceText(recorded.get(learner.person_id))}</span>
              </div>
            )) : null}
            <p className="muted">حضور ثبت‌نشده غیبت نیست؛ ارزیاب اختیار ثبت یا اصلاح حضور ندارد.</p>
          </section>
          <section className="panel">
            <h2>فعالیت‌های کلاس</h2>
            {activity?.items.length === 0 ? <p>فعالیت ثبت نشده است.</p> : null}
            {activity?.items.map((item) => (
              <div key={`${item.source_type}-${item.source_id}`} className="assessor-class-activity">
                <strong>{item.source_type}</strong>
                <span dir="ltr">{item.person_id} · {item.source_id}</span>
                <span>{item.state ?? "وضعیت ثبت نشده"}</span>
              </div>
            ))}
            {activity?.is_truncated ? <p className="muted">نمایش به جدیدترین فعالیت‌های صفحه محدود شده است.</p> : null}
          </section>
          <section className="panel">
            <h2>کارنامه کیفی فراگیر</h2>
            {learners.length > 0 ? (
              <div className="form-stack">
                <label htmlFor="assessor-class-person">فراگیر کلاس</label>
                <select id="assessor-class-person" value={personId ?? ""}
                  onChange={(e) => onPersonChange(e.target.value)}>
                  {learners.map((item) => (
                    <option key={item.person_id} value={item.person_id}>{item.person_id}</option>
                  ))}
                </select>
              </div>
            ) : <p>فراگیری برای کارنامه در دسترس نیست.</p>}
            {validReport ? report.subjects.map((subject) => (
              <article className="assessor-class-report" key={subject.capability_version_id}>
                <h3>{subject.capability_name ?? "عنوان درس در دسترس نیست"}</h3>
                <p>آموزش: {learningText(subject.learning_state)}</p>
                <p>اثبات رسمی مستقل: {subject.proof_state ?? "داده معتبر مستقل موجود نیست"}</p>
                <p>Claim بازبینی‌شده انسانی: {subject.reviewed_claim?.claim_state ?? "در دسترس نیست"}</p>
                <p>تمرکز بعدی: {subject.next_learning_focus ?? "هنوز توسط مدرس تصویب نشده"}</p>
                <p>منابع آموزشی: {subject.learning_sources.length}</p>
                <h4>بازخورد آموزشی ثبت‌شده</h4>
                {subject.feedback_sources.map((feedback) => (
                  <p key={feedback.source_id}>{feedback.feedback_text}</p>
                ))}
              </article>
            )) : null}
            {validReport && report.subjects.length === 0 ? <p>درس قابل‌نمایشی ثبت نشده است.</p> : null}
          </section>
        </>
      ) : null}
    </main>
  );
}

export function AssessorClassWorkspace({
  accessToken, organizationId, personId,
}: {
  accessToken: string;
  organizationId: string;
  personId: string;
}) {
  const api = makeApi(accessToken);
  const [offset, setOffset] = useState(0);
  const [chosenClass, setChosenClass] = useState<string>();
  const [chosenSession, setChosenSession] = useState<string>();
  const [chosenLearner, setChosenLearner] = useState<string>();

  const assigned = useQuery({
    queryKey: ["assessor-live-classes", organizationId, personId, offset],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/me/academy/assessor-classes", {
        params: { query: { offset, limit: PAGE_SIZE } },
      });
      if (error || !data) throw new Error("بررسی مأموریت‌های زنده ناموفق بود.");
      return data as AssignedAssessorClassPage;
    },
    retry: false,
    staleTime: 0,
    refetchInterval: READ_REFRESH_MS,
    refetchOnWindowFocus: true,
  });
  const validPage = assigned.isSuccess && !assigned.isFetching && !assigned.isError &&
    assigned.data.items.every((item) => Boolean(
      item.class_offering_id && item.cohort_id && item.grant_id
    )) ? assigned.data : undefined;
  const selected = validPage?.items.find((item) => item.class_offering_id === chosenClass)
    ?? validPage?.items[0];
  const classId = selected?.class_offering_id;
  const roster = useQuery({
    queryKey: ["assessor-class-roster", organizationId, personId, classId],
    enabled: Boolean(classId && validPage),
    retry: false,
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/class-offerings/{class_offering_id}/roster", {
        params: { path: { class_offering_id: classId ?? "" } },
      });
      if (error || !data) throw new Error("مجوز مشاهده افراد کلاس معتبر نیست.");
      return data as InstructorRoster;
    },
    refetchInterval: READ_REFRESH_MS,
    refetchOnWindowFocus: true,
  });
  const sessions = useQuery({
    queryKey: ["assessor-class-sessions", organizationId, personId, classId],
    enabled: Boolean(classId && validPage),
    retry: false,
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/class-offerings/{class_offering_id}/sessions", {
        params: { path: { class_offering_id: classId ?? "" } },
      });
      if (error || !data) throw new Error("جلسات کلاس مجاز در دسترس نیست.");
      return data as InstructorSession[];
    },
    refetchInterval: READ_REFRESH_MS,
  });
  const validatedSessions = sessions.data?.every((s) => s.class_offering_id === classId)
    ? sessions.data : undefined;
  const sessionId = validatedSessions?.some((x) => x.session_id === chosenSession)
    ? chosenSession : validatedSessions?.[0]?.session_id;
  const attendance = useQuery({
    queryKey: ["assessor-class-attendance", organizationId, personId, classId, sessionId],
    enabled: Boolean(classId && validPage && sessionId),
    retry: false,
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/sessions/{session_id}/attendance", {
        params: { path: { session_id: sessionId ?? "" } },
      });
      if (error || !data) throw new Error("اطلاعات حضور این جلسه در دسترس نیست.");
      return data as InstructorAttendance;
    },
    refetchInterval: READ_REFRESH_MS,
  });
  const activity = useQuery({
    queryKey: ["assessor-class-activity", organizationId, personId, classId],
    enabled: Boolean(classId && validPage),
    retry: false,
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/class-offerings/{class_offering_id}/activity", {
        params: { path: { class_offering_id: classId ?? "" }, query: { limit: 50 } },
      });
      if (error || !data) throw new Error("فعالیت‌های کلاس در دسترس نیست.");
      return data as InstructorClassActivity;
    },
    refetchInterval: READ_REFRESH_MS,
  });
  const validRoster = roster.data?.class_offering_id === classId &&
    roster.data?.cohort_id === selected?.cohort_id ? roster.data : undefined;
  const learners = validRoster?.members.filter((x) => x.member_type === "CANDIDATE") ?? [];
  const person = learners.some((x) => x.person_id === chosenLearner)
    ? chosenLearner : learners[0]?.person_id;
  const report = useQuery({
    queryKey: ["assessor-class-report", organizationId, personId, classId, person],
    enabled: Boolean(classId && validPage && person),
    retry: false,
    queryFn: async () => {
      const { data, error } = await api.GET(
        "/api/v1/class-offerings/{class_offering_id}/report-cards/{person_id}", {
          params: { path: { class_offering_id: classId ?? "", person_id: person ?? "" } },
        },
      );
      if (error || !data) throw new Error("کارنامه کیفی این فراگیر در دسترس نیست.");
      return data as CandidateClassReport;
    },
    refetchInterval: READ_REFRESH_MS,
  });
  const reads = [roster, sessions, attendance, activity, report];
  const busy = assigned.isPending || assigned.isFetching ||
    (Boolean(classId) && reads.some((query) => query.isFetching ||
      (query.isPending && query.fetchStatus === "fetching")));
  const errors = [assigned, ...reads].filter((query) => query.isError)
    .map((query) => query.error?.message ?? "دسترسی به کلاس نامعتبر است.");
  const mismatch = (roster.data && !validRoster) ||
    (sessions.data && !validatedSessions) ||
    (attendance.data && attendance.data.session_id !== sessionId) ||
    (activity.data && activity.data.class_offering_id !== classId) ||
    (report.data && (report.data.class_offering_id !== classId ||
      report.data.cohort_id !== selected?.cohort_id || report.data.person_id !== person));
  return (
    <AssessorClassView
      classes={validPage ?? { items: [], next_offset: null }}
      classId={classId}
      onClassChange={(id) => { setChosenClass(id); setChosenSession(undefined); setChosenLearner(undefined); }}
      pageOffset={offset}
      onPageOffset={(value) => {
        setOffset(value); setChosenClass(undefined); setChosenSession(undefined);
        setChosenLearner(undefined);
      }}
      roster={validRoster}
      sessions={validatedSessions}
      sessionId={sessionId}
      onSessionChange={setChosenSession}
      attendance={attendance.data?.session_id === sessionId ? attendance.data : undefined}
      activity={activity.data?.class_offering_id === classId ? activity.data : undefined}
      personId={person}
      onPersonChange={setChosenLearner}
      report={report.data?.class_offering_id === classId && report.data?.person_id === person
        ? report.data : undefined}
      loading={busy && !assigned.isError}
      error={mismatch ? "عدم تطبیق داده با محدوده مأموریت ارزیاب." : errors[0]}
    />
  );
}
