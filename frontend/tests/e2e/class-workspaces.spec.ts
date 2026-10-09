import { expect, test, type Page } from "@playwright/test";

// These IDs belong to backend/app/seed.py's ephemeral development fixture.
// This suite checks actual FastAPI + PostgreSQL + Keycloak permissions, not mocked routes.
const CLASS_ID = "00000000-0000-0000-0000-000000000220";
const CANDIDATE_ID = "00000000-0000-0000-0000-000000000101";
const INSTRUCTOR_ID = "00000000-0000-0000-0000-000000000102";
const SESSION_ID = "00000000-0000-0000-0000-000000000241";
const API = process.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function login(page: Page, username: string, password: string) {
  await page.goto("/");
  await page.getByRole("button", { name: "ورود به آکادمی" }).click();
  await page.locator("#username").fill(username);
  await page.locator("#password").fill(password);
  await page.locator("#kc-login").click();
}

async function logout(page: Page) {
  await page.getByRole("button", { name: "خروج" }).click();
  await expect(page.getByRole("button", { name: "ورود به آکادمی" })).toBeVisible();
  await page.context().clearCookies();
}

async function tokenForCurrentUser(page: Page): Promise<string> {
  const token = await page.evaluate(() => {
    for (const storage of [window.sessionStorage, window.localStorage]) {
      for (let i = 0; i < storage.length; i += 1) {
        const raw = storage.getItem(storage.key(i) ?? "");
        if (!raw) continue;
        try {
          const value = JSON.parse(raw) as { access_token?: unknown };
          if (typeof value.access_token === "string" && value.access_token) {
            return value.access_token;
          }
        } catch {
          // Ignore unrelated OIDC/browser entries.
        }
      }
    }
    return null;
  });
  if (!token) throw new Error("Live OIDC access token not found");
  return token;
}

test("P23-12: live role-isolated class report and human-only attendance", async ({ page }) => {
  test.setTimeout(180_000);
  const passwords = {
    candidate: process.env.PARCHAM_DEV_CANDIDATE_PASSWORD,
    instructor: process.env.PARCHAM_DEV_INSTRUCTOR_PASSWORD,
    assessor: process.env.PARCHAM_DEV_ASSESSOR_PASSWORD,
    admin: process.env.PARCHAM_DEV_ADMIN_PASSWORD,
  };
  if (Object.values(passwords).some((value) => !value)) {
    throw new Error("All four ephemeral OIDC development user passwords are required");
  }

  // Candidate sees own learning context, never an inferred absence or formal proof.
  await login(page, "candidate", passwords.candidate!);
  const candidateWorkspace = page.getByTestId("candidate-report-workspace");
  await expect(candidateWorkspace).toBeVisible();
  await expect(candidateWorkspace.getByLabel("انتخاب کلاس")).toHaveValue(CLASS_ID);
  await expect(candidateWorkspace.getByText("حضور و غیاب هنوز ثبت نشده").first()).toBeVisible();
  const candidateCard = candidateWorkspace.locator(".report-subject-card").first();
  await expect(candidateCard).toContainText("Ownership & Accountability");
  await expect(candidateCard).toContainText("وضعیت معتبر در این کارنامه ارائه نشده است.");
  await expect(candidateWorkspace).not.toContainText("معدل");
  const candidateToken = await tokenForCurrentUser(page);
  const ownReport = await page.request.get(
    `${API}/api/v1/class-offerings/${CLASS_ID}/report-cards/${CANDIDATE_ID}`,
    { headers: { Authorization: `Bearer ${candidateToken}` } },
  );
  expect(ownReport.status()).toBe(200);
  const ownSubjects = (await ownReport.json()) as {
    person_id: string;
    subjects: Array<{ proof_state: string | null }>;
  };
  expect(ownSubjects.person_id).toBe(CANDIDATE_ID);
  expect(ownSubjects.subjects.length).toBeGreaterThan(0);
  expect(ownSubjects.subjects.every((subject) => subject.proof_state === null)).toBe(true);
  const anotherPersonReport = await page.request.get(
    `${API}/api/v1/class-offerings/${CLASS_ID}/report-cards/${INSTRUCTOR_ID}`,
    { headers: { Authorization: `Bearer ${candidateToken}` } },
  );
  expect(anotherPersonReport.status()).toBe(404);
  await logout(page);

  // An ASSESSOR role is not a class assignment. Existing formal-Evidence
  // access must not be repurposed as Academy roster/report/activity authority.
  await login(page, "assessor", passwords.assessor!);
  await expect(page.getByText("فضای ارزیاب Evidence")).toBeVisible();
  await expect(page.getByTestId("candidate-report-workspace")).toHaveCount(0);
  await expect(page.getByTestId("instructor-class-workspace")).toHaveCount(0);
  await expect(page.getByTestId("admin-academy-operations")).toHaveCount(0);
  const assessorToken = await tokenForCurrentUser(page);
  for (const path of [
    `/class-offerings/${CLASS_ID}/roster`,
    `/class-offerings/${CLASS_ID}/activity`,
    `/class-offerings/${CLASS_ID}/report-cards/${CANDIDATE_ID}`,
  ]) {
    const response = await page.request.get(`${API}/api/v1${path}`, {
      headers: { Authorization: `Bearer ${assessorToken}` },
    });
    expect(response.status(), `Assessor must not read ${path}`).toBe(404);
  }
  const assessorAdmin = await page.request.get(`${API}/api/v1/admin/academy/cohorts`, {
    headers: { Authorization: `Bearer ${assessorToken}` },
  });
  expect(assessorAdmin.status()).toBe(403);
  await logout(page);

  // Instructor observes the assigned class and its recorded/missing attendance,
  // but cannot use the admin-only attendance mutation endpoint.
  await login(page, "instructor", passwords.instructor!);
  const instructorWorkspace = page.getByTestId("instructor-class-workspace");
  await expect(instructorWorkspace).toBeVisible();
  await expect(instructorWorkspace.getByLabel("کلاس تخصیص‌یافته")).toHaveValue(CLASS_ID);
  await expect(instructorWorkspace.getByText("ثبت نشده؛ به معنی غیبت نیست").first()).toBeVisible();
  await expect(instructorWorkspace.getByRole("button", { name: "ثبت حاضر" })).toHaveCount(0);
  const instructorToken = await tokenForCurrentUser(page);
  const forbiddenMutation = await page.request.post(
    `${API}/api/v1/sessions/${SESSION_ID}/attendance/${CANDIDATE_ID}`,
    {
      headers: { Authorization: `Bearer ${instructorToken}` },
      data: { status: "PRESENT", expected_version: 0, idempotency_key: crypto.randomUUID() },
    },
  );
  expect(forbiddenMutation.status()).toBe(403);
  await logout(page);

  // Only Academy Admin records PRESENT through the actual browser command.
  await login(page, "academy-admin", passwords.admin!);
  const adminWorkspace = page.getByTestId("admin-academy-operations");
  await expect(adminWorkspace).toBeVisible();
  await expect(adminWorkspace.getByLabel("کلاس واقعی")).toHaveValue(CLASS_ID);
  await expect(adminWorkspace.getByLabel("جلسه کلاس")).toHaveValue(SESSION_ID);
  const row = adminWorkspace.locator(".admin-ops-attendance-row").filter({
    hasText: CANDIDATE_ID,
  });
  await expect(row.locator("span").nth(1)).toHaveText("ثبت نشده؛ غیبت محسوب نمی‌شود");
  const adminToken = await tokenForCurrentUser(page);
  await row.getByRole("button", { name: "ثبت حاضر" }).click();
  await expect(row.locator("span").nth(1)).toHaveText("حاضر");

  // Replay with a NEW key but old version must fail rather than overwrite the human record.
  const stale = await page.request.post(
    `${API}/api/v1/sessions/${SESSION_ID}/attendance/${CANDIDATE_ID}`,
    {
      headers: { Authorization: `Bearer ${adminToken}` },
      data: { status: "ABSENT", expected_version: 0, idempotency_key: crypto.randomUUID() },
    },
  );
  expect(stale.status()).toBe(409);
  expect((await stale.json()).code).toBe("ATTENDANCE_VERSION_CONFLICT");
  await expect(row.locator("span").nth(1)).toHaveText("حاضر");
  await logout(page);

  // Candidate must see the exact human-recorded attendance in the same class,
  // without interpreting it as formal ProofState or automatic progression.
  await login(page, "candidate", passwords.candidate!);
  const updatedReport = page.getByTestId("candidate-report-workspace");
  await expect(updatedReport).toBeVisible();
  await expect(updatedReport.getByText("حاضر", { exact: true })).toBeVisible();
  await expect(updatedReport.locator(".report-subject-card").first()).toContainText(
    "وضعیت معتبر در این کارنامه ارائه نشده است.",
  );
});
