import type { InstructorHomeResponse } from "../api/client";

export function InstructorHome({ data }: { data: InstructorHomeResponse }) {
  return (
    <main className="page-shell">
      <section className="hero-card">
        <div>
          <p className="eyebrow">فضای مدرس</p>
          <h1>{data.assigned_cohort?.name ?? "کلاس‌های من"}</h1>
          <p className="muted">{data.current_wave?.name ?? "—"}</p>
        </div>
        <div className="metric">
          <strong>{data.candidate_count ?? 0}</strong>
          <span>فراگیر</span>
        </div>
      </section>

      <section className="grid-two">
        <article className="panel">
          <p className="eyebrow">کلاس‌ها</p>
          <h2>کلاس‌های واگذارشده</h2>
          <div className="stack">
            {(data.assigned_classes ?? []).map((item) => (
              <div className="proof-row" key={item.id}>
                <span>{item.title}</span>
                <span className="state">فعال</span>
              </div>
            ))}
          </div>
        </article>

        <article className="panel">
          <p className="eyebrow">تمرکز آموزشی</p>
          <h2>{data.capability_focus ?? "—"}</h2>
          <p className="muted">
            بازخورد مدرس به یادگیری کمک می‌کند، اما به‌تنهایی Capability را Proven نمی‌کند.
          </p>
        </article>
      </section>
    </main>
  );
}
