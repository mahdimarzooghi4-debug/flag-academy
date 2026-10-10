import { expect, test, type Page } from "@playwright/test";

// These IDs belong to backend/app/seed.py's ephemeral development fixture.
// This suite checks actual FastAPI + PostgreSQL + Keycloak permissions, not mocked routes.
const CLASS_ID = "00000000-0000-0000-0000-000000000220";
const CANDIDATE_ID = "00000000-0000-0000-0000-000000000101";
const ASSESSOR_ID = "00000000-0000-0000-0000-000000000104";
const INDEPENDENT_REVIEWER_ID = "00000000-0000-0000-0000-000000000105";
const INSTRUCTOR_ID = "00000000-0000-0000-0000-000000000102";
const SESSION_ID = "00000000-0000-0000-0000-000000000241";
// Ephemeral in-progress Session created by scripts/observation_ci_session.py ONLY in CI.
const OBSERVATION_SESSION_ID = "00000000-0000-0000-0000-000000000243";
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
  // OIDC rehydration can lag behind the protected workspace rendering.
  // Wait for real browser storage instead of assuming immediate persistence.
  const handle = await page.waitForFunction(() => {
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
  }, undefined, { timeout: 15_000 });
  const token = await handle.jsonValue();
  if (typeof token !== "string" || !token) {
    throw new Error("Live OIDC access token not found");
  }
  return token;
}

test("P23-12: live role-isolated class report and human-only attendance", async ({ page }) => {
  test.setTimeout(240_000);
  const passwords = {
    candidate: process.env.PARCHAM_DEV_CANDIDATE_PASSWORD,
    instructor: process.env.PARCHAM_DEV_INSTRUCTOR_PASSWORD,
    assessor: process.env.PARCHAM_DEV_ASSESSOR_PASSWORD,
    reviewer: process.env.PARCHAM_DEV_SOURCE_REVIEWER_PASSWORD,
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
  const unassignedClassView = page.getByTestId("assessor-class-workspace");
  await expect(unassignedClassView.getByText("اکنون مأموریت معتبر کلاسی ندارید.")).toBeVisible();
  await expect(unassignedClassView.getByLabel("کلاس منصوب‌شده")).toHaveCount(0);
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
  const preGrantObservation = await page.request.get(
    `${API}/api/v1/class-offerings/${CLASS_ID}/observations`, {
      headers: { Authorization: `Bearer ${assessorToken}` },
    },
  );
  expect(preGrantObservation.status()).toBe(404);
  const assessorAdmin = await page.request.get(`${API}/api/v1/admin/academy/cohorts`, {
    headers: { Authorization: `Bearer ${assessorToken}` },
  });
  expect(assessorAdmin.status()).toBe(403);
  // The Seed learning approval surface remains Academy-Admin-only.
  const forbiddenSeedPreview = await page.request.get(
    `${API}/api/v1/admin/ai/seed-learning/decision-making-v1`,
    { headers: { Authorization: `Bearer ${assessorToken}` } },
  );
  expect(forbiddenSeedPreview.status()).toBe(403);
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
  const forbiddenObservation = await page.request.post(
    `${API}/api/v1/class-offerings/${CLASS_ID}/observations`, {
      headers: { Authorization: `Bearer ${instructorToken}` },
      data: { session_id: OBSERVATION_SESSION_ID, candidate_person_id: CANDIDATE_ID,
        observed_at: new Date().toISOString(), observed_fact: "Instructor must not impersonate Assessor",
        idempotency_key: crypto.randomUUID() },
    },
  );
  expect(forbiddenObservation.status()).toBe(403);
  const forbiddenMutation = await page.request.post(
    `${API}/api/v1/sessions/${SESSION_ID}/attendance/${CANDIDATE_ID}`,
    {
      headers: { Authorization: `Bearer ${instructorToken}` },
      data: { status: "PRESENT", expected_version: 0, idempotency_key: crypto.randomUUID() },
    },
  );
  expect(forbiddenMutation.status()).toBe(403);

  // P23-10: a real Instructor may submit versioned, UNPUBLISHED knowledge Drafts.
  // A Draft must never become approved AI knowledge, Evidence or training data.
  const knowledgeSourceKey = `decision-case-${crypto.randomUUID().slice(0, 8)}`;
  const knowledgeRequest = {
    source_key: knowledgeSourceKey,
    content_text: "Teach tradeoffs, acknowledge uncertainty, and separate outcomes from decision quality.",
    idempotency_key: crypto.randomUUID(),
  };
  const instructorDraft = await page.request.post(`${API}/api/v1/knowledge/draft-versions`, {
    headers: { Authorization: `Bearer ${instructorToken}` },
    data: knowledgeRequest,
  });
  expect(instructorDraft.status()).toBe(201);
  const draftVersion = (await instructorDraft.json()) as {
    source_id: string; source_version_id: string; version_number: number;
    source_key: string; status: string; classification: string; content_digest: string;
  };
  expect(draftVersion.source_key).toBe(knowledgeSourceKey);
  expect(draftVersion.version_number).toBe(1);
  expect(draftVersion.status).toBe("DRAFT");
  expect(draftVersion.classification).toBe("INTERNAL");
  expect(draftVersion.content_digest).toMatch(/^[0-9a-f]{64}$/);
  const replayDraft = await page.request.post(`${API}/api/v1/knowledge/draft-versions`, {
    headers: { Authorization: `Bearer ${instructorToken}` },
    data: knowledgeRequest,
  });
  expect(replayDraft.status()).toBe(201);
  expect((await replayDraft.json()).source_version_id).toBe(draftVersion.source_version_id);
  const conflictingDraft = await page.request.post(`${API}/api/v1/knowledge/draft-versions`, {
    headers: { Authorization: `Bearer ${instructorToken}` },
    data: { ...knowledgeRequest, content_text: "Changed content under the same key" },
  });
  expect(conflictingDraft.status()).toBe(409);
  const nextDraft = await page.request.post(`${API}/api/v1/knowledge/draft-versions`, {
    headers: { Authorization: `Bearer ${instructorToken}` },
    data: { ...knowledgeRequest, content_text: "Revised teacher-authored draft", idempotency_key: crypto.randomUUID() },
  });
  expect(nextDraft.status()).toBe(201);
  expect((await nextDraft.json()).version_number).toBe(2);
  const myDrafts = await page.request.get(`${API}/api/v1/knowledge/my-drafts`, {
    headers: { Authorization: `Bearer ${instructorToken}` },
  });
  expect(myDrafts.status()).toBe(200);
  const myDraftPage = (await myDrafts.json()) as {
    items: Array<{ source_key: string; status: string; version_number: number }>;
  };
  expect(myDraftPage.items.filter((x) => x.source_key === knowledgeSourceKey)
    .map((x) => x.version_number)).toEqual([1, 2]);
  expect(JSON.stringify(myDraftPage)).not.toContain("content_text");
  await logout(page);

  // Only Academy Admin records PRESENT through the actual browser command.
  await login(page, "academy-admin", passwords.admin!);
  const adminWorkspace = page.getByTestId("admin-academy-operations");
  await expect(adminWorkspace).toBeVisible();
  const seedPanel = page.getByTestId("seed-learning-approval-workspace");
  await expect(seedPanel.getByText("تأیید انسانی دیتای اولیه تصمیم‌گیری")).toBeVisible();
  await expect(seedPanel.getByTestId("seed-learning-metadata")).toContainText(
    "docs/ai/seed/decision-making-v1.jsonl",
  );
  const exactDigest = await seedPanel.getByTestId("seed-learning-sha256").innerText();
  expect(exactDigest).toMatch(/^[0-9a-f]{64}$/);
  await expect(seedPanel.getByRole("button", {
    name: "ثبت مجوز انسانی استفاده از Seed در دیتاست",
  })).toBeDisabled();
  // E2E only previews: there is NO implicit human AI-learning approval in CI.
  await expect(adminWorkspace.getByLabel("کلاس واقعی")).toHaveValue(CLASS_ID);
  await adminWorkspace.getByLabel("جلسه کلاس").selectOption(SESSION_ID);
  await expect(adminWorkspace.getByLabel("جلسه کلاس")).toHaveValue(SESSION_ID);
  const row = adminWorkspace.locator(".admin-ops-attendance-row").filter({
    hasText: CANDIDATE_ID,
  });
  await expect(row.locator("span").nth(1)).toHaveText("ثبت نشده؛ غیبت محسوب نمی‌شود");
  const adminToken = await tokenForCurrentUser(page);
  const adminDrafts = await page.request.get(`${API}/api/v1/admin/knowledge/draft-versions`, {
    headers: { Authorization: `Bearer ${adminToken}` },
  });
  expect(adminDrafts.status()).toBe(200);
  const draftCatalog = (await adminDrafts.json()) as {
    items: Array<{ source_key: string; status: string; content_digest: string }>;
  };
  expect(draftCatalog.items.filter((x) => x.source_key === knowledgeSourceKey)).toHaveLength(2);
  expect(draftCatalog.items.every((x) => x.status === "DRAFT")).toBe(true);
  expect(JSON.stringify(draftCatalog)).not.toContain("content_text");
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

  // P23-09: REAL admin browser creates a time-bounded Academy-owned grant.
  // This grants only the one class; never Evidence, Gate or a global roster.
  await logout(page);
  await login(page, "academy-admin", passwords.admin!);
  const grantPanel = page.getByTestId("admin-assessor-grants");
  await expect(grantPanel).toBeVisible();
  await expect(grantPanel).toContainText("مأموریتی برای این کلاس ثبت نشده است.");
  const start = new Date(Date.now() - 5 * 60_000).toISOString();
  const end = new Date(Date.now() + 48 * 60 * 60_000).toISOString();
  await grantPanel.getByLabel("شناسه ارزیاب عضو همین سازمان").fill(ASSESSOR_ID);
  await grantPanel.getByLabel("آغاز مأموریت (ISO با منطقه زمانی)").fill(start);
  await grantPanel.getByLabel("پایان مأموریت (ISO با منطقه زمانی)").fill(end);
  await grantPanel.getByRole("button", { name: "ثبت انتصاب با تأیید مدیر" }).click();
  await expect(grantPanel.getByTestId("selected-assessor-grant")).toContainText(ASSESSOR_ID);
  await expect(grantPanel.getByTestId("selected-assessor-grant")).toContainText("لغو نشده");
  await logout(page);

  // Same real OIDC Assessor can read authorized classroom projections ONLY
  // while the mandate is valid; the pre-grant 404 checks above still apply.
  await login(page, "assessor", passwords.assessor!);
  const assignedClassView = page.getByTestId("assessor-class-workspace");
  await expect(assignedClassView.getByLabel("کلاس منصوب‌شده")).toHaveValue(CLASS_ID);
  await expect(assignedClassView.getByLabel("فراگیر کلاس")).toHaveValue(CANDIDATE_ID);
  await expect(assignedClassView.getByText(
    "اثبات رسمی مستقل: داده معتبر مستقل موجود نیست"
  )).toBeVisible();
  await expect(assignedClassView).not.toContainText("معدل");
  const grantedAssessorToken = await tokenForCurrentUser(page);
  for (const path of [
    `/class-offerings/${CLASS_ID}/roster`,
    `/class-offerings/${CLASS_ID}/sessions`,
    `/sessions/${SESSION_ID}/attendance`,
    `/class-offerings/${CLASS_ID}/activity`,
    `/class-offerings/${CLASS_ID}/report-cards/${CANDIDATE_ID}`,
  ]) {
    const result = await page.request.get(`${API}/api/v1${path}`, {
      headers: { Authorization: `Bearer ${grantedAssessorToken}` },
    });
    expect(result.status(), `Assigned Assessor needs scoped GET ${path}`).toBe(200);
  }
  // P23-09C — actual OIDC/FastAPI/PostgreSQL writer, no Evidence admission.
  // This synthetic current Session exists ONLY in the isolated GitHub Actions fixture.
  const observationUrl = `${API}/api/v1/class-offerings/${CLASS_ID}/observations`;
  const observationHeaders = { Authorization: `Bearer ${grantedAssessorToken}` };
  const beforeObservation = await page.request.get(observationUrl, { headers: observationHeaders });
  expect(beforeObservation.status()).toBe(200);
  expect(await beforeObservation.json()).toEqual([]);
  const observationBody = {
    session_id: OBSERVATION_SESSION_ID,
    candidate_person_id: CANDIDATE_ID,
    observed_at: new Date().toISOString(),
    observed_fact: "CI factual classroom observation: learner separated evidence from interpretation.",
    idempotency_key: crypto.randomUUID(),
  };
  // Two concurrent physical HTTP requests use independent DB transactions.
  const [firstObservation, concurrentReplay] = await Promise.all([
    page.request.post(observationUrl, { headers: observationHeaders, data: observationBody }),
    page.request.post(observationUrl, { headers: observationHeaders, data: observationBody }),
  ]);
  expect(firstObservation.status()).toBe(201);
  expect(concurrentReplay.status()).toBe(201);
  const observation = (await firstObservation.json()) as {
    observation_id: string; grant_version: number; observed_at: string;
    recorded_at: string; observer_person_id: string; candidate_person_id: string;
    session_id: string; observed_fact: string;
  };
  expect((await concurrentReplay.json()).observation_id).toBe(observation.observation_id);
  expect(observation.session_id).toBe(OBSERVATION_SESSION_ID);
  expect(observation.candidate_person_id).toBe(CANDIDATE_ID);
  expect(observation.observer_person_id).toBe(ASSESSOR_ID);
  expect(observation.observed_fact).toBe(observationBody.observed_fact);
  expect(new Date(observation.recorded_at).getTime()).toBeGreaterThanOrEqual(
    new Date(observation.observed_at).getTime(),
  );
  const historical = await page.request.get(observationUrl, { headers: observationHeaders });
  expect(historical.status()).toBe(200);
  const history = (await historical.json()) as Array<{ observation_id: string }>;
  expect(history).toHaveLength(1);
  expect(history[0]?.observation_id).toBe(observation.observation_id);
  const conflictingReplay = await page.request.post(observationUrl, {
    headers: observationHeaders,
    data: { ...observationBody, observed_fact: "changed source under the same replay key" },
  });
  expect(conflictingReplay.status()).toBe(409);
  for (const invalid of [
    { ...observationBody, idempotency_key: crypto.randomUUID(), candidate_person_id: ASSESSOR_ID },
    { ...observationBody, idempotency_key: crypto.randomUUID(), session_id: SESSION_ID },
  ]) {
    const bad = await page.request.post(observationUrl, {
      headers: observationHeaders, data: invalid,
    });
    expect([404, 409]).toContain(bad.status());
  }
  const futureObservation = await page.request.post(observationUrl, {
    headers: observationHeaders,
    data: { ...observationBody, observed_at: new Date(Date.now() + 60 * 60_000).toISOString(),
      idempotency_key: crypto.randomUUID() },
  });
  expect(futureObservation.status()).toBe(409);
  const crossClassObservation = await page.request.post(
    `${API}/api/v1/class-offerings/${crypto.randomUUID()}/observations`,
    { headers: observationHeaders, data: { ...observationBody, idempotency_key: crypto.randomUUID() } },
  );
  expect(crossClassObservation.status()).toBe(404);
  const authorCannotReview = await page.request.get(
    `${API}/api/v1/classroom-observations/${observation.observation_id}/review-source`,
    { headers: observationHeaders },
  );
  expect(authorCannotReview.status()).toBe(404);
  // The separate Evidence API has no implicit link to this new Academy source.
  expect(JSON.stringify(observation)).not.toContain("evidence_case_id");

  const assessorStillCannotAdmin = await page.request.get(
    `${API}/api/v1/admin/academy/classes/${CLASS_ID}/assessor-grants`, {
      headers: { Authorization: `Bearer ${grantedAssessorToken}` },
    },
  );
  expect(assessorStillCannotAdmin.status()).toBe(403);
  await logout(page);

  // P23-09C human source review: SECOND real Keycloak identity, scoped to
  // the same class by an independent Admin appointment. No Evidence admission.
  const sourceReviewUrl = `${API}/api/v1/classroom-observations/${observation.observation_id}/review-source`;
  await login(page, "assessor-reviewer", passwords.reviewer!);
  const reviewerUnassignedToken = await tokenForCurrentUser(page);
  const beforeReviewerGrant = await page.request.get(sourceReviewUrl, {
    headers: { Authorization: `Bearer ${reviewerUnassignedToken}` },
  });
  expect(beforeReviewerGrant.status()).toBe(404);
  await logout(page);

  await login(page, "academy-admin", passwords.admin!);
  const adminReviewToken = await tokenForCurrentUser(page);
  const reviewerGrantResponse = await page.request.post(
    `${API}/api/v1/admin/academy/classes/${CLASS_ID}/assessor-grants`, {
      headers: { Authorization: `Bearer ${adminReviewToken}` },
      data: {
        assessor_person_id: INDEPENDENT_REVIEWER_ID,
        starts_at: new Date(Date.now() - 5 * 60_000).toISOString(),
        ends_at: new Date(Date.now() + 48 * 60 * 60_000).toISOString(),
        idempotency_key: crypto.randomUUID(),
      },
    },
  );
  expect(reviewerGrantResponse.status()).toBe(200);
  const reviewerGrant = (await reviewerGrantResponse.json()) as {
    grant_id: string; version: number;
  };
  expect(reviewerGrant.version).toBe(1);
  await logout(page);

  await login(page, "assessor-reviewer", passwords.reviewer!);
  const reviewerToken = await tokenForCurrentUser(page);
  const reviewerHeaders = { Authorization: `Bearer ${reviewerToken}` };
  const reviewerSource = await page.request.get(sourceReviewUrl, { headers: reviewerHeaders });
  expect(reviewerSource.status()).toBe(200);
  const scopedSource = (await reviewerSource.json()) as {
    observation_id: string; observer_person_id: string; candidate_person_id: string;
    source_sha256: string; observed_fact: string;
  };
  expect(scopedSource.observation_id).toBe(observation.observation_id);
  expect(scopedSource.observer_person_id).toBe(ASSESSOR_ID);
  expect(scopedSource.candidate_person_id).toBe(CANDIDATE_ID);
  expect(scopedSource.source_sha256).toMatch(/^[a-f0-9]{64}$/);
  expect(scopedSource.observed_fact).toBe(observationBody.observed_fact);
  const reviewBody = {
    expected_source_sha256: scopedSource.source_sha256,
    decision: "VERIFIED",
    rationale: "Independently reviewed this particular source and authorized classroom interval",
  };
  const [reviewA, reviewB] = await Promise.all([
    page.request.post(sourceReviewUrl, { headers: reviewerHeaders, data: reviewBody }),
    page.request.post(sourceReviewUrl, { headers: reviewerHeaders, data: reviewBody }),
  ]);
  expect(reviewA.status()).toBe(201);
  expect(reviewB.status()).toBe(201);
  const reviewResult = (await reviewA.json()) as {
    review_id: string; reviewer_person_id: string;
    decision: string; source_sha256: string;
  };
  expect((await reviewB.json()).review_id).toBe(reviewResult.review_id);
  expect(reviewResult.reviewer_person_id).toBe(INDEPENDENT_REVIEWER_ID);
  expect(reviewResult.decision).toBe("VERIFIED");
  expect(reviewResult.source_sha256).toBe(scopedSource.source_sha256);
  expect(JSON.stringify(reviewResult)).not.toContain("evidence_case_id");
  const staleSource = await page.request.post(sourceReviewUrl, {
    headers: reviewerHeaders,
    data: { ...reviewBody, expected_source_sha256: "0".repeat(64) },
  });
  expect(staleSource.status()).toBe(409);
  const conflictingSource = await page.request.post(sourceReviewUrl, {
    headers: reviewerHeaders,
    data: { ...reviewBody, decision: "REJECTED" },
  });
  expect(conflictingSource.status()).toBe(409);

  // P23-09C: a human explicitly creates a private, source-pinned Draft only
  // AFTER independent VERIFIED review. Concurrent replay is one EvidenceCase.
  const draftUrl = `${API}/api/v1/classroom-observations/${observation.observation_id}/evidence-draft`;
  const draftCommand = {
    expected_review_id: reviewResult.review_id,
    expected_source_sha256: reviewResult.source_sha256,
    submission_reason: "Explicit human request to open a private Draft for formal later review",
  };
  const [draftA, draftB] = await Promise.all([
    page.request.post(draftUrl, { headers: reviewerHeaders, data: draftCommand }),
    page.request.post(draftUrl, { headers: reviewerHeaders, data: draftCommand }),
  ]);
  expect(draftA.status()).toBe(201);
  expect(draftB.status()).toBe(201);
  const draft = (await draftA.json()) as {
    evidence_case_id: string; status: string; candidate_visible: boolean;
    source_review_id: string; source_observation_id: string; observed_fact: string;
  };
  expect((await draftB.json()).evidence_case_id).toBe(draft.evidence_case_id);
  expect(draft.status).toBe("DRAFT");
  expect(draft.candidate_visible).toBe(false);
  expect(draft.source_review_id).toBe(reviewResult.review_id);
  expect(draft.source_observation_id).toBe(observation.observation_id);
  expect(draft.observed_fact).toBe(observationBody.observed_fact);
  const privateDraftUrl = `${API}/api/v1/classroom-evidence-drafts/${draft.evidence_case_id}`;
  const ownedDraft = await page.request.get(privateDraftUrl, { headers: reviewerHeaders });
  expect(ownedDraft.status()).toBe(200);
  expect((await ownedDraft.json()).evidence_case_id).toBe(draft.evidence_case_id);
  const guessedOtherDraft = await page.request.get(
    `${API}/api/v1/classroom-evidence-drafts/${crypto.randomUUID()}`,
    { headers: reviewerHeaders },
  );
  expect(guessedOtherDraft.status()).toBe(404);
  const authorCannotReadPrivateDraft = await page.request.get(
    privateDraftUrl,
    { headers: { Authorization: `Bearer ${grantedAssessorToken}` } },
  );
  expect(authorCannotReadPrivateDraft.status()).toBe(404);
  const genericDetail = await page.request.get(
    `${API}/api/v1/evidence-cases/${draft.evidence_case_id}`,
    { headers: reviewerHeaders },
  );
  expect(genericDetail.status()).toBe(404);
  const genericList = await page.request.get(
    `${API}/api/v1/evidence-cases`,
    { headers: reviewerHeaders },
  );
  expect(genericList.status()).toBe(200);
  expect(JSON.stringify(await genericList.json())).not.toContain(draft.evidence_case_id);
  for (const changed of [
    { ...draftCommand, expected_source_sha256: "0".repeat(64) },
    { ...draftCommand, expected_review_id: crypto.randomUUID() },
    { ...draftCommand, submission_reason: "Conflicting attempt to rewrite the human reason" },
  ]) {
    const rejected = await page.request.post(draftUrl, {
      headers: reviewerHeaders, data: changed,
    });
    expect(rejected.status()).toBe(409);
  }
  await logout(page);

  await login(page, "academy-admin", passwords.admin!);
  const revokeReviewerToken = await tokenForCurrentUser(page);
  const revokeReviewer = await page.request.post(
    `${API}/api/v1/admin/academy/assessor-grants/${reviewerGrant.grant_id}/revoke`, {
      headers: { Authorization: `Bearer ${revokeReviewerToken}` },
      data: {
        expected_version: reviewerGrant.version,
        reason: "CI verification that review authorization is live only",
        idempotency_key: crypto.randomUUID(),
      },
    },
  );
  expect(revokeReviewer.status()).toBe(200);
  await logout(page);

  await login(page, "assessor-reviewer", passwords.reviewer!);
  const revokedReviewerToken = await tokenForCurrentUser(page);
  const revokedSource = await page.request.get(sourceReviewUrl, {
    headers: { Authorization: `Bearer ${revokedReviewerToken}` },
  });
  expect(revokedSource.status()).toBe(404);
  const revokedDraftRead = await page.request.get(privateDraftUrl, {
    headers: { Authorization: `Bearer ${revokedReviewerToken}` },
  });
  expect(revokedDraftRead.status()).toBe(404);
  const revokedDraftWrite = await page.request.post(draftUrl, {
    headers: { Authorization: `Bearer ${revokedReviewerToken}` },
    data: draftCommand,
  });
  expect(revokedDraftWrite.status()).toBe(404);
  await logout(page);

  // Human revocation closes the same grant immediately without erasing audit.
  await login(page, "academy-admin", passwords.admin!);
  const revocationPanel = page.getByTestId("admin-assessor-grants");
  await expect(revocationPanel.getByTestId("selected-assessor-grant")).toContainText(ASSESSOR_ID);
  await revocationPanel.getByLabel("دلیل تمدید یا لغو").fill("Assignment formally ended");
  await revocationPanel.getByLabel(
    "لغو مأموریت این ارزیاب در همین کلاس را تأیید می‌کنم."
  ).check();
  await revocationPanel.getByRole("button", { name: "لغو مأموریت" }).click();
  await expect(revocationPanel).toContainText("مأموریت لغوشده قابل تمدید نیست.");
  await logout(page);
  await login(page, "assessor", passwords.assessor!);
  const revokedClassView = page.getByTestId("assessor-class-workspace");
  await expect(revokedClassView.getByText("اکنون مأموریت معتبر کلاسی ندارید.")).toBeVisible();
  await expect(revokedClassView.getByLabel("کلاس منصوب‌شده")).toHaveCount(0);
  await expect(revokedClassView).not.toContainText(CANDIDATE_ID);
  const revokedAssessorToken = await tokenForCurrentUser(page);
  const afterRevoke = await page.request.get(
    `${API}/api/v1/class-offerings/${CLASS_ID}/roster`, {
      headers: { Authorization: `Bearer ${revokedAssessorToken}` },
    },
  );
  expect(afterRevoke.status()).toBe(404);
  const revokedObservationRead = await page.request.get(
    `${API}/api/v1/class-offerings/${CLASS_ID}/observations`,
    { headers: { Authorization: `Bearer ${revokedAssessorToken}` } },
  );
  expect(revokedObservationRead.status()).toBe(404);
  const revokedObservationWrite = await page.request.post(
    `${API}/api/v1/class-offerings/${CLASS_ID}/observations`, {
      headers: { Authorization: `Bearer ${revokedAssessorToken}` },
      data: { ...observationBody, idempotency_key: crypto.randomUUID() },
    },
  );
  expect(revokedObservationWrite.status()).toBe(404);

});
