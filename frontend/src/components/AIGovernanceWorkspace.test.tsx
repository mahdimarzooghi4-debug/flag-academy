import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  AIGovernanceWorkspace,
  type AIGovernanceData,
} from "./AIGovernanceWorkspace";

const data: AIGovernanceData = {
  organization_context_id: "30000000-0000-0000-0000-000000000001",
  dataset_versions: [
    {
      id: "10000000-0000-0000-0000-000000000001",
      dataset_id: "10000000-0000-0000-0000-000000000010",
      dataset_name: "governed-learning",
      purpose: "TRAINING",
      version_number: 3,
      dataset_digest: "a".repeat(64),
      item_count: 12,
      created_at: "2026-10-07T12:00:00Z",
    },
  ],
  training_runs: [
    {
      id: "20000000-0000-0000-0000-000000000001",
      dataset_version_id: "10000000-0000-0000-0000-000000000001",
      model_family: "Gemma 4 12B Unified",
      state: "SUCCEEDED",
      requested_at: "2026-10-07T12:10:00Z",
      model_artifact_id: "22000000-0000-0000-0000-000000000001",
      model_version_id: "23000000-0000-0000-0000-000000000001",
    },
  ],
  model_versions: [
    {
      id: "23000000-0000-0000-0000-000000000001",
      training_run_id: "20000000-0000-0000-0000-000000000001",
      dataset_version_id: "10000000-0000-0000-0000-000000000001",
      model_family: "Gemma 4 12B Unified",
      semantic_version: "candidate-1",
      attestation_sha256: "b".repeat(64),
      attestation_byte_size: 1024,
      attested_at: "2026-10-07T12:20:00Z",
      created_at: "2026-10-07T12:20:00Z",
    },
  ],
  evaluation_runs: [
    {
      id: "30000000-0000-0000-0000-000000000010",
      model_version_id: "23000000-0000-0000-0000-000000000001",
      evaluation_dataset_version_id: "10000000-0000-0000-0000-000000000002",
      evaluation_policy_key: "offline-evaluation",
      evaluation_policy_version: "v1",
      state: "SUCCEEDED",
      requested_at: "2026-10-07T12:30:00Z",
      result_digest: "c".repeat(64),
      result_byte_size: 512,
      result_attested_at: "2026-10-07T12:35:00Z",
    },
  ],
  promotion_decisions: [
    {
      id: "40000000-0000-0000-0000-000000000001",
      model_version_id: "23000000-0000-0000-0000-000000000001",
      evaluation_run_id: "30000000-0000-0000-0000-000000000010",
      reviewer_id: "50000000-0000-0000-0000-000000000001",
      rationale: "شواهد بررسی شد و مجوز انسانی ثبت شد.",
      decision: "APPROVED",
      target_environment: "PRODUCTION",
      prior_active_model_version_id: null,
      decided_at: "2026-10-07T12:40:00Z",
    },
  ],
};

describe("AIGovernanceWorkspace", () => {
  it("renders the governed lineage without runtime activation controls", () => {
    render(<AIGovernanceWorkspace data={data} />);

    expect(screen.getByText("کنترل‌پلین هوش مصنوعی پرچم")).toBeInTheDocument();
    expect(screen.getAllByText("Gemma 4 12B Unified").length).toBeGreaterThan(0);
    expect(screen.getByText("OFFLINE EVALUATION")).toBeInTheDocument();
    expect(screen.getAllByText("APPROVED").length).toBeGreaterThan(0);
    expect(
      screen.getByText(
        "مجوز انسانی ثبت شده است؛ این رکورد به‌تنهایی Runtime را فعال نمی‌کند.",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });
});
