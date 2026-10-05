/**
 * Bootstrap declaration. CI regenerates this file from FastAPI OpenAPI.
 */
export interface paths {
  "/api/v1/me": {
    get: { responses: { 200: { content: { "application/json": {
      person_id: string; organization_context_id: string; roles: string[];
    } } } } };
  };
  "/api/v1/capabilities": {
    get: { responses: { 200: { content: { "application/json": Array<{
      id: string; code: string; version_id: string; version_number: number;
      name: string; definition: string; status: string;
    }> } } } };
  };
  "/api/v1/studio/mission-templates": {
    get: { responses: { 200: { content: { "application/json": MissionTemplateResponse[] } } } };
    post: {
      requestBody: { content: { "application/json": MissionTemplateCreate } };
      responses: { 201: { content: { "application/json": MissionTemplateResponse } } };
    };
  };
  "/api/v1/studio/mission-templates/{template_id}/versions": {
    post: {
      parameters: { path: { template_id: string } };
      requestBody: { content: { "application/json": MissionTemplateCreate & { base_version_id: string } } };
      responses: { 201: { content: { "application/json": MissionVersionResponse } } };
    };
  };
  "/api/v1/studio/mission-versions/{version_id}/validate-definition": {
    post: {
      parameters: { path: { version_id: string } };
      responses: { 200: { content: { "application/json": MissionValidationResponse } } };
    };
  };
  "/api/v1/studio/mission-versions/{version_id}/pilot": MissionTransitionPath;
  "/api/v1/studio/mission-versions/{version_id}/mark-validated": MissionTransitionPath;
  "/api/v1/studio/mission-versions/{version_id}/activate": MissionTransitionPath;
  "/api/v1/studio/mission-versions/{version_id}/retire": MissionTransitionPath;
  "/api/v1/studio/mission-assignment-candidates": {
    get: { responses: { 200: { content: { "application/json": MissionAssignmentCandidate[] } } } };
  };
  "/api/v1/studio/mission-assignments": {
    get: { responses: { 200: { content: { "application/json": MissionAssignmentSummary[] } } } };
  };
  "/api/v1/mission-assignments": {
    post: {
      requestBody: { content: { "application/json": MissionAssignmentCreate } };
      responses: { 201: { content: { "application/json": MissionAssignmentSummary } } };
    };
  };
  "/api/v1/missions/active": {
    get: { responses: { 200: { content: { "application/json": MissionCatalogItem[] } } } };
  };
  "/api/v1/me/mission-instances": {
    get: { responses: { 200: { content: { "application/json": MissionInstanceResponse[] } } } };
  };
  "/api/v1/missions/{version_id}/instances": {
    post: {
      parameters: { path: { version_id: string } };
      requestBody: { content: { "application/json": {
        assignment_id: string; idempotency_key: string;
      } } };
      responses: { 201: { content: { "application/json": MissionInstanceResponse } } };
    };
  };
  "/api/v1/mission-instances/{instance_id}": {
    get: {
      parameters: { path: { instance_id: string } };
      responses: { 200: { content: { "application/json": MissionInstanceResponse } } };
    };
  };
  "/api/v1/mission-instances/{instance_id}/actions": {
    post: {
      parameters: { path: { instance_id: string } };
      requestBody: { content: { "application/json": MissionActionCreate } };
      responses: { 200: { content: { "application/json": MissionInstanceResponse } } };
    };
  };
  "/api/v1/me/candidate-home": {
    get: { responses: { 200: { content: { "application/json": CandidateHome } } } };
  };
  "/api/v1/me/instructor-home": {
    get: { responses: { 200: { content: { "application/json": InstructorHome } } } };
  };
  "/api/v1/learning-units/{learning_unit_id}/start": {
    post: {
      parameters: { path: { learning_unit_id: string } };
      responses: { 200: { content: { "application/json": unknown } } };
    };
  };
  "/api/v1/learning-units/{learning_unit_id}/complete": {
    post: {
      parameters: { path: { learning_unit_id: string } };
      responses: { 200: { content: { "application/json": unknown } } };
    };
  };
  "/api/v1/practice-units/{learning_unit_id}/attempts": {
    post: {
      parameters: { path: { learning_unit_id: string } };
      requestBody: { content: { "application/json": { response_text: string } } };
      responses: { 201: { content: { "application/json": unknown } } };
    };
  };
  "/api/v1/practice-attempts/{practice_attempt_id}/feedback": {
    post: {
      parameters: { path: { practice_attempt_id: string } };
      requestBody: { content: { "application/json": { feedback_text: string } } };
      responses: { 201: { content: { "application/json": unknown } } };
    };
  };
  "/api/v1/assignments/{assignment_id}/submissions": {
    post: {
      parameters: { path: { assignment_id: string } };
      requestBody: { content: { "application/json": { content_text: string } } };
      responses: { 201: { content: { "application/json": unknown } } };
    };
  };
  "/api/v1/submissions/{submission_id}/feedback": {
    post: {
      parameters: { path: { submission_id: string } };
      requestBody: { content: { "application/json": { feedback_text: string } } };
      responses: { 201: { content: { "application/json": unknown } } };
    };
  };
}
export interface CandidateHome {
  journey: { track: string; state: string };
  cohort: { id: string; name: string };
  current_wave: { code: string; name: string };
  upcoming_sessions: SessionSummary[];
  what_to_learn: Array<{
    capability_version_id: string; name: string; learning_state: string; next_session?: SessionSummary | null;
  }>;
  what_to_prove: Array<{ capability_version_id: string; name: string; proof_state: string }>;
  learning_tasks: LearningTask[];
  open_missions: unknown[];
  profile_summary: { status: string };
  processing_states: unknown[];
}
export interface InstructorHome {
  assigned_cohort: { id: string; name: string };
  assigned_classes: Array<{ id: string; title: string }>;
  upcoming_sessions: SessionSummary[];
  candidate_count: number;
  capability_focus: string;
  current_wave: { code: string; name: string };
  learning_units: Array<{ id: string; title: string; phase: string; unit_type: string; practice_kind?: string | null; body: string }>;
  assignments: Array<{ id: string; title: string; instructions: string; due_at?: string | null; status: string }>;
  practice_attempts: Array<{
    id: string; learning_unit_id: string; practice_title: string; candidate_id: string;
    candidate_name: string; attempt_number: number; replay_of_attempt_id?: string | null;
    response_text: string; status: string; feedback_text?: string | null;
    feedback_history: PracticeFeedbackHistoryItem[];
  }>;
  submissions: Array<{
    id: string; assignment_id: string; assignment_title: string; candidate_id: string;
    candidate_name: string; content_text: string; status: string; feedback_text?: string | null;
  }>;
}
export interface LearningTask {
  id: string;
  task_type: string;
  title: string;
  practice_kind?: string | null;
  class_offering_id: string;
  capability_version_id: string;
  status: string;
  body: string;
  due_at?: string | null;
  submission_id?: string | null;
  feedback_text?: string | null;
  replay_available?: boolean;
  practice_attempts?: CandidatePracticeAttempt[];
}
export interface PracticeFeedbackHistoryItem {
  id: string;
  feedback_text: string;
  created_at: string;
}
export interface CandidatePracticeAttempt {
  id: string;
  attempt_number: number;
  replay_of_attempt_id?: string | null;
  response_text: string;
  status: string;
  submitted_at: string;
  feedback_history: PracticeFeedbackHistoryItem[];
}
export interface SessionSummary {
  session_id: string;
  title: string;
  starts_at: string;
  ends_at: string;
  delivery_mode: string;
}

export interface MissionTransitionPath {
  post: {
    parameters: { path: { version_id: string } };
    requestBody: { content: { "application/json": { expected_version: number } } };
    responses: { 200: { content: { "application/json": MissionVersionResponse } } };
  };
}
export interface MissionTemplateCreate {
  code: string;
  name: string;
  title: string;
  purpose: string;
  objective: string;
  primary_capability_version_id: string;
  mission_mode: "LEARN" | "PRACTICE" | "ASSESSMENT" | "REAL_PROJECT";
  difficulty: "D1" | "D2" | "D3" | "D4" | "D5";
  world_context: Record<string, unknown>;
  actors: Array<{ name: string; goal: string; authority: string }>;
  information_items: Array<{
    label: string;
    access: "DEFAULT" | "DISCOVERABLE" | "RESTRICTED" | "UNAVAILABLE" | "NOISY";
    content: string;
  }>;
  constraints: Array<{ label: string; description: string }>;
  decision_points: Array<{ code: string; prompt: string }>;
  consequence_rules: Array<{ trigger: string; effect: string }>;
  evidence_opportunities: Array<{ behaviour: string; source: string }>;
  replay_policy: Record<string, unknown>;
  safety_policy: Record<string, unknown>;
}
export interface MissionValidationResponse {
  valid: boolean;
  errors: string[];
  warnings: string[];
}
export interface MissionTemplateResponse {
  id: string;
  code: string;
  name: string;
  versions: MissionVersionResponse[];
}
export interface MissionVersionResponse {
  id: string;
  template_id: string;
  aggregate_version: number;
  version_number: number;
  status: string;
  title: string;
  purpose: string;
  objective: string;
  primary_capability_version_id: string;
  mission_mode: string;
  difficulty: string;
  world_context: Record<string, unknown>;
  actors: Array<Record<string, unknown>>;
  information_items: Array<Record<string, unknown>>;
  constraints: Array<Record<string, unknown>>;
  decision_points: Array<Record<string, unknown>>;
  consequence_rules: Array<Record<string, unknown>>;
  evidence_opportunities: Array<Record<string, unknown>>;
  replay_policy: Record<string, unknown>;
  safety_policy: Record<string, unknown>;
  created_at: string;
  validated_at?: string | null;
  activated_at?: string | null;
  retired_at?: string | null;
}

export interface MissionCatalogItem {
  assignment_id: string;
  assignment_status: string;
  version_id: string;
  template_id: string;
  code: string;
  title: string;
  purpose: string;
  difficulty: string;
  decision_points: Array<Record<string, unknown>>;
  information_options: Array<{ label?: string; access?: string }>;
  decision_options: Array<{ code?: string; label?: string }>;
}
export interface MissionRuntimeEvent {
  id: string;
  sequence_number: number;
  event_type: string;
  source: string;
  visibility: string;
  payload: Record<string, unknown>;
  world_version_before: number;
  world_version_after: number;
  occurred_at: string;
}
export interface MissionObservation {
  id: string;
  source_event_id: string;
  sequence_number: number;
  observation_type: string;
  factual_statement: string;
  payload: Record<string, unknown>;
  occurred_at: string;
}
export interface MissionInstanceResponse {
  id: string;
  version: number;
  assignment_id?: string | null;
  mission_version_id: string;
  template_id: string;
  mission_code: string;
  title: string;
  status: string;
  world_state: Record<string, unknown>;
  world_state_version: number;
  decision_points: Array<Record<string, unknown>>;
  information_options: Array<{ label?: string; access?: string }>;
  decision_options: Array<{ code?: string; label?: string }>;
  disclosed_information: Array<{ label?: string; content?: string; access?: string }>;
  audit_events: MissionRuntimeEvent[];
  observations: MissionObservation[];
  created_at: string;
  started_at?: string | null;
  completed_at?: string | null;
}
export interface MissionActionCreate {
  action_type:
    | "REQUEST_INFORMATION"
    | "COMMUNICATE"
    | "DECIDE"
    | "ESCALATE"
    | "DELEGATE"
    | "CHANGE_SCOPE"
    | "ALLOCATE_RESOURCE"
    | "RUN_EXPERIMENT"
    | "NO_ACTION";
  target?: string | null;
  payload: Record<string, unknown>;
  reasoning: string;
  confidence: number;
  expected_world_version: number;
  idempotency_key: string;
  resource_cost: Record<string, unknown>;
  mode: string;
  provenance: Record<string, unknown>;
}

export interface MissionAssignmentCandidate {
  id: string;
  display_name: string;
}
export interface MissionAssignmentCreate {
  candidate_id: string;
  mission_version_id: string;
  assignment_reason: string;
  idempotency_key: string;
}
export interface MissionAssignmentSummary {
  id: string;
  version: number;
  candidate_id: string;
  candidate_name: string;
  mission_version_id: string;
  mission_code: string;
  mission_title: string;
  status: string;
  assignment_reason: string;
  created_at: string;
  started_at?: string | null;
  completed_at?: string | null;
}
