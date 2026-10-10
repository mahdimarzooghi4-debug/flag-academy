import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  CandidateReportCardView,
  type CandidateClass,
  type CandidateClassReport,
} from "./CandidateReportWorkspace";

afterEach(() => cleanup());

const classes: CandidateClass[] = [
  {
    class_offering_id: "class-a",
    cohort_id: "cohort-a",
    title: "کارگاه تصمیم‌گیری",
    primary_capability_version_id: "capability-version-1",
    status: "ACTIVE",
  },
  {
    class_offering_id: "class-b",
    cohort_id: "cohort-a",
    title: "کلاس مالکیت محصول",
    primary_capability_version_id: "capability-version-2",
    status: "ACTIVE",
  },
];

const report: CandidateClassReport = {
  class_offering_id: "class-a",
  cohort_id: "cohort-a",
  person_id: "candidate-a",
  attendance_scope: "CLASS_OFFERING",
  attendance: [
    {
      session_id: "session-a",
      title: "جلسه نخست",
      starts_at: "2026-10-08T12:00:00Z",
      status: "NOT_RECORDED",
      attendance_record_id: null,
    },
  ],
  subjects: [
    {
      capability_version_id: "capability-version-1",
      capability_name: "قضاوت محصول",
      capability_version_number: 3,
      learning_state: "IN_LEARNING",
      proof_state: null,
      next_learning_focus: null,
      reviewed_claim: null,
      learning_sources: [
        {
          source_type: "LEARNING_UNIT",
          source_id: "unit-a",
          state: "IN_PROGRESS",
          title: "تحلیل تصمیم",
        },
      ],
      feedback_sources: [],
    },
  ],
};

describe("CandidateReportCardView", () => {
  it("shows actual learning separately from missing formal proof and attendance", () => {
    render(
      <CandidateReportCardView
        classes={classes}
        selectedClassId="class-a"
        onSelectClass={vi.fn()}
        report={report}
        loading={false}
      />,
    );
    expect(screen.getByText("قضاوت محصول")).toBeInTheDocument();
    expect(screen.getByText("در حال یادگیری")).toBeInTheDocument();
    expect(screen.getByText("حضور و غیاب هنوز ثبت نشده")).toBeInTheDocument();
    expect(screen.getByText(/وضعیت معتبر در این کارنامه ارائه نشده است/)).toBeInTheDocument();
    expect(screen.getByText(/برای این درس Claim بازبینی‌شده‌ای در دسترس نیست/)).toBeInTheDocument();
    expect(screen.getByText(/هنوز تعیین نشده است/)).toBeInTheDocument();
    expect(screen.getByText(/تحلیل تصمیم/)).toBeInTheDocument();
    expect(screen.queryByText("ABSENT")).not.toBeInTheDocument();
    expect(screen.queryByText("UNPROVEN")).not.toBeInTheDocument();
  });

  it("allows class selection without inventing report results", () => {
    const choose = vi.fn();
    render(
      <CandidateReportCardView
        classes={classes}
        selectedClassId="class-a"
        onSelectClass={choose}
        loading={true}
      />,
    );
    fireEvent.change(screen.getByRole("combobox", { name: "انتخاب کلاس" }), {
      target: { value: "class-b" },
    });
    expect(choose).toHaveBeenCalledWith("class-b");
    expect(screen.getByText("در حال دریافت کارنامه...")).toBeInTheDocument();
    expect(screen.queryByText("قضاوت محصول")).not.toBeInTheDocument();
  });

  it("distinguishes no classes, missing lesson records and request failures", () => {
    const { rerender } = render(
      <CandidateReportCardView
        classes={[]}
        onSelectClass={vi.fn()}
        loading={false}
      />,
    );
    expect(screen.getByText(/در این گروه آموزشی هنوز کلاسی ثبت نشده/)).toBeInTheDocument();
    rerender(
      <CandidateReportCardView
        classes={classes}
        selectedClassId="class-a"
        onSelectClass={vi.fn()}
        loading={false}
        error="دریافت کارنامه کلاس ناموفق بود."
      />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("دریافت کارنامه کلاس ناموفق بود.");
    expect(screen.queryByText("قضاوت محصول")).not.toBeInTheDocument();
  });

  it("displays reviewed claim as a distinct human-reviewed record", () => {
    render(
      <CandidateReportCardView
        classes={classes}
        selectedClassId="class-a"
        onSelectClass={vi.fn()}
        loading={false}
        report={{
          ...report,
          subjects: [
            {
              ...report.subjects[0],
              reviewed_claim: {
                claim_id: "claim-a",
                claim_version: 2,
                claim_state: "DEMONSTRATED",
                level: "L2",
                reviewed_at: "2026-10-08T12:00:00Z",
              },
            },
          ],
        }}
      />,
    );
    expect(screen.getByText(/Claim بازبینی‌شده انسانی/)).toBeInTheDocument();
    expect(screen.getByText(/DEMONSTRATED/)).toBeInTheDocument();
    expect(screen.getByText(/وضعیت معتبر در این کارنامه ارائه نشده است/)).toBeInTheDocument();
  });
});
