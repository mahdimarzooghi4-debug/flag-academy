import createClient from "openapi-fetch";
import type { paths } from "./schema";

export function makeApi(accessToken: string) {
  return createClient<paths>({
    baseUrl: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000",
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });
}

export type MeResponse =
  paths["/api/v1/me"]["get"]["responses"]["200"]["content"]["application/json"];
export type CandidateHomeResponse =
  paths["/api/v1/me/candidate-home"]["get"]["responses"]["200"]["content"]["application/json"];
export type InstructorHomeResponse =
  paths["/api/v1/me/instructor-home"]["get"]["responses"]["200"]["content"]["application/json"];
