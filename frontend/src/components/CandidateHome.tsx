import type { CandidateHomeResponse } from "../api/client";

function formatDate(value?: string) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("fa-IR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function CandidateHome({ data }: { data: CandidateHomeResponse }) {
  return (
    <main className="page-shell">
      <section className="hero-card">
        <div>
          <p className="eyebrow">مسیر رشد من</p>
          <h1>{data.cohort?.name ?? "آکادمی پرچم"}</h1>
          <p className="muted">
            {data.journey?.track ?? "—"} · {data.current_wave?.name ?? "—"}
          </p>
        </div>
        <span className="status-chip">{data.journey?.state ?? "—"}</span>
      </section>

      <section className="grid-two">
        <article className="panel">
          <p className="eyebrow">LEARN</p>
          <h2>الان چه چیزی باید یاد بگیرم؟</h2>
          <div className="stack">
            {(data.what_to_learn ?? []).map((item) => (
              <div className="task-card" key={item.capability_version_id}>
                <div>
                  <strong>{item.name}</strong>
                  <p>{item.next_session?.title ?? "جلسه بعدی هنوز زمان‌بندی نشده است."}</p>
                  <small>{formatDate(item.next_session?.starts_at)}</small>
                </div>
                <span className="state">{item.learning_state}</span>
              </div>
            ))}
          </div>
        </article>

        <article className="panel">
          <p className="eyebrow">PROVE</p>
          <h2>الان چه چیزی باید اثبات کنم؟</h2>
          <div className="stack">
            {(data.what_to_prove ?? []).map((item) => (
              <div className="proof-row" key={item.capability_version_id}>
                <span>{item.name}</span>
                <span className="state state-muted">{item.proof_state}</span>
              </div>
            ))}
          </div>
        </article>
      </section>

      <section className="panel">
        <div className="section-title">
          <div>
            <p className="eyebrow">تقویم</p>
            <h2>جلسه‌های پیش‌رو</h2>
          </div>
          <span className="count">{data.upcoming_sessions?.length ?? 0}</span>
        </div>
        <div className="stack">
          {(data.upcoming_sessions ?? []).map((session) => (
            <div className="session-row" key={session.session_id}>
              <strong>{session.title}</strong>
              <span>{formatDate(session.starts_at)}</span>
              <span className="mode">{session.delivery_mode}</span>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
