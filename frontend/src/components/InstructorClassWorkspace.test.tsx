import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  InstructorClassView,
  type InstructorAttendance,
  type InstructorClassActivity,
  type InstructorRoster,
  type InstructorSession,
} from "./InstructorClassWorkspace";
import type { CandidateClassReport } from "./CandidateReportWorkspace";

afterEach(() => cleanup());

const classes = [
  { id: "class-a", title: "کلاس واگذارشده الف" },
  { id: "class-b", title: "کلاس واگذارشده ب" },
];
const roster: InstructorRoster = {
  class_offering_id: "class-a",
  cohort_id: "cohort-a",
  title: "کلاس واگذارشده الف",
  members: [
    { person_id: "learner-a", member_type: "CANDIDATE" },
    { person_id: "learner-b", member_type: "CANDIDATE" },
    { person_id: "staff-a", member_type: "INSTRUCTOR" },
  ],
  instructor_person_ids: ["staff-a"],
};
const sessions: InstructorSession[] = [
  {
    session_id: "session-a", class_offering_id: "class-a",
    title: "جلسه آزمایشی", starts_at: "2026-10-09T09:00:00Z",
    ends_at: "2026-10-09T10:00:00Z", delivery_mode: "IN_PERSON",
    status: "SCHEDULED",
  },
];
const attendance: InstructorAttendance = {
  session_id: "session-a",
  items: [
    { id: "attendance-a", person_id: "learner-a", status: "PRESENT", version: 1 },
  ],
};
const activity: InstructorClassActivity = {
  class_offering_id: "class-a",
  items: [{
    source_id: "source-a",
    source_type: "PRACTICE_ATTEMPT",
    source_parent_id: "unit-a",
    person_id: "learner-a",
    occurred_at: "2026-10-09T09:00:00Z",
    state: "SUBMITTED",
  }],
  is_truncated: false,
};
const report: CandidateClassReport = {
  class_offering_id: "class-a",
  cohort_id: "cohort-a",
  person_id: "learner-a",
  attendance_scope: "CLASS_OFFERING",
  attendance: [],
  subjects: [{
    capability_version_id: "cap-a",
    capability_name: "قضاوت محصول",
    capability_version_number: 1,
    learning_state: "IN_LEARNING",
    proof_state: null,
    next_learning_focus: null,
    reviewed_claim: null,
    learning_sources: [],
    feedback_sources: [],
  }],
};

function renderView(override: Partial<Parameters<typeof InstructorClassView>[0]> = {}) {
  return render(
    <InstructorClassView
      classes={classes}
      classId="class-a"
      onClassChange={vi.fn()}
      roster={roster}
      sessions={sessions}
      sessionId="session-a"
      onSessionChange={vi.fn()}
      attendance={attendance}
      activity={activity}
      personId="learner-a"
      onPersonChange={vi.fn()}
      report={report}
      practiceFeedbackPending={2}
      assignmentFeedbackPending={1}
      {...override}
    />,
  );
}

describe("InstructorClassView", () => {
  it("shows real roster and recorded-only attendance without inventing absence", () => {
    renderView();
    const workspace = screen.getByTestId("instructor-class-workspace");
    expect(within(workspace).getByText("عملیات کلاس من")).toBeInTheDocument();
    expect(within(workspace).getAllByText("learner-a").length).toBeGreaterThan(0);
    expect(within(workspace).getAllByText("learner-b").length).toBeGreaterThan(0);
    expect(within(workspace).queryByText("staff-a")).not.toBeInTheDocument();
    expect(within(workspace).getByText("حاضر")).toBeInTheDocument();
    expect(within(workspace).getByText("ثبت نشده؛ به معنی غیبت نیست")).toBeInTheDocument();
    expect(within(workspace).getByText(/PRACTICE_ATTEMPT/)).toBeInTheDocument();
    expect(within(workspace).getByText("قضاوت محصول")).toBeInTheDocument();
    expect(within(workspace).getByText(/وضعیت مستقل در دسترس نیست/)).toBeInTheDocument();
    expect(within(workspace).getByText(/تلاش‌های تمرینی بدون بازخورد: 2/)).toBeInTheDocument();
  });

  it("selects class, session and learner from known context", () => {
    const onClass = vi.fn();
    const onSession = vi.fn();
    const onPerson = vi.fn();
    renderView({
      onClassChange: onClass,
      onSessionChange: onSession,
      onPersonChange: onPerson,
    });
    fireEvent.change(screen.getByLabelText("کلاس تخصیص‌یافته"), {
      target: { value: "class-b" },
    });
    fireEvent.change(screen.getByLabelText("انتخاب جلسه"), {
      target: { value: "session-a" },
    });
    fireEvent.change(screen.getByLabelText("انتخاب فراگیر کلاس"), {
      target: { value: "learner-b" },
    });
    expect(onClass).toHaveBeenCalledWith("class-b");
    expect(onSession).toHaveBeenCalledWith("session-a");
    expect(onPerson).toHaveBeenCalledWith("learner-b");
  });

  it("shows absence of assigned classes and prevents private stale panels on error", () => {
    renderView({
      classes: [],
      classId: undefined,
      roster: undefined,
      sessions: undefined,
      attendance: undefined,
      activity: undefined,
      report: undefined,
      errors: ["کلاس مجاز نیست."],
    });
    expect(screen.getByText("هنوز کلاسی به این مدرس واگذار نشده است.")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("کلاس مجاز نیست.");
    expect(screen.queryByText("قضاوت محصول")).not.toBeInTheDocument();
  });

  it("keeps reviewed claim and proof independent even when educational work completes", () => {
    renderView({
      report: {
        ...report,
        subjects: [{
          ...report.subjects[0],
          learning_state: "LEARNING_COMPLETED",
          proof_state: null,
          reviewed_claim: {
            claim_id: "claim-a", claim_version: 2, claim_state: "EMERGING",
            level: "L1", reviewed_at: "2026-10-09T09:00:00Z",
          },
        }],
      },
    });
    expect(screen.getByText("الزامات آموزشی تکمیل شده")).toBeInTheDocument();
    expect(screen.getByText(/Claim انسانی: EMERGING/)).toBeInTheDocument();
    expect(screen.getByText(/وضعیت مستقل در دسترس نیست/)).toBeInTheDocument();
  });
});
