import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AssessorGrantAdminView, explicitUtcInstant, type AssessorClassGrant } from "./AssessorGrantAdminWorkspace";

const ASSESSOR = "00000000-0000-0000-0000-000000000104";
const grant: AssessorClassGrant = {
  grant_id: "00000000-0000-4000-8000-000000000115",
  version: 2,
  organization_context_id: "org-one",
  class_offering_id: "class-one",
  assessor_person_id: ASSESSOR,
  starts_at: "2026-10-09T00:00:00Z",
  ends_at: "2026-10-10T00:00:00Z",
  revoked_at: null,
};

afterEach(cleanup);

function setup(overrides: Partial<Parameters<typeof AssessorGrantAdminView>[0]> = {}) {
  const actions = { onCreate: vi.fn(), onExtend: vi.fn(), onRevoke: vi.fn(), onOffset: vi.fn() };
  render(
    <AssessorGrantAdminView
      classId="class-one"
      grants={{ items: [grant], next_offset: 50 }}
      offset={0}
      {...actions}
      {...overrides}
    />,
  );
  return actions;
}

describe("Class Assessor admin mandate", () => {
  it("requires a human-specified timezone window and valid person ID", () => {
    const actions = setup();
    fireEvent.change(screen.getByLabelText("شناسه ارزیاب عضو همین سازمان"), {
      target: { value: ASSESSOR },
    });
    fireEvent.change(screen.getByLabelText("آغاز مأموریت (ISO با منطقه زمانی)"), {
      target: { value: "2026-10-09T10:00:00Z" },
    });
    fireEvent.change(screen.getByLabelText("پایان مأموریت (ISO با منطقه زمانی)"), {
      target: { value: "2026-10-10T10:00:00Z" },
    });
    fireEvent.click(screen.getByRole("button", { name: "ثبت انتصاب با تأیید مدیر" }));
    expect(actions.onCreate).toHaveBeenCalledExactlyOnceWith(
      ASSESSOR, "2026-10-09T10:00:00.000Z", "2026-10-10T10:00:00.000Z",
    );
    expect(actions.onRevoke).not.toHaveBeenCalled();
  });

  it("does not infer a timezone or accept an inverted window", () => {
    expect(() => explicitUtcInstant("2026-10-09T10:00:00")).toThrow();
    expect(() => explicitUtcInstant("invalid")).toThrow();
    const actions = setup({ grants: { items: [], next_offset: null } });
    fireEvent.change(screen.getByLabelText("شناسه ارزیاب عضو همین سازمان"), {
      target: { value: ASSESSOR },
    });
    fireEvent.change(screen.getByLabelText("آغاز مأموریت (ISO با منطقه زمانی)"), {
      target: { value: "2026-10-10T10:00:00Z" },
    });
    fireEvent.change(screen.getByLabelText("پایان مأموریت (ISO با منطقه زمانی)"), {
      target: { value: "2026-10-09T10:00:00Z" },
    });
    fireEvent.click(screen.getByRole("button", { name: "ثبت انتصاب با تأیید مدیر" }));
    expect(screen.getByRole("alert")).toHaveTextContent("پایان مأموریت باید بعد از شروع آن باشد.");
    expect(actions.onCreate).not.toHaveBeenCalled();
  });

  it("demands explicit reason, current selected version and confirmation to revoke", () => {
    const actions = setup();
    const cancel = screen.getByRole("button", { name: "لغو مأموریت" });
    expect(cancel).toBeDisabled();
    fireEvent.change(screen.getByLabelText("دلیل تمدید یا لغو"), {
      target: { value: "End of authorized assessment" },
    });
    expect(cancel).toBeDisabled();
    fireEvent.click(screen.getByLabelText(
      "لغو مأموریت این ارزیاب در همین کلاس را تأیید می‌کنم."
    ));
    expect(cancel).toBeEnabled();
    fireEvent.click(cancel);
    expect(actions.onRevoke).toHaveBeenCalledExactlyOnceWith(
      grant, "End of authorized assessment"
    );
    expect(cancel).toBeDisabled();
  });

  it("permits reasoned extension but blocks existing or earlier end", () => {
    const actions = setup();
    fireEvent.change(screen.getByLabelText("دلیل تمدید یا لغو"), {
      target: { value: "Extended assessment scope" },
    });
    fireEvent.change(screen.getByLabelText("تاریخ پایان جدید (ISO با منطقه زمانی)"), {
      target: { value: "2026-10-11T00:00:00Z" },
    });
    fireEvent.click(screen.getByRole("button", { name: "تمدید مأموریت" }));
    expect(actions.onExtend).toHaveBeenCalledExactlyOnceWith(
      grant, "2026-10-11T00:00:00.000Z", "Extended assessment scope"
    );
  });

  it("retains revoked history read only and pages only on explicit selection", () => {
    const actions = setup({
      grants: { items: [{ ...grant, revoked_at: "2026-10-09T14:00:00Z" }], next_offset: 50 },
    });
    expect(screen.getByTestId("selected-assessor-grant")).toHaveTextContent("2026-10-09T14:00:00Z");
    expect(screen.queryByRole("button", { name: "تمدید مأموریت" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "لغو مأموریت" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "صفحه بعد مأموریت‌ها" }));
    expect(actions.onOffset).toHaveBeenCalledExactlyOnceWith(50);
    expect(actions.onRevoke).not.toHaveBeenCalled();
  });

  it("fails closed on operational errors and mutation pending", () => {
    const actions = setup({ busy: true, error: "Class mismatch" });
    expect(screen.getByRole("alert")).toHaveTextContent("Class mismatch");
    expect(screen.getByRole("button", { name: "ثبت انتصاب با تأیید مدیر" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "تمدید مأموریت" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "صفحه بعد مأموریت‌ها" })).toBeDisabled();
    expect(actions.onExtend).not.toHaveBeenCalled();
  });

  it("invalidates human confirmation when a concurrent admin changes the grant version", () => {
    const onRevoke = vi.fn();
    const props = {
      classId: "class-one",
      offset: 0,
      grants: { items: [grant], next_offset: null },
      onCreate: vi.fn(),
      onExtend: vi.fn(),
      onRevoke,
      onOffset: vi.fn(),
    };
    const { rerender } = render(<AssessorGrantAdminView {...props} />);
    fireEvent.change(screen.getByLabelText("دلیل تمدید یا لغو"), {
      target: { value: "Review complete" },
    });
    fireEvent.click(screen.getByLabelText(
      "لغو مأموریت این ارزیاب در همین کلاس را تأیید می‌کنم."
    ));
    expect(screen.getByRole("button", { name: "لغو مأموریت" })).toBeEnabled();
    rerender(<AssessorGrantAdminView
      {...props}
      grants={{ items: [{ ...grant, version: 3 }], next_offset: null }}
    />);
    expect(screen.getByRole("button", { name: "لغو مأموریت" })).toBeDisabled();
    expect(screen.getByLabelText("دلیل تمدید یا لغو")).toHaveValue("");
    expect(onRevoke).not.toHaveBeenCalled();
  });

});
