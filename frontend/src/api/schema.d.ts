/**
 * Bootstrap declaration. CI regenerates this file from FastAPI OpenAPI.
 */
export interface paths {
  "/api/v1/me": {
    get: {
      responses: {
        200: {
          content: {
            "application/json": {
              person_id: string;
              organization_context_id: string;
              roles: string[];
            };
          };
        };
      };
    };
  };
  "/api/v1/me/candidate-home": {
    get: {
      responses: {
        200: {
          content: {
            "application/json": CandidateHome;
          };
        };
      };
    };
  };
  "/api/v1/me/instructor-home": {
    get: {
      responses: {
        200: {
          content: {
            "application/json": InstructorHome;
          };
        };
      };
    };
  };
}
export interface CandidateHome {
  journey?: { track?: string; state?: string };
  cohort?: { id?: string; name?: string };
  current_wave?: { code?: string; name?: string };
  upcoming_sessions?: SessionSummary[];
  what_to_learn?: Array<{
    capability_version_id?: string;
    name?: string;
    learning_state?: string;
    next_session?: SessionSummary;
  }>;
  what_to_prove?: Array<{
    capability_version_id?: string;
    name?: string;
    proof_state?: string;
  }>;
  learning_tasks?: unknown[];
  open_missions?: unknown[];
  profile_summary?: { status?: string };
  processing_states?: unknown[];
}
export interface InstructorHome {
  assigned_cohort?: { id?: string; name?: string };
  assigned_classes?: Array<{ id?: string; title?: string }>;
  upcoming_sessions?: SessionSummary[];
  candidate_count?: number;
  capability_focus?: string;
  current_wave?: { code?: string; name?: string };
}
export interface SessionSummary {
  session_id?: string;
  title?: string;
  starts_at?: string;
  ends_at?: string;
  delivery_mode?: string;
}
