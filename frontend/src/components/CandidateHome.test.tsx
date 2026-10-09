import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CandidateHome } from "./CandidateHome";

describe("CandidateHome", () => {
  it("separates learning from proof", () => {
    render(
      <CandidateHome
        data={{
          journey: { track: "PRODUCT_MANAGER", state: "ACTIVE" },
          cohort: { id: "cohort-1", name: "PM Flag Cohort" },
          current_wave: { code: "WAVE_1", name: "Think & Own" },
          what_to_learn: [
            {
              capability_version_id: "1",
              name: "Ownership",
              learning_state: "TO_LEARN",
              next_session: null,
            },
          ],
          what_to_prove: [
            {
              capability_version_id: "1",
              name: "Ownership",
              proof_state: "UNPROVEN",
            },
          ],
          upcoming_sessions: [],
          learning_tasks: [],
          open_missions: [],
          profile_summary: { status: "UNPROVEN" },
          processing_states: [],
        }}
      />,
    );
    expect(screen.getByText("الان چه چیزی باید یاد بگیرم؟")).toBeInTheDocument();
    expect(screen.getByText("الان چه چیزی باید اثبات کنم؟")).toBeInTheDocument();
    expect(screen.getByText("هنوز اثبات نشده")).toBeInTheDocument();
    expect(screen.getByText("هنوز شروع نشده")).toBeInTheDocument();
    expect(screen.getByText("جلسه بعدی ثبت نشده است.")).toBeInTheDocument();
  });

  it("does not infer weakness from empty learning and proof data", () => {
    render(
      <CandidateHome
        data={{
          journey: { track: "PRODUCT_MANAGER", state: "ACTIVE" },
          cohort: { id: "cohort-1", name: "PM Flag Cohort" },
          current_wave: { code: "WAVE_1", name: "Think & Own" },
          what_to_learn: [],
          what_to_prove: [],
          upcoming_sessions: [],
          learning_tasks: [],
          open_missions: [],
          profile_summary: { status: "UNPROVEN" },
          processing_states: [],
        }}
      />,
    );
    expect(screen.getByText("در جریان")).toBeInTheDocument();
    expect(screen.getByText("هنوز برنامه یادگیری قابل‌نمایشی ثبت نشده است.")).toBeInTheDocument();
    expect(screen.getByText(/نبود داده به معنای ضعف نیست/)).toBeInTheDocument();
  });

  it("never marks an unknown pre-work status as completed", () => {
    const data = {
      journey: { track: "PRODUCT_MANAGER", state: "ACTIVE" },
      cohort: { id: "cohort-1", name: "PM Flag Cohort" },
      current_wave: { code: "WAVE_1", name: "Think & Own" },
      what_to_learn: [],
      what_to_prove: [],
      upcoming_sessions: [],
      learning_tasks: [
        { id: "unit-1", task_type: "PRE_WORK", title: "جلسه", status: "UNRECOGNIZED", body: "مطالعه" },
      ],
      open_missions: [],
      profile_summary: { status: "UNPROVEN" },
      processing_states: [],
    };
    render(<CandidateHome data={data as unknown as import("../api/client").CandidateHomeResponse} />);
    expect(screen.getByText(/وضعیت فعالیت نیازمند بررسی است/)).toBeInTheDocument();
    expect(screen.queryByText("این فعالیت یادگیری تکمیل شده است.")).not.toBeInTheDocument();
  });
});
