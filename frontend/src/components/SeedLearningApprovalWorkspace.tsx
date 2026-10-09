import { useEffect, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { makeApi } from "../api/client";

export type SeedLearningPreview = {
  seed_key: string;
  source_reference: string;
  source_version: string;
  source_payload_digest: string;
  record_count: number;
  dataset_name: string;
  purpose: string;
  source_policy_key: string;
  source_policy_version: string;
  source_type: string;
  data_classification: string;
  approved: boolean;
  approval_event_id: string | null;
  approved_by: string | null;
};

export type SeedLearningApprovalReceipt = {
  approval_event_id: string;
  source_payload_digest: string;
  record_count: number;
  dataset_name: string;
  purpose: string;
  source_reference: string;
  source_version: string;
  approval_reference: string;
  reviewer_id: string;
  created: boolean;
  dataset_creation_pending: boolean;
};

const SHA256 = /^[0-9a-f]{64}$/;
const SEED_KEY = "decision-making-v1";

/** Visible metadata is not proof that the reviewer inspected the actual file. */
export function SeedLearningApprovalView({
  preview,
  loading = false,
  busy = false,
  error,
  receipt,
  onApprove,
  onRefresh,
}: {
  preview?: SeedLearningPreview;
  loading?: boolean;
  busy?: boolean;
  error?: string;
  receipt?: SeedLearningApprovalReceipt;
  onApprove: (digest: string, approvalReference: string) => void;
  onRefresh: () => void;
}) {
  const [confirmedDigest, setConfirmedDigest] = useState("");
  const [reviewedFile, setReviewedFile] = useState(false);
  const [reference, setReference] = useState("");

  // A new preview or source version invalidates any prior human confirmation.
  useEffect(() => {
    setConfirmedDigest("");
    setReviewedFile(false);
    setReference("");
  }, [preview?.source_payload_digest, preview?.source_version]);

  const trustworthy =
    preview?.seed_key === SEED_KEY &&
    preview.source_reference === "docs/ai/seed/decision-making-v1.jsonl" &&
    SHA256.test(preview.source_payload_digest) &&
    preview.record_count > 0 &&
    preview.source_type === "CURATED_SYNTHETIC_SEED" &&
    preview.purpose === "MODEL_TRAINING";

  const ready = Boolean(
    trustworthy && !preview?.approved && !loading && !busy && !error &&
    reviewedFile &&
    confirmedDigest.trim() === preview?.source_payload_digest &&
    reference.trim().length > 0 && reference.trim().length <= 255,
  );

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!ready || !preview) return;
    onApprove(preview.source_payload_digest, reference.trim());
  };

  return (
    <section className="panel" data-testid="seed-learning-approval-workspace">
      <div className="section-title">
        <div>
          <p className="eyebrow">AI LEARNING GOVERNANCE</p>
          <h2>تأیید انسانی دیتای اولیه تصمیم‌گیری</h2>
        </div>
        <span className="state">SEED V1</span>
      </div>
      <p className="muted">
        فقط مدیر آکادمی می‌تواند پس از بررسی فایل ثابت Seed، مجوز استفاده از همان
        نسخه و همان SHA-256 را برای مسیر یادگیری ثبت کند. این فرمان آموزش مدل،
        ارزیابی، انتخاب مدل یا استقرار را آغاز نمی‌کند.
      </p>
      {loading ? <p role="status">در حال اعتبارسنجی نسخه رسمی Seed...</p> : null}
      {error ? <p role="alert" className="error">{error}</p> : null}
      {!loading && preview && !trustworthy ? (
        <p role="alert" className="error">قرارداد یا اثرانگشت Seed معتبر نیست؛ تأیید متوقف شد.</p>
      ) : null}
      {preview && trustworthy && !error ? (
        <>
          <dl className="ai-record-meta" data-testid="seed-learning-metadata">
            <div><dt>عنوان</dt><dd>{preview.dataset_name}</dd></div>
            <div><dt>نسخه</dt><dd>{preview.source_version}</dd></div>
            <div><dt>تعداد رکورد</dt><dd>{preview.record_count.toLocaleString("fa-IR")}</dd></div>
            <div><dt>نوع داده</dt><dd>{preview.source_type}</dd></div>
            <div><dt>سیاست</dt><dd>{preview.source_policy_key} / {preview.source_policy_version}</dd></div>
            <div><dt>فایل منبع</dt><dd dir="ltr">{preview.source_reference}</dd></div>
          </dl>
          <p>SHA-256 فایل منبع:</p>
          <code data-testid="seed-learning-sha256">{preview.source_payload_digest}</code>
          {preview.approved ? (
            <div data-testid="seed-learning-already-approved">
              <p>مجوز استفاده آموزشی AI برای این سازمان قبلاً ثبت شده است.</p>
              <p dir="ltr">Approval Event: {preview.approval_event_id ?? "نامشخص"}</p>
              <p className="muted">
                ثبت مجوز به معنای ساخته‌شدن Dataset Version نیست؛ ایجاد نسخه
                برعهده مصرف‌کننده رویداد و Dataset Builder است.
              </p>
            </div>
          ) : (
            <form className="form-stack" onSubmit={submit} data-testid="seed-learning-approval-form">
              <label htmlFor="seed-approval-reference">شناسه مستقل تأیید / مصوبه انسانی</label>
              <input
                id="seed-approval-reference"
                value={reference}
                maxLength={255}
                onChange={(e) => setReference(e.target.value)}
                placeholder="شناسه واقعی تصمیم بازبینی"
                disabled={busy || loading}
                required
              />
              <label htmlFor="seed-reviewed-file">
                <input
                  id="seed-reviewed-file" type="checkbox" checked={reviewedFile}
                  disabled={busy || loading}
                  onChange={(e) => setReviewedFile(e.target.checked)}
                />
                محتوای فایل منبع را واقعاً بازبینی کرده‌ام و مجوز مستقل استفاده آن
                برای آموزش AI را، جدا از مجوز نمایش دانش، تأیید می‌کنم.
              </label>
              <label htmlFor="seed-confirm-digest">برای تطبیق نسخه، SHA-256 کامل بالا را وارد کنید</label>
              <input
                id="seed-confirm-digest"
                value={confirmedDigest}
                onChange={(e) => setConfirmedDigest(e.target.value)}
                dir="ltr"
                spellCheck={false}
                autoComplete="off"
                disabled={busy || loading}
              />
              <button type="submit" disabled={!ready}>
                ثبت مجوز انسانی استفاده از Seed در دیتاست
              </button>
            </form>
          )}
        </>
      ) : null}
      {receipt ? (
        <div role="status" data-testid="seed-learning-approval-receipt">
          <strong>رویداد تأیید ثبت شد</strong>
          <p dir="ltr">{receipt.approval_event_id}</p>
          <p>
            ایجاد Dataset Version هنوز نیازمند مصرف رویداد از Outbox و اجرای
            Dataset Builder است؛ این پاسخ به‌تنهایی ایجاد Dataset را ثابت نمی‌کند.
          </p>
        </div>
      ) : null}
      <button type="button" className="ghost" disabled={busy || loading}
        onClick={onRefresh}>بازخوانی وضعیت Seed و دیتاست</button>
    </section>
  );
}

export function SeedLearningApprovalWorkspace({
  accessToken, organizationId, personId,
}: {
  accessToken: string;
  organizationId: string;
  personId: string;
}) {
  const api = makeApi(accessToken);
  const queryClient = useQueryClient();
  const queryKey = ["ai-seed-learning-preview", organizationId, personId, SEED_KEY];
  const preview = useQuery({
    queryKey,
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/admin/ai/seed-learning/decision-making-v1");
      if (error || !data) throw new Error("دریافت نسخه معتبر Seed ممکن نشد.");
      return data as SeedLearningPreview;
    },
    retry: false,
    staleTime: 0,
    refetchOnWindowFocus: true,
  });
  const approval = useMutation({
    mutationFn: async ({ digest, reference }: { digest: string; reference: string }) => {
      if (
        preview.isError || !preview.data || preview.data.approved ||
        preview.isFetching || digest !== preview.data.source_payload_digest
      ) throw new Error("نسخه Seed تغییر کرده یا وضعیت مجوز معتبر نیست؛ دوباره بررسی کنید.");
      const { data, error } = await api.POST(
        "/api/v1/admin/ai/seed-learning/decision-making-v1/approve",
        { body: { expected_source_payload_digest: digest, approval_reference: reference } },
      );
      if (error || !data) throw new Error("مجوز انسانی ثبت نشد؛ وضعیت و SHA را مجدداً بررسی کنید.");
      const receipt = data as SeedLearningApprovalReceipt;
      if (
        receipt.source_payload_digest !== digest ||
        receipt.source_reference !== preview.data.source_reference ||
        receipt.dataset_name !== preview.data.dataset_name ||
        receipt.reviewer_id !== personId
      ) throw new Error("رسید تأیید با هویت یا منبع فعلی سازگار نیست.");
      return receipt;
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey }),
        queryClient.invalidateQueries({ queryKey: ["admin-ai-governance"] }),
      ]);
    },
  });
  return (
    <SeedLearningApprovalView
      preview={preview.isSuccess && !preview.isFetching ? preview.data : undefined}
      loading={preview.isPending || preview.isFetching}
      busy={approval.isPending}
      error={preview.isError ? preview.error.message :
        approval.isError ? approval.error.message : undefined}
      receipt={approval.data}
      onApprove={(digest, reference) => approval.mutate({ digest, reference })}
      onRefresh={() => {
        approval.reset();
        void Promise.all([
          queryClient.invalidateQueries({ queryKey }),
          queryClient.invalidateQueries({ queryKey: ["admin-ai-governance"] }),
        ]);
      }}
    />
  );
}
