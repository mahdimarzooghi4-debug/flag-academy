/**
 * Bootstrap declaration. CI regenerates this file from FastAPI OpenAPI.
 */
export interface paths {
  "/api/v1/me": {
    get: { responses: { 200: { content: { "application/json": {
      person_id: string; organization_context_id: string; roles: string[];
    } } } } };
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
