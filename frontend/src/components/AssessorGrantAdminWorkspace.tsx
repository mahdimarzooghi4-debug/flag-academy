import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { makeApi } from "../api/client";

export type AssessorClassGrant = {
  grant_id: string;
  version: number;
  organization_context_id: string;
  class_offering_id: string;
  assessor_person_id: string;
  starts_at: string;
  ends_at: string;
  revoked_at: string | null;
};
export type AssessorGrantPage = {
  items: AssessorClassGrant[];
  next_offset: number | null;
};
const LIMIT = 50;
const UUID_RE = /^[a-f\d]{8}-[a-f\d]{4}-[a-f\d]{4}-[a-f\d]{4}-[a-f\d]{12}$/i;

export function explicitUtcInstant(value: string): string {
  // No implicit timezone: a grant is an explicit human authorization window.
  if (!/^\d{4}-\d\d-\d\dT\d\d:\d\d(?::\d\d(?:\.\d+)?)?(?:Z|[+-]\d\d:\d\d)$/i.test(value.trim())) {
    throw new Error("تاریخ باید با منطقه زمانی صریح وارد شود؛ مثال: 2026-10-09T10:00:00Z");
  }
  const time = new Date(value.trim());
  if (Number.isNaN(time.getTime())) {
    throw new Error("تاریخ یا ساعت معتبر نیست.");
  }
  return time.toISOString();
}

export function AssessorGrantAdminView({
  classId, grants, offset, onOffset, onCreate, onExtend, onRevoke, busy = false, error,
}: {
  classId: string;
  grants?: AssessorGrantPage;
  offset: number;
  onOffset: (offset: number) => void;
  onCreate: (assessorId: string, start: string, end: string) => void;
  onExtend: (grant: AssessorClassGrant, end: string, reason: string) => void;
  onRevoke: (grant: AssessorClassGrant, reason: string) => void;
  busy?: boolean;
  error?: string;
}) {
  const [assessorId, setAssessorId] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [selectedId, setSelectedId] = useState("");
  const [newEnd, setNewEnd] = useState("");
  const [reason, setReason] = useState("");
  const [confirmRevocation, setConfirmRevocation] = useState(false);
  const [validationError, setValidationError] = useState<string>();
  const selected = grants?.items.find((item) => item.grant_id === selectedId)
    ?? grants?.items[0];

  const create = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    try {
      if (!UUID_RE.test(assessorId.trim())) throw new Error("شناسه ارزیاب باید UUID معتبر باشد.");
      const s = explicitUtcInstant(start);
      const e = explicitUtcInstant(end);
      if (new Date(e) <= new Date(s)) throw new Error("پایان مأموریت باید بعد از شروع آن باشد.");
      setValidationError(undefined);
      onCreate(assessorId.trim(), s, e);
    } catch (err) {
      setValidationError(err instanceof Error ? err.message : "ورودی نامعتبر است.");
    }
  };
  const extend = () => {
    if (!selected) return;
    try {
      const e = explicitUtcInstant(newEnd);
      if (new Date(e) <= new Date(selected.ends_at)) throw new Error("تاریخ جدید باید بعد از پایان فعلی باشد.");
      if (!reason.trim()) throw new Error("دلیل تصمیم الزامی است.");
      setValidationError(undefined);
      onExtend(selected, e, reason.trim());
    } catch (err) {
      setValidationError(err instanceof Error ? err.message : "ورودی نامعتبر است.");
    }
  };
  const revoke = () => {
    if (!selected) return;
    if (!confirmRevocation || !reason.trim()) {
      setValidationError("برای لغو، دلیل و تأیید صریح لازم است.");
      return;
    }
    setValidationError(undefined);
    onRevoke(selected, reason.trim());
    setConfirmRevocation(false);
  };

  return (
    <section className="panel" data-testid="admin-assessor-grants">
      <h2>انتصاب و مأموریت ارزیاب کلاس</h2>
      <p className="muted">دسترسی ارزیاب فقط برای همین کلاس و در بازه زمانی معتبر است. نقش ASSESSOR به‌تنهایی مجوز کلاس نیست.</p>
      <p dir="ltr" className="muted">ClassOffering: {classId}</p>
      {error ? <p role="alert" className="error">{error}</p> : null}
      {validationError ? <p role="alert" className="error">{validationError}</p> : null}
      <form className="form-stack" onSubmit={create}>
        <h3>انتصاب جدید</h3>
        <label htmlFor="assessor-grant-person">شناسه ارزیاب عضو همین سازمان</label>
        <input id="assessor-grant-person" value={assessorId}
          onChange={(e) => setAssessorId(e.target.value)} required
          placeholder="UUID ارزیاب با نقش ASSESSOR" />
        <label htmlFor="assessor-grant-start">آغاز مأموریت (ISO با منطقه زمانی)</label>
        <input id="assessor-grant-start" value={start} onChange={(e) => setStart(e.target.value)}
          required placeholder="2026-10-09T10:00:00Z" />
        <label htmlFor="assessor-grant-end">پایان مأموریت (ISO با منطقه زمانی)</label>
        <input id="assessor-grant-end" value={end} onChange={(e) => setEnd(e.target.value)}
          required placeholder="2026-10-10T10:00:00Z" />
        <button type="submit" disabled={busy}>ثبت انتصاب با تأیید مدیر</button>
      </form>
      <h3>مأموریت‌های ثبت‌شده همین کلاس</h3>
      {grants?.items.length === 0 ? <p className="muted">مأموریتی برای این کلاس ثبت نشده است.</p> : null}
      {grants?.items.length ? (
        <>
          <label htmlFor="assessor-grant-select">مأموریت برای بررسی</label>
          <select id="assessor-grant-select" value={selected?.grant_id ?? ""}
            onChange={(e) => { setSelectedId(e.target.value); setNewEnd(""); setReason(""); setConfirmRevocation(false); }}>
            {grants.items.map((item) => (
              <option value={item.grant_id} key={item.grant_id}>{item.assessor_person_id} · نسخه {item.version}</option>
            ))}
          </select>
          {selected ? (
            <div className="form-stack" data-testid="selected-assessor-grant">
              <p>شناسه ارزیاب: <span dir="ltr">{selected.assessor_person_id}</span></p>
              <p>نسخه: {selected.version}</p>
              <p>شروع: {selected.starts_at}</p>
              <p>پایان: {selected.ends_at}</p>
              <p>لغو: {selected.revoked_at ?? "لغو نشده"}</p>
              {selected.revoked_at === null ? (
                <>
                  <label htmlFor="assessor-grant-reason">دلیل تمدید یا لغو</label>
                  <textarea id="assessor-grant-reason" value={reason}
                    onChange={(e) => setReason(e.target.value)} />
                  <label htmlFor="assessor-grant-extend-end">تاریخ پایان جدید (ISO با منطقه زمانی)</label>
                  <input id="assessor-grant-extend-end" value={newEnd}
                    onChange={(e) => setNewEnd(e.target.value)} />
                  <button type="button" disabled={busy || !reason.trim()} onClick={extend}>تمدید مأموریت</button>
                  <label>
                    <input type="checkbox" checked={confirmRevocation}
                      onChange={(e) => setConfirmRevocation(e.target.checked)} />
                    لغو مأموریت این ارزیاب در همین کلاس را تأیید می‌کنم.
                  </label>
                  <button type="button" disabled={busy || !reason.trim() || !confirmRevocation}
                    onClick={revoke}>لغو مأموریت</button>
                </>
              ) : <p className="muted">مأموریت لغوشده قابل تمدید نیست.</p>}
            </div>
          ) : null}
        </>
      ) : null}
      <div className="action-row">
        <button type="button" className="ghost" disabled={busy || offset === 0}
          onClick={() => onOffset(Math.max(0, offset - LIMIT))}>صفحه قبل مأموریت‌ها</button>
        {grants?.next_offset !== null && grants?.next_offset !== undefined ? (
          <button type="button" className="ghost" disabled={busy}
            onClick={() => onOffset(grants.next_offset!)}>صفحه بعد مأموریت‌ها</button>
        ) : null}
      </div>
    </section>
  );
}

export function AssessorGrantAdminWorkspace({
  accessToken, organizationId, personId, classId,
}: {
  accessToken: string;
  organizationId: string;
  personId: string;
  classId: string;
}) {
  const api = makeApi(accessToken);
  const client = useQueryClient();
  const [offset, setOffset] = useState(0);
  const queryKey = ["admin-assessor-class-grants", organizationId, personId, classId];
  const grants = useQuery({
    queryKey: [...queryKey, offset],
    queryFn: async () => {
      const { data, error } = await api.GET(
        "/api/v1/admin/academy/classes/{class_offering_id}/assessor-grants",
        { params: { path: { class_offering_id: classId }, query: { limit: LIMIT, offset } } },
      );
      if (error || !data) throw new Error("دریافت مأموریت‌های ارزیاب ناموفق بود.");
      const page = data as AssessorGrantPage;
      if (!Array.isArray(page.items) || page.items.some((item) =>
        item.organization_context_id !== organizationId || item.class_offering_id !== classId
      )) throw new Error("داده مأموریت با سازمان یا کلاس انتخاب‌شده تطبیق ندارد.");
      return page;
    },
  });
  const mutation = useMutation({
    mutationFn: async (command:
      | { kind: "CREATE"; assessorId: string; start: string; end: string }
      | { kind: "EXTEND"; grant: AssessorClassGrant; end: string; reason: string }
      | { kind: "REVOKE"; grant: AssessorClassGrant; reason: string }
    ) => {
      const source = command.kind === "CREATE" ? undefined : command.grant;
      if (source && (
        source.organization_context_id !== organizationId ||
        source.class_offering_id !== classId ||
        !grants.data?.items.some((x) => x.grant_id === source.grant_id && x.version === source.version)
      )) throw new Error("مأموریت یا نسخه آن متعلق به کلاس جاری نیست؛ دوباره بارگذاری کنید.");
      const key = crypto.randomUUID();
      const response = command.kind === "CREATE"
        ? await api.POST("/api/v1/admin/academy/classes/{class_offering_id}/assessor-grants", {
            params: { path: { class_offering_id: classId } },
            body: { assessor_person_id: command.assessorId, starts_at: command.start,
              ends_at: command.end, idempotency_key: key },
          })
        : command.kind === "EXTEND"
          ? await api.POST("/api/v1/admin/academy/assessor-grants/{grant_id}/extend", {
              params: { path: { grant_id: command.grant.grant_id } },
              body: { expected_version: command.grant.version, ends_at: command.end,
                reason: command.reason, idempotency_key: key },
            })
          : await api.POST("/api/v1/admin/academy/assessor-grants/{grant_id}/revoke", {
              params: { path: { grant_id: command.grant.grant_id } },
              body: { expected_version: command.grant.version,
                reason: command.reason, idempotency_key: key },
            });
      if (response.error || !response.data) throw new Error(
        "فرمان مأموریت پذیرفته نشد؛ مجوز، نسخه و وضعیت فعلی را دوباره بررسی کنید."
      );
      const result = response.data as AssessorClassGrant;
      if (result.class_offering_id !== classId || result.organization_context_id !== organizationId) {
        throw new Error("پاسخ مأموریت با کلاس یا سازمان جاری تطبیق ندارد.");
      }
      return result;
    },
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey });
    },
  });
  return (
    <AssessorGrantAdminView
      classId={classId}
      grants={grants.data}
      offset={offset}
      onOffset={setOffset}
      busy={mutation.isPending}
      error={grants.isError ? grants.error.message :
        mutation.isError ? mutation.error.message : undefined}
      onCreate={(assessorId, start, end) => mutation.mutate({ kind: "CREATE", assessorId, start, end })}
      onExtend={(grant, end, reason) => mutation.mutate({ kind: "EXTEND", grant, end, reason })}
      onRevoke={(grant, reason) => mutation.mutate({ kind: "REVOKE", grant, reason })}
    />
  );
}
