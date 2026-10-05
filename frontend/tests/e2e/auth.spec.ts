import { expect, test, type Page } from "@playwright/test";

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
  // remove the Keycloak SSO session between role switches in this acceptance scenario
  await page.context().clearCookies();
}

test("candidate learns, submits; instructor gives feedback; proof remains separate", async ({ page }) => {
  test.setTimeout(90_000);
  const candidatePassword = process.env.PARCHAM_DEV_CANDIDATE_PASSWORD;
  const instructorPassword = process.env.PARCHAM_DEV_INSTRUCTOR_PASSWORD;
  if (!candidatePassword || !instructorPassword) {
    throw new Error("Development OIDC passwords are required");
  }

  await login(page, "candidate", candidatePassword);
  await expect(page.getByText("الان چه چیزی باید یاد بگیرم؟")).toBeVisible();
  await expect(page.getByText("پیش‌مطالعه: مالکیت مسئله تا نتیجه")).toBeVisible();
  await expect(page.getByText("تمرین هدایت‌شده: مسئله بدون صاحب")).toBeVisible();
  await expect(page.getByText("مطالعه موردی: انتشار ناموفق")).toBeVisible();
  await expect(page.getByText("تمرین هدایت‌شده").first()).toBeVisible();
  await expect(page.getByText("مطالعه موردی").first()).toBeVisible();
  await expect(page.getByText("تکلیف: Ownership Memo")).toBeVisible();
  await expect(page.getByText("TO_LEARN").first()).toBeVisible();
  await expect(page.getByText("UNPROVEN").first()).toBeVisible();

  const preWorkCard = page.locator(".learning-card").filter({
    hasText: "پیش‌مطالعه: مالکیت مسئله تا نتیجه",
  });
  await preWorkCard.getByRole("button", { name: "شروع" }).click();
  await expect(page.getByText("IN_LEARNING").first()).toBeVisible();
  await expect(page.getByText("UNPROVEN").first()).toBeVisible();
  await preWorkCard.getByRole("button", { name: "تکمیل فعالیت" }).click();

  const practiceCard = page.locator(".learning-card").filter({
    hasText: "تمرین هدایت‌شده: مسئله بدون صاحب",
  });
  await practiceCard.getByLabel("پاسخ تمرین").fill(
    "مالکیت Outcome را از تعریف مسئله تا بازیابی نتیجه نگه می‌دارم و نقطه Escalation را شفاف می‌کنم.",
  );
  await practiceCard.getByRole("button", { name: "ثبت تمرین" }).click();
  await expect(practiceCard.getByText("1 ATTEMPT")).toBeVisible();
  await expect(practiceCard.getByText("در انتظار بازخورد مدرس.")).toBeVisible();
  await expect(page.getByText("UNPROVEN").first()).toBeVisible();

  const caseCard = page.locator(".learning-card").filter({
    hasText: "مطالعه موردی: انتشار ناموفق",
  });
  await caseCard.getByLabel("پاسخ تمرین").fill(
    "ابتدا Outcome شکست‌خورده و مالک تصمیم را روشن می‌کنم، سپس داده‌های رخداد را جمع می‌کنم و Recovery Plan با Checkpoint مشخص می‌سازم.",
  );
  await caseCard.getByRole("button", { name: "ثبت تمرین" }).click();
  await expect(caseCard.getByText("1 ATTEMPT")).toBeVisible();

  await page.getByLabel("پاسخ تکلیف").fill(
    "Outcome را مالک می‌شوم، مرز تصمیم را روشن می‌کنم و در شکست مسئول بازیابی نتیجه هستم.",
  );
  await page.getByRole("button", { name: "ثبت تکلیف" }).click();
  await expect(page.getByText("تکلیف ثبت شد. این ثبت به‌تنهایی به معنی اثبات شایستگی نیست.")).toBeVisible();
  await expect(page.getByText("LEARNING_COMPLETED").first()).toBeVisible();
  await expect(page.getByText("UNPROVEN").first()).toBeVisible();

  await logout(page);
  await login(page, "instructor", instructorPassword);

  await expect(page.getByText("فضای مدرس")).toBeVisible();
  await expect(page.getByText("تمرین‌های ثبت‌شده")).toBeVisible();
  await expect(page.getByText("Candidate Demo").first()).toBeVisible();
  const guidedAttemptCard = page.locator(".assignment-card").filter({
    hasText: "تمرین هدایت‌شده: مسئله بدون صاحب — تلاش 1",
  });
  await guidedAttemptCard.getByLabel("بازخورد تمرین 1").fill(
    "منطق تصمیم روشن است؛ در Attempt بعدی Trigger مشخص برای Escalation و معیار Outcome اضافه کن.",
  );
  await guidedAttemptCard.getByRole("button", { name: "ثبت بازخورد تمرین" }).click();
  await expect(
    page.getByText("بازخورد تمرین ثبت شد. این بازخورد توسعه‌ای است و Evidence مستقل محسوب نمی‌شود."),
  ).toBeVisible();

  await expect(page.getByText("ارسال‌های فراگیران")).toBeVisible();
  await page.getByLabel("بازخورد مدرس").fill(
    "مرز مسئولیت روشن است؛ در نسخه بعد شاخص Outcome و نقطه Escalation را دقیق‌تر کن.",
  );
  await page.getByRole("button", { name: "ثبت بازخورد", exact: true }).click();
  await expect(
    page.getByText("بازخورد ثبت شد. بازخورد آموزشی مستقیماً Capability را Proven نمی‌کند."),
  ).toBeVisible();

  await logout(page);
  await login(page, "candidate", candidatePassword);

  await expect(page.getByTestId("candidate-practice-feedback-1")).toContainText(
    "Trigger مشخص برای Escalation",
  );
  await expect(page.getByTestId("candidate-feedback")).toContainText("مرز مسئولیت روشن است");
  await expect(page.getByText("UNPROVEN").first()).toBeVisible();

  const replayCard = page.locator(".learning-card").filter({
    hasText: "تمرین هدایت‌شده: مسئله بدون صاحب",
  });
  await replayCard.getByLabel("پاسخ Replay").fill(
    "در Replay، Trigger را افت بیش از ۱۰٪ Outcome و Escalation را عبور از مرز اختیار تعریف می‌کنم.",
  );
  await replayCard.getByRole("button", { name: "ثبت Replay" }).click();
  await expect(replayCard.getByText("2 ATTEMPT")).toBeVisible();
  await expect(page.getByText("UNPROVEN").first()).toBeVisible();

  await logout(page);
  await login(page, "instructor", instructorPassword);

  const guidedReplayAttemptCard = page.locator(".assignment-card").filter({
    hasText: "تمرین هدایت‌شده: مسئله بدون صاحب — تلاش 2",
  });
  await expect(guidedReplayAttemptCard).toBeVisible();
  await guidedReplayAttemptCard.getByLabel("بازخورد تمرین 2").fill(
    "Replay نسبت به تلاش اول بهتر است؛ Trigger و مرز اختیار اکنون قابل اقدام شده‌اند.",
  );
  await guidedReplayAttemptCard
    .getByRole("button", { name: "ثبت بازخورد تمرین" })
    .click();
  await expect(page.getByTestId("instructor-practice-feedback-2")).toContainText(
    "Replay نسبت به تلاش اول بهتر است",
  );

  await logout(page);
  await login(page, "candidate", candidatePassword);

  await expect(page.getByTestId("candidate-practice-feedback-1")).toContainText(
    "Trigger مشخص برای Escalation",
  );
  await expect(page.getByTestId("candidate-practice-feedback-2")).toContainText(
    "Replay نسبت به تلاش اول بهتر است",
  );
  await expect(page.getByText("UNPROVEN").first()).toBeVisible();
});


test("academy admin authors and activates a versioned mission", async ({ page }) => {
  test.setTimeout(90_000);
  const adminPassword = process.env.PARCHAM_DEV_ADMIN_PASSWORD;
  if (!adminPassword) throw new Error("Academy Admin OIDC password is required");

  await login(page, "academy-admin", adminPassword);
  await expect(page.getByText("طراحی مأموریت")).toBeVisible();

  await page.getByLabel("کد مأموریت").fill("OWNERSHIP_RECOVERY_E2E");
  await page.getByLabel("نام Template").fill("Ownership Recovery E2E");
  await page.getByRole("button", { name: "ساخت Draft" }).click();

  const missionCard = page.locator(".assignment-card").filter({
    hasText: "OWNERSHIP_RECOVERY_E2E",
  });
  await expect(missionCard.getByTestId("mission-status")).toHaveText("DRAFT");

  await missionCard.getByRole("button", { name: "اعتبارسنجی تعریف" }).click();
  await expect(page.getByText("تعریف مأموریت معتبر است.")).toBeVisible();

  await missionCard.getByRole("button", { name: "ورود به Pilot" }).click();
  await expect(missionCard.getByTestId("mission-status")).toHaveText("PILOT");

  await missionCard.getByRole("button", { name: "تأیید Validated" }).click();
  await expect(missionCard.getByTestId("mission-status")).toHaveText("VALIDATED");

  await missionCard.getByRole("button", { name: "فعال‌سازی" }).click();
  await expect(missionCard.getByTestId("mission-status")).toHaveText("ACTIVE");
});
