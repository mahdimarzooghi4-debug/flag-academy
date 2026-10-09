import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  AssessorClassView, type AssignedAssessorClassPage,
} from "./AssessorClassWorkspace";
import type {
  InstructorAttendance, InstructorClassActivity, InstructorRoster, InstructorSession,
} from "./InstructorClassWorkspace";
import type { CandidateClassReport } from "./CandidateReportWorkspace";

afterEach(cleanup);

const classes: AssignedAssessorClassPage = {
  items: [{
    class_offering_id: "class-a", cohort_id: "cohort-a",
    title: "کلاس ارزیابی الف", grant_id: "grant-a", grant_version: 1,
    starts_at: "2026-10-09T08:00:00Z", ends_at: "2026-10-10T08:00:00Z",
  }],
  next_offset: 50,
};
const roster: InstructorRoster = {
  class_offering_id: "class-a", cohort_id: "cohort-a", title: "کلاس ارزیابی الف",
  members: [{ person_id: "candidate-a", member_type: "CANDIDATE" }],
  instructor_person_ids: ["teacher-a"],
};
const sessions: InstructorSession[] = [{
  session_id: "session-a", class_offering_id: "class-a", title: "جلسه اول",
  starts_at: "2026-10-09T09:00:00Z", ends_at: "2026-10-09T10:00:00Z",
  delivery_mode: "IN_PERSON", status: "SCHEDULED",
}];
const attendance: InstructorAttendance = {
  session_id: "session-a", items: [],
};
const activity: InstructorClassActivity = {
  class_offering_id: "class-a", items: [{
    source_id: "attempt-a", source_type: "PRACTICE_ATTEMPT",
    source_parent_id: "learning-a", person_id: "candidate-a",
    occurred_at: "2026-10-09T09:00:00Z", state: "SUBMITTED",
  }], is_truncated: false,
};
const report: CandidateClassReport = {
  class_offering_id: "class-a", cohort_id: "cohort-a", person_id: "candidate-a",
  attendance_scope: "CLASS_OFFERING", attendance: [], subjects: [{
    capability_version_id: "cap-a", capability_name: "حل مسئله",
    capability_version_number: 1, learning_state: "LEARNING_COMPLETED",
    proof_state: null, next_learning_focus: null, reviewed_claim: null,
    learning_sources: [], feedback_sources: [{
      source_type: "PRACTICE_FEEDBACK", source_id: "feedback-a",
      feedback_text: "بازخورد مدرس", created_at: "2026-10-09T10:00:00Z",
    }],
  }],
};

function mount(overrides: Partial<Parameters<typeof AssessorClassView>[0]> = {}) {
  const actions = {
    onClassChange: vi.fn(), onPageOffset: vi.fn(),
    onSessionChange: vi.fn(), onPersonChange: vi.fn(),
  };
  render(<AssessorClassView
    classes={classes} classId="class-a" onClassChange={actions.onClassChange}
    pageOffset={0} onPageOffset={actions.onPageOffset}
    roster={roster} sessions={sessions} sessionId="session-a"
    onSessionChange={actions.onSessionChange}
    attendance={attendance} activity={activity} personId="candidate-a"
    onPersonChange={actions.onPersonChange} report={report} {...overrides}
  />);
  return actions;
}

describe("Assessor class view", () => {
  it("shows only assigned classroom projections as read-only, without inventing proof", () => {
    const actions = mount();
    expect(screen.getByTestId("assessor-class-workspace")).toBeInTheDocument();
    expect(screen.getByText("کلاس ارزیابی الف")).toBeInTheDocument();
    expect(screen.getByText("ثبت نشده؛ غیبت محسوب نمی‌شود")).toBeInTheDocument();
    expect(screen.getByText("بازخورد مدرس")).toBeInTheDocument();
    expect(screen.getByText("اثبات رسمی مستقل: داده معتبر مستقل موجود نیست")).toBeInTheDocument();
    expect(screen.getByText("تمرکز بعدی: هنوز توسط مدرس تصویب نشده")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /ثبت حضور|پذیرش Evidence|Gate PASS/i }))
      .not.toBeInTheDocument();
    expect(actions.onPersonChange).not.toHaveBeenCalled();
  });

  it("hides all private details if class or cohort lineage is mismatched", () => {
    mount({ roster: { ...roster, cohort_id: "cohort-b" } });
    expect(screen.queryByText("بازخورد مدرس")).not.toBeInTheDocument();
    expect(screen.queryByText("PRACTICE_ATTEMPT")).not.toBeInTheDocument();
    expect(screen.queryByText("حل مسئله")).not.toBeInTheDocument();
  });

  it("hides all private details while permission is revalidating or has failed", () => {
    mount({ loading: true, error: "مجوز کلاس باطل شد" });
    expect(screen.getByRole("alert")).toHaveTextContent("مجوز کلاس باطل شد");
    expect(screen.queryByText("بازخورد مدرس")).not.toBeInTheDocument();
    expect(screen.queryByText("candidate-a")).not.toBeInTheDocument();
  });

  it("does not resurrect private classroom data when grants disappear", () => {
    mount({ classes: { items: [], next_offset: null }, classId: undefined });
    expect(screen.getByText("اکنون مأموریت معتبر کلاسی ندارید.")).toBeInTheDocument();
    expect(screen.queryByText("بازخورد مدرس")).not.toBeInTheDocument();
    expect(screen.queryByText("candidate-a")).not.toBeInTheDocument();
  });

  it("can only navigate classes returned in the current grant page", () => {
    const actions = mount();
    fireEvent.click(screen.getByRole("button", { name: "کلاس‌های بعد" }));
    expect(actions.onPageOffset).toHaveBeenCalledExactlyOnceWith(50);
    fireEvent.change(screen.getByLabelText("کلاس منصوب‌شده"), {
      target: { value: "class-a" },
    });
    expect(actions.onClassChange).toHaveBeenCalledExactlyOnceWith("class-a");
    fireEvent.change(screen.getByLabelText("فراگیر کلاس"), {
      target: { value: "candidate-a" },
    });
    expect(actions.onPersonChange).toHaveBeenCalledExactlyOnceWith("candidate-a");
  });
});
