import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  SeedLearningApprovalView,
  type SeedLearningApprovalReceipt,
  type SeedLearningPreview,
} from "./SeedLearningApprovalWorkspace";

afterEach(cleanup);

const DIGEST = "a".repeat(64);
const preview: SeedLearningPreview = {
  seed_key: "decision-making-v1",
  source_reference: "docs/ai/seed/decision-making-v1.jsonl",
  source_version: "1",
  source_payload_digest: DIGEST,
  record_count: 24,
  dataset_name: "parcham-decision-making",
  purpose: "MODEL_TRAINING",
  source_policy_key: "parcham-curated-synthetic-seed",
  source_policy_version: "v1",
  source_type: "CURATED_SYNTHETIC_SEED",
  data_classification: "INTERNAL",
  approved: false,
  approval_event_id: null,
  approved_by: null,
};
const receipt: SeedLearningApprovalReceipt = {
  approval_event_id: "00000000-0000-0000-0000-000000000704",
  source_payload_digest: DIGEST,
  record_count: 24,
  dataset_name: preview.dataset_name,
  purpose: preview.purpose,
  source_reference: preview.source_reference,
  source_version: preview.source_version,
  approval_reference: "REAL-APPROVAL-REFERENCE",
  reviewer_id: "00000000-0000-0000-0000-000000000001",
  created: true,
  dataset_creation_pending: true,
};

function mount(overrides: Partial<Parameters<typeof SeedLearningApprovalView>[0]> = {}) {
  const onApprove = vi.fn();
  const onRefresh = vi.fn();
  const props = { preview, onApprove, onRefresh, ...overrides };
  const view = render(<SeedLearningApprovalView {...props} />);
  return { ...view, onApprove, onRefresh, props };
}

describe("governed Seed learning approval UI", () => {
  it("shows exact source/digest and never mistakes Seed for an already created Dataset", () => {
    const { onApprove } = mount();
    expect(screen.getByText("parcham-decision-making")).toBeInTheDocument();
    expect(screen.getByTestId("seed-learning-sha256")).toHaveTextContent(DIGEST);
    expect(screen.getByTestId("seed-learning-metadata")).toHaveTextContent(
      "docs/ai/seed/decision-making-v1.jsonl",
    );
    expect(screen.getByRole("button", { name: "ثبت مجوز انسانی استفاده از Seed در دیتاست" }))
      .toBeDisabled();
    expect(onApprove).not.toHaveBeenCalled();
  });

  it("requires separate actual-file review, independent approval reference, and exact full digest", () => {
    const { onApprove } = mount();
    const approve = screen.getByRole("button", { name: "ثبت مجوز انسانی استفاده از Seed در دیتاست" });
    fireEvent.change(screen.getByLabelText("شناسه مستقل تأیید / مصوبه انسانی"), {
      target: { value: "REAL-DECISION-ID" },
    });
    fireEvent.change(screen.getByLabelText("برای تطبیق نسخه، SHA-256 کامل بالا را وارد کنید"), {
      target: { value: "b".repeat(64) },
    });
    fireEvent.click(screen.getByLabelText(/محتوای فایل منبع را واقعاً بازبینی کرده‌ام/));
    expect(approve).toBeDisabled();
    fireEvent.change(screen.getByLabelText("برای تطبیق نسخه، SHA-256 کامل بالا را وارد کنید"), {
      target: { value: DIGEST },
    });
    expect(approve).toBeEnabled();
    fireEvent.click(approve);
    expect(onApprove).toHaveBeenCalledExactlyOnceWith(DIGEST, "REAL-DECISION-ID");
  });

  it("fails closed when a source contract or digest is not the approved fixed Seed", () => {
    const { rerender, onApprove, props } = mount({
      preview: { ...preview, source_reference: "other-file.jsonl" },
    });
    expect(screen.getByRole("alert")).toHaveTextContent("قرارداد یا اثرانگشت Seed معتبر نیست");
    expect(screen.queryByRole("button", { name: "ثبت مجوز انسانی استفاده از Seed در دیتاست" }))
      .not.toBeInTheDocument();
    rerender(<SeedLearningApprovalView
      {...props} preview={{ ...preview, source_payload_digest: "invalid" }}
    />);
    expect(screen.queryByTestId("seed-learning-approval-form")).not.toBeInTheDocument();
    expect(onApprove).not.toHaveBeenCalled();
  });

  it("removes prior review confirmation if source digest changes", () => {
    const { rerender, props } = mount();
    fireEvent.change(screen.getByLabelText("شناسه مستقل تأیید / مصوبه انسانی"), {
      target: { value: "DELIBERATE-APPROVAL" },
    });
    fireEvent.change(screen.getByLabelText("برای تطبیق نسخه، SHA-256 کامل بالا را وارد کنید"), {
      target: { value: DIGEST },
    });
    fireEvent.click(screen.getByLabelText(/محتوای فایل منبع را واقعاً بازبینی کرده‌ام/));
    expect(screen.getByRole("button", { name: "ثبت مجوز انسانی استفاده از Seed در دیتاست" }))
      .toBeEnabled();
    rerender(<SeedLearningApprovalView
      {...props} preview={{ ...preview, source_payload_digest: "c".repeat(64) }}
    />);
    expect(screen.getByLabelText("شناسه مستقل تأیید / مصوبه انسانی")).toHaveValue("");
    expect(screen.getByLabelText("برای تطبیق نسخه، SHA-256 کامل بالا را وارد کنید")).toHaveValue("");
    expect(screen.getByRole("button", { name: "ثبت مجوز انسانی استفاده از Seed در دیتاست" }))
      .toBeDisabled();
  });

  it("treats existing approved version as read-only, never approves again", () => {
    const { onApprove } = mount({
      preview: { ...preview, approved: true, approval_event_id: receipt.approval_event_id },
    });
    expect(screen.getByTestId("seed-learning-already-approved")).toHaveTextContent(
      receipt.approval_event_id,
    );
    expect(screen.queryByTestId("seed-learning-approval-form")).not.toBeInTheDocument();
    expect(onApprove).not.toHaveBeenCalled();
  });

  it("does not confuse a receipt with a persistent Dataset Version", () => {
    mount({ receipt });
    expect(screen.getByTestId("seed-learning-approval-receipt")).toHaveTextContent(
      "ایجاد Dataset Version هنوز نیازمند مصرف رویداد",
    );
  });

  it("disables approval and refresh during a request and hides untrusted preview on read failure", () => {
    const { rerender, props, onApprove } = mount({ loading: true, busy: true });
    expect(screen.getByRole("button", { name: "بازخوانی وضعیت Seed و دیتاست" }))
      .toBeDisabled();
    rerender(<SeedLearningApprovalView {...props} error="دریافت ناموفق" loading={false} busy={false} />);
    expect(screen.getByRole("alert")).toHaveTextContent("دریافت ناموفق");
    expect(screen.queryByTestId("seed-learning-approval-form")).not.toBeInTheDocument();
    expect(onApprove).not.toHaveBeenCalled();
  });
});
