import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { makeApi } from "../api/client";
import type {
  InstructorAttendance,
  InstructorClassActivity,
  InstructorRoster,
  InstructorSession,
} from "./InstructorClassWorkspace";
import type { CandidateClassReport } from "./CandidateReportWorkspace";

export type AdminCohort = {
  cohort_id: string;
  code: string;
  name: string;
  track_code: string;
  status: string;
};
export type AdminClass = {
  class_offering_id: string;
  cohort_id: string;
  title: string;
  primary_capability_version_id: string;
  status: string;
};
export type AdminCohortPage = {
  items: AdminCohort[];
  next_offset: number | null;
};
export type AdminClassPage = {
  cohort_id: string;
  items: AdminClass[];
  next_offset: number | null;
};

const PAGE_SIZE = 50;
type AttendanceState = "PRESENT" | "ABSENT";

function attendanceLabel(value: string | undefined) {
  if (value === "PRESENT") return "حاضر";
  if (value === "ABSENT") return "غایب (ثبت‌شده)";
  if (value === undefined) return "ثبت نشده؛ غیبت محسوب نمی‌شود";
  return "وضعیت نامعتبر؛ بررسی لازم است";
}
function learningLabel(value: string | null) {
  if (value === "TO_LEARN") return "هنوز شروع نشده";
  if (value === "IN_LEARNING") return "در حال یادگیری";
  if (value === "LEARNING_COMPLETED") return "الزامات آموزشی تکمیل شده";
  return "نامشخص";
}

export function AdminAcademyOperationsView({
  cohorts,
  cohortId,
  onCohortChange,
  cohortOffset,
  onCohortOffset,
  classes,
  classId,
  onClassChange,
  classOffset,
  onClassOffset,
  roster,
  sessions,
  sessionId,
  onSessionChange,
  attendance,
  activity,
  selectedPersonId,
  onPersonChange,
  report,
  onRecordAttendance,
  pendingPersonId,
  loading = false,
  errors = [],
}: {
  cohorts?: AdminCohortPage;
  cohortId?: string;
  onCohortChange: (value: string) => void;
  cohortOffset: number;
  onCohortOffset: (value: number) => void;
  classes?: AdminClassPage;
  classId?: string;
  onClassChange: (value: string) => void;
  classOffset: number;
  onClassOffset: (value: number) => void;
  roster?: InstructorRoster;
  sessions?: InstructorSession[];
  sessionId?: string;
  onSessionChange: (value: string) => void;
  attendance?: InstructorAttendance;
  activity?: InstructorClassActivity;
  selectedPersonId?: string;
  onPersonChange: (value: string) => void;
  report?: CandidateClassReport;
  onRecordAttendance: (personId: string, status: AttendanceState) => void;
  pendingPersonId?: string;
  loading?: boolean;
  errors?: string[];
}) {
  const learners = (roster?.members ?? []).filter((m) => m.member_type === "CANDIDATE");
  const attendanceByPerson = new Map(attendance?.items.map((item) => [item.person_id, item]) ?? []);
  const showDetails = Boolean(classId && roster && sessions && activity) && errors.length === 0 && !loading;

  return (
    <main className="page-shell" data-testid="admin-academy-operations">
      <section className="panel">
        <p className="eyebrow">ACADEMY OPERATIONS</p>
        <h2>مدیریت عملیاتی آکادمی</h2>
        <p className="muted">
          داده‌ها از کلاس، عضویت، جلسه و فعالیت ثبت‌شده خوانده می‌شوند. مدیریت Mission
          در فضای طراحی مأموریت و بررسی رسمی Evidence و Gate در مسیرهای مجاز خود باقی می‌مانند.
        </p>
        {loading ? <p role="status">در حال دریافت اطلاعات عملیاتی...</p> : null}
        {errors.map((error, index) => <p role="alert" className="error" key={index}>{error}</p>)}
        {cohorts && cohorts.items.length === 0 ? (
          <p className="muted">در این صفحه از سازمان، گروه آموزشی ثبت نشده است.</p>
        ) : null}
        {cohorts?.items.length ? (
          <div className="form-stack">
            <label htmlFor="admin-ops-cohort">گروه آموزشی سازمان</label>
            <select
              id="admin-ops-cohort"
              value={cohortId ?? ""}
              onChange={(e) => onCohortChange(e.target.value)}
            >
              {cohorts.items.map((item) => (
                <option key={item.cohort_id} value={item.cohort_id}>
                  {item.name} · {item.code} · {item.status}
                </option>
              ))}
            </select>
            <div className="action-row">
              <button type="button" className="ghost" disabled={cohortOffset === 0}
                onClick={() => onCohortOffset(Math.max(0, cohortOffset - PAGE_SIZE))}>
                گروه‌های قبلی
              </button>
              {cohorts.next_offset !== null ? (
                <button type="button" className="ghost"
                  onClick={() => onCohortOffset(cohorts.next_offset!)}>
                  گروه‌های بعدی
                </button>
              ) : null}
            </div>
          </div>
        ) : null}
        {cohortId && classes?.items.length === 0 ? (
          <p className="muted">در این صفحه از گروه، کلاسی ثبت نشده است.</p>
        ) : null}
        {classes?.items.length ? (
          <div className="form-stack">
            <label htmlFor="admin-ops-class">کلاس واقعی</label>
            <select
              id="admin-ops-class"
              value={classId ?? ""}
              onChange={(e) => onClassChange(e.target.value)}
            >
              {classes.items.map((item) => (
                <option value={item.class_offering_id} key={item.class_offering_id}>
                  {item.title} · {item.status}
                </option>
              ))}
            </select>
            <div className="action-row">
              <button type="button" className="ghost" disabled={classOffset === 0}
                onClick={() => onClassOffset(Math.max(0, classOffset - PAGE_SIZE))}>
                کلاس‌های قبلی
              </button>
              {classes.next_offset !== null ? (
                <button type="button" className="ghost"
                  onClick={() => onClassOffset(classes.next_offset!)}>
                  کلاس‌های بعدی
                </button>
              ) : null}
            </div>
          </div>
        ) : null}
      </section>

      {showDetails ? (
        <>
          <section className="panel">
            <h2>افراد کلاس</h2>
            <p className="muted">شناسه‌ها از عضویت واقعی Cohort خوانده می‌شوند.</p>
            {learners.length === 0 ? <p className="muted">فراگیری ثبت نشده است.</p> : null}
            {learners.map((learner) => (
              <div className="admin-ops-person-row" key={learner.person_id}>
                <span dir="ltr">{learner.person_id}</span>
                <span className="state">فراگیر</span>
              </div>
            ))}
            <p className="muted">مدرسان تخصیص‌یافته: {roster?.instructor_person_ids.join("، ") || "ثبت نشده"}</p>
          </section>
          <section className="panel">
            <h2>جلسات و حضور و غیاب</h2>
            {sessions?.length ? (
              <div className="form-stack">
                <label htmlFor="admin-ops-session">جلسه کلاس</label>
                <select
                  id="admin-ops-session"
                  value={sessionId ?? ""}
                  onChange={(e) => onSessionChange(e.target.value)}
                >
                  {sessions.map((item) => (
                    <option key={item.session_id} value={item.session_id}>{item.title}</option>
                  ))}
                </select>
              </div>
            ) : <p className="muted">جلسه‌ای ثبت نشده است.</p>}
            {sessionId && attendance && attendance.session_id === sessionId
              ? learners.map((learner) => {
                  const record = attendanceByPerson.get(learner.person_id);
                  return (
                    <div className="admin-ops-attendance-row" key={learner.person_id}>
                      <span dir="ltr">{learner.person_id}</span>
                      <span>{attendanceLabel(record?.status)}</span>
                      <button type="button" disabled={Boolean(pendingPersonId) || record?.status === "PRESENT"}
                        onClick={() => onRecordAttendance(learner.person_id, "PRESENT")}>
                        ثبت حاضر
                      </button>
                      <button type="button" disabled={Boolean(pendingPersonId) || record?.status === "ABSENT"}
                        onClick={() => onRecordAttendance(learner.person_id, "ABSENT")}>
                        ثبت غایب
                      </button>
                    </div>
                  );
                })
              : null}
            <p className="muted">
              ثبت یا اصلاح حضور صرفاً با اقدام صریح مدیر، نسخه فعلی و کلید درخواست مستقل انجام می‌شود.
              نبود ثبت، غیبت نیست.
            </p>
          </section>
          <section className="panel">
            <h2>فعالیت‌های اخیر همان کلاس</h2>
            {(activity?.items ?? []).length === 0 ? <p className="muted">فعالیتی ثبت نشده است.</p> : null}
            {activity?.items.map((item) => (
              <div className="admin-ops-activity-row" key={`${item.source_type}-${item.source_id}`}>
                <strong>{item.source_type}</strong>
                <p dir="ltr" className="muted">{item.person_id} · {item.source_id}</p>
                <p>{item.state ?? "وضعیت ثبت نشده"}</p>
              </div>
            ))}
            {activity?.is_truncated ? <p className="muted">فقط تازه‌ترین رکوردهای این صفحه نمایش داده شده‌اند.</p> : null}
          </section>
          <section className="panel">
            <h2>کارنامه کیفی</h2>
            {learners.length ? (
              <div className="form-stack">
                <label htmlFor="admin-ops-person">فراگیر برای کارنامه</label>
                <select
                  id="admin-ops-person"
                  value={selectedPersonId ?? ""}
                  onChange={(e) => onPersonChange(e.target.value)}
                >
                  {learners.map((item) => (
                    <option key={item.person_id} value={item.person_id}>{item.person_id}</option>
                  ))}
                </select>
              </div>
            ) : <p className="muted">فراگیری برای انتخاب وجود ندارد.</p>}
            {report?.subjects.map((subject) => (
              <article className="admin-ops-report-row" key={subject.capability_version_id}>
                <h3>{subject.capability_name ?? "عنوان درس در دسترس نیست"}</h3>
                <p>آموزش: {learningLabel(subject.learning_state)}</p>
                <p>ProofState مستقل: {subject.proof_state ?? "نامشخص"}</p>
                <p>Claim بازبینی‌شده انسانی: {subject.reviewed_claim?.claim_state ?? "در دسترس نیست"}</p>
                <p>منابع فعالیت: {subject.learning_sources.length} · منابع بازخورد: {subject.feedback_sources.length}</p>
              </article>
            ))}
            {report && report.subjects.length === 0 ? (
              <p className="muted">درس قابل‌نمایشی ثبت نشده است.</p>
            ) : null}
          </section>
        </>
      ) : null}
    </main>
  );
}

export function AdminAcademyOperationsWorkspace({
  accessToken,
  organizationId,
  personId,
}: {
  accessToken: string;
  organizationId: string;
  personId: string;
}) {
  const api = makeApi(accessToken);
  const queryClient = useQueryClient();
  const [cohortOffset, setCohortOffset] = useState(0);
  const [classOffset, setClassOffset] = useState(0);
  const [chosenCohortId, setChosenCohortId] = useState<string>();
  const [chosenClassId, setChosenClassId] = useState<string>();
  const [chosenSessionId, setChosenSessionId] = useState<string>();
  const [chosenPersonId, setChosenPersonId] = useState<string>();
  const cohorts = useQuery({
    queryKey: ["admin-academy-cohorts", organizationId, personId, cohortOffset],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/admin/academy/cohorts", {
        params: { query: { limit: PAGE_SIZE, offset: cohortOffset } },
      });
      if (error || !data) throw new Error("دریافت گروه‌های سازمان ناموفق بود.");
      return data as AdminCohortPage;
    },
  });
  const cohortId = cohorts.data?.items.some((item) => item.cohort_id === chosenCohortId)
    ? chosenCohortId : cohorts.data?.items[0]?.cohort_id;
  const classes = useQuery({
    queryKey: ["admin-academy-classes", organizationId, personId, cohortId, classOffset],
    enabled: Boolean(cohortId),
    queryFn: async () => {
      const { data, error } = await api.GET(
        "/api/v1/admin/academy/cohorts/{cohort_id}/classes", {
          params: {
            path: { cohort_id: cohortId ?? "" },
            query: { limit: PAGE_SIZE, offset: classOffset },
          },
        },
      );
      if (error || !data) throw new Error("دریافت کلاس‌های گروه ناموفق بود.");
      return data as AdminClassPage;
    },
  });
  const verifiedClassPage = classes.data?.cohort_id === cohortId
    ? classes.data : undefined;
  const classId = verifiedClassPage?.items.some((item) => item.class_offering_id === chosenClassId)
    ? chosenClassId : verifiedClassPage?.items[0]?.class_offering_id;
  const roster = useQuery({
    queryKey: ["admin-academy-roster", organizationId, personId, classId],
    enabled: Boolean(classId),
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/class-offerings/{class_offering_id}/roster", {
        params: { path: { class_offering_id: classId ?? "" } },
      });
      if (error || !data) throw new Error("دریافت افراد کلاس ناموفق بود.");
      return data as InstructorRoster;
    },
  });
  const sessions = useQuery({
    queryKey: ["admin-academy-sessions", organizationId, personId, classId],
    enabled: Boolean(classId),
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/class-offerings/{class_offering_id}/sessions", {
        params: { path: { class_offering_id: classId ?? "" } },
      });
      if (error || !data) throw new Error("دریافت جلسات کلاس ناموفق بود.");
      return data as InstructorSession[];
    },
  });
  const verifiedSessions = sessions.data?.every((item) => item.class_offering_id === classId)
    ? sessions.data : undefined;
  const sessionId = verifiedSessions?.some((item) => item.session_id === chosenSessionId)
    ? chosenSessionId : verifiedSessions?.[0]?.session_id;
  const attendance = useQuery({
    queryKey: ["admin-academy-attendance", organizationId, personId, classId, sessionId],
    enabled: Boolean(classId && sessionId),
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/sessions/{session_id}/attendance", {
        params: { path: { session_id: sessionId ?? "" } },
      });
      if (error || !data) throw new Error("دریافت حضور کلاس ناموفق بود.");
      return data as InstructorAttendance;
    },
  });
  const activity = useQuery({
    queryKey: ["admin-academy-activity", organizationId, personId, classId],
    enabled: Boolean(classId),
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/class-offerings/{class_offering_id}/activity", {
        params: { path: { class_offering_id: classId ?? "" }, query: { limit: 50 } },
      });
      if (error || !data) throw new Error("دریافت فعالیت کلاس ناموفق بود.");
      return data as InstructorClassActivity;
    },
  });
  const verifiedRoster =
    roster.data?.class_offering_id === classId && roster.data?.cohort_id === cohortId
      ? roster.data : undefined;
  const learners = (verifiedRoster?.members ?? []).filter(
    (x) => x.member_type === "CANDIDATE",
  );
  const selectedPersonId = learners.some((x) => x.person_id === chosenPersonId)
    ? chosenPersonId : learners[0]?.person_id;
  const report = useQuery({
    queryKey: ["admin-academy-report", organizationId, personId, classId, selectedPersonId],
    enabled: Boolean(classId && selectedPersonId),
    queryFn: async () => {
      const { data, error } = await api.GET(
        "/api/v1/class-offerings/{class_offering_id}/report-cards/{person_id}", {
          params: { path: { class_offering_id: classId ?? "", person_id: selectedPersonId ?? "" } },
        },
      );
      if (error || !data) throw new Error("دریافت کارنامه کیفی ناموفق بود.");
      return data as CandidateClassReport;
    },
  });
  const saveAttendance = useMutation({
    mutationFn: async ({ learnerId, status }: { learnerId: string; status: AttendanceState }) => {
      if (!sessionId || !classId || !attendance.data || attendance.data.session_id !== sessionId) {
        throw new Error("نسخه حضور و غیاب معتبر نیست؛ داده را تازه‌سازی کنید.");
      }
      if (!learners.some((x) => x.person_id === learnerId)) {
        throw new Error("فراگیر به کلاس جاری تعلق ندارد.");
      }
      const current = attendance.data.items.find((item) => item.person_id === learnerId);
      const { data, error } = await api.POST(
        "/api/v1/sessions/{session_id}/attendance/{person_id}", {
          params: { path: { session_id: sessionId, person_id: learnerId } },
          body: {
            status,
            expected_version: current?.version ?? 0,
            idempotency_key: crypto.randomUUID(),
          },
        },
      );
      if (error || !data) throw new Error("ثبت حضور ناموفق بود؛ نسخه را بررسی و دوباره بارگذاری کنید.");
      return data;
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["admin-academy-attendance", organizationId, personId] }),
        queryClient.invalidateQueries({ queryKey: ["admin-academy-activity", organizationId, personId] }),
        queryClient.invalidateQueries({ queryKey: ["admin-academy-report", organizationId, personId] }),
      ]);
    },
  });
  const errors = [cohorts, classes, roster, sessions, attendance, activity, report]
    .filter((query) => query.isError)
    .map((query) => query.error?.message ?? "دریافت اطلاعات ناموفق بود.");
  if (classes.data && classes.data.cohort_id !== cohortId) {
    errors.push("شناسه گروه فهرست کلاس‌ها تطبیق ندارد.");
  }
  if (roster.data && !verifiedRoster) {
    errors.push("فهرست افراد با کلاس و گروه انتخاب‌شده تطبیق ندارد.");
  }
  if (sessions.data && !verifiedSessions) {
    errors.push("جلسات با کلاس انتخاب‌شده تطبیق ندارند.");
  }
  if (report.data && (
    report.data.class_offering_id !== classId ||
    report.data.cohort_id !== cohortId ||
    report.data.person_id !== selectedPersonId
  )) {
    errors.push("کارنامه با کلاس یا فراگیر انتخاب‌شده تطبیق ندارد.");
  }
  if (saveAttendance.isError) {
    errors.push(saveAttendance.error.message);
  }
  const loading = [cohorts, classes, roster, sessions, attendance, activity, report].some(
    (query) => query.isPending && query.fetchStatus === "fetching",
  );
  const changeCohort = (value: string) => {
    setChosenCohortId(value);
    setChosenClassId(undefined);
    setChosenSessionId(undefined);
    setChosenPersonId(undefined);
    setClassOffset(0);
  };
  const changeCohortOffset = (value: number) => {
    setCohortOffset(value);
    changeCohort("");
  };
  const changeClassOffset = (value: number) => {
    setClassOffset(value);
    setChosenClassId(undefined);
    setChosenSessionId(undefined);
    setChosenPersonId(undefined);
  };
  const changeClass = (value: string) => {
    setChosenClassId(value);
    setChosenSessionId(undefined);
    setChosenPersonId(undefined);
  };
  return (
    <AdminAcademyOperationsView
      cohorts={cohorts.data}
      cohortId={cohortId}
      onCohortChange={changeCohort}
      cohortOffset={cohortOffset}
      onCohortOffset={changeCohortOffset}
      classes={verifiedClassPage}
      classId={classId}
      onClassChange={changeClass}
      classOffset={classOffset}
      onClassOffset={changeClassOffset}
      roster={verifiedRoster}
      sessions={verifiedSessions}
      sessionId={sessionId}
      onSessionChange={setChosenSessionId}
      attendance={attendance.data?.session_id === sessionId ? attendance.data : undefined}
      activity={activity.data?.class_offering_id === classId ? activity.data : undefined}
      selectedPersonId={selectedPersonId}
      onPersonChange={setChosenPersonId}
      report={
        report.data?.class_offering_id === classId &&
        report.data?.cohort_id === cohortId &&
        report.data?.person_id === selectedPersonId
          ? report.data : undefined
      }
      onRecordAttendance={(learnerId, status) => {
        void saveAttendance.mutateAsync({ learnerId, status }).catch(() => {
          // The mutation error is shown by the workspace; never assume success.
        });
      }}
      pendingPersonId={saveAttendance.isPending ? saveAttendance.variables?.learnerId : undefined}
      loading={loading}
      errors={errors}
    />
  );
}
