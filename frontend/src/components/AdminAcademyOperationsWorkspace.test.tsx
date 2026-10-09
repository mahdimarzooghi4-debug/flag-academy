import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  AdminAcademyOperationsView,
  type AdminClassPage,
  type AdminCohortPage,
} from "./AdminAcademyOperationsWorkspace";
import type {
  InstructorAttendance,
  InstructorClassActivity,
  InstructorRoster,
  InstructorSession,
} from "./InstructorClassWorkspace";
import type { CandidateClassReport } from "./CandidateReportWorkspace";

afterEach(() => cleanup());

const cohorts: AdminCohortPage = {
  items: [
    { cohort_id: "cohort-a", code: "A", name: "گروه اصلی", track_code: "PRODUCT", status: "ACTIVE" },
    { cohort_id: "cohort-b", code: "B", name: "گروه دوم", track_code: "PRODUCT", status: "ACTIVE" },
  ],
  next_offset: 50,
};
const classes: AdminClassPage = {
  cohort_id: "cohort-a",
  items: [
    {
      class_offering_id: "class-a", cohort_id: "cohort-a", title: "کلاس واقعی الف",
      primary_capability_version_id: "version-a", status: "ACTIVE",
    },
    {
      class_offering_id: "class-b", cohort_id: "cohort-a", title: "کلاس واقعی ب",
      primary_capability_version_id: "version-b", status: "ACTIVE",
    },
  ],
  next_offset: null,
};
const roster: InstructorRoster = {
  class_offering_id: "class-a",
  cohort_id: "cohort-a",
  title: "کلاس واقعی الف",
  members: [
    { person_id: "candidate-a", member_type: "CANDIDATE" },
    { person_id: "candidate-b", member_type: "CANDIDATE" },
    { person_id: "teacher-a", member_type: "INSTRUCTOR" },
  ],
  instructor_person_ids: ["teacher-a"],
};
const sessions: InstructorSession[] = [{
  session_id: "session-a", class_offering_id: "class-a", title: "جلسه اول",
  starts_at: "2026-10-09T10:00:00Z", ends_at: "2026-10-09T11:00:00Z",
  delivery_mode: "IN_PERSON", status: "SCHEDULED",
}];
const attendance: InstructorAttendance = {
  session_id: "session-a",
  items: [{ id: "record-a", person_id: "candidate-a", status: "PRESENT", version: 2 }],
};
const activity: InstructorClassActivity = {
  class_offering_id: "class-a",
  items: [{
    source_type: "PRACTICE_ATTEMPT", source_id: "source-a",
    source_parent_id: "unit-a", person_id: "candidate-a",
    occurred_at: "2026-10-09T10:00:00Z", state: "SUBMITTED",
  }],
  is_truncated: false,
};
const report: CandidateClassReport = {
  class_offering_id: "class-a",
  cohort_id: "cohort-a",
  person_id: "candidate-a",
  attendance_scope: "CLASS_OFFERING",
  attendance: [],
  subjects: [{
    capability_version_id: "version-a", capability_name: "قضاوت محصول",
    capability_version_number: 1, learning_state: "LEARNING_COMPLETED",
    proof_state: null, next_learning_focus: null,
    reviewed_claim: {
      claim_id: "claim-a", claim_version: 2, claim_state: "EMERGING",
      level: "L1", reviewed_at: "2026-10-09T10:00:00Z",
    },
    learning_sources: [], feedback_sources: [],
  }],
};

function mount(overrides: Partial<Parameters<typeof AdminAcademyOperationsView>[0]> = {}) {
  const callbacks = {
    onCohortChange: vi.fn(),
    onCohortOffset: vi.fn(),
    onClassChange: vi.fn(),
    onClassOffset: vi.fn(),
    onSessionChange: vi.fn(),
    onPersonChange: vi.fn(),
    onRecordAttendance: vi.fn(),
  };
  render(
    <AdminAcademyOperationsView
      cohorts={cohorts}
      cohortId="cohort-a"
      cohortOffset={0}
      classes={classes}
      classId="class-a"
      classOffset={0}
      roster={roster}
      sessions={sessions}
      sessionId="session-a"
      attendance={attendance}
      activity={activity}
      selectedPersonId="candidate-a"
      report={report}
      {...callbacks}
      {...overrides}
    />,
  );
  return callbacks;
}

describe("AdminAcademyOperationsView", () => {
  it("shows real class context with recorded-only attendance and separate proof", () => {
    mount();
    const root = screen.getByTestId("admin-academy-operations");
    expect(within(root).getByText("مدیریت عملیاتی آکادمی")).toBeInTheDocument();
    expect(within(root).getAllByText("candidate-a").length).toBeGreaterThan(0);
    expect(within(root).getAllByText("candidate-b").length).toBeGreaterThan(0);
    expect(within(root).getByText("حاضر")).toBeInTheDocument();
    expect(within(root).getByText("ثبت نشده؛ غیبت محسوب نمی‌شود")).toBeInTheDocument();
    expect(within(root).getByText("PRACTICE_ATTEMPT")).toBeInTheDocument();
    expect(within(root).getByText("قضاوت محصول")).toBeInTheDocument();
    expect(within(root).getByText("آموزش: الزامات آموزشی تکمیل شده")).toBeInTheDocument();
    expect(within(root).getByText("ProofState مستقل: نامشخص")).toBeInTheDocument();
    expect(within(root).getByText("Claim بازبینی‌شده انسانی: EMERGING")).toBeInTheDocument();
    expect(within(root).queryByText("UNPROVEN")).not.toBeInTheDocument();
  });

  it("only submits an explicit admin attendance command, never a default absence", () => {
    const actions = mount();
    expect(actions.onRecordAttendance).not.toHaveBeenCalled();
    const unknown = screen.getAllByText("candidate-b")[1].closest(".admin-ops-attendance-row");
    expect(unknown).not.toBeNull();
    fireEvent.click(within(unknown as HTMLElement).getByRole("button", { name: "ثبت غایب" }));
    expect(actions.onRecordAttendance).toHaveBeenCalledExactlyOnceWith("candidate-b", "ABSENT");
    const recorded = screen.getAllByText("candidate-a")[1].closest(".admin-ops-attendance-row");
    expect(within(recorded as HTMLElement).getByRole("button", { name: "ثبت حاضر" })).toBeDisabled();
  });

  it("selects pages and scopes and does not invent hidden extra results", () => {
    const actions = mount();
    fireEvent.click(screen.getByRole("button", { name: "گروه‌های بعدی" }));
    expect(actions.onCohortOffset).toHaveBeenCalledWith(50);
    fireEvent.change(screen.getByLabelText("گروه آموزشی سازمان"), { target: { value: "cohort-b" } });
    expect(actions.onCohortChange).toHaveBeenCalledWith("cohort-b");
    fireEvent.change(screen.getByLabelText("کلاس واقعی"), { target: { value: "class-b" } });
    expect(actions.onClassChange).toHaveBeenCalledWith("class-b");
    fireEvent.change(screen.getByLabelText("جلسه کلاس"), { target: { value: "session-a" } });
    expect(actions.onSessionChange).toHaveBeenCalledWith("session-a");
    fireEvent.change(screen.getByLabelText("فراگیر برای کارنامه"), { target: { value: "candidate-b" } });
    expect(actions.onPersonChange).toHaveBeenCalledWith("candidate-b");
  });

  it("hides private class detail on failed read and does not send mutations", () => {
    const actions = mount({
      errors: ["دسترسی به کلاس تأیید نشد."],
      roster: undefined,
      report: undefined,
      activity: undefined,
      attendance: undefined,
    });
    expect(screen.getByRole("alert")).toHaveTextContent("دسترسی به کلاس تأیید نشد.");
    expect(screen.queryByText("قضاوت محصول")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "ثبت غایب" })).not.toBeInTheDocument();
    expect(actions.onRecordAttendance).not.toHaveBeenCalled();
  });
});
