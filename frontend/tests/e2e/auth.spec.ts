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
  const candidatePassword = process.env.PARCHAM_DEV_CANDIDATE_PASSWORD;
  const instructorPassword = process.env.PARCHAM_DEV_INSTRUCTOR_PASSWORD;
  if (!candidatePassword || !instructorPassword) {
    throw new Error("Development OIDC passwords are required");
  }

  await login(page, "candidate", candidatePassword);
  await expect(page.getByText("الان چه چیزی باید یاد بگیرم؟")).toBeVisible();
  await expect(page.getByText("پیش‌مطالعه: مالکیت مسئله تا نتیجه")).toBeVisible();
  await expect(page.getByText("تمرین: مسئله بدون صاحب")).toBeVisible();
  await expect(page.getByText("تکلیف: Ownership Memo")).toBeVisible();
  await expect(page.getByText("UNPROVEN").first()).toBeVisible();

  await page.getByLabel("پاسخ تکلیف").fill(
    "Outcome را مالک می‌شوم، مرز تصمیم را روشن می‌کنم و در شکست مسئول بازیابی نتیجه هستم.",
  );
  await page.getByRole("button", { name: "ثبت تکلیف" }).click();
  await expect(page.getByText("تکلیف ثبت شد. این ثبت به‌تنهایی به معنی اثبات شایستگی نیست.")).toBeVisible();

  await logout(page);
  await login(page, "instructor", instructorPassword);

  await expect(page.getByText("فضای مدرس")).toBeVisible();
  await expect(page.getByText("ارسال‌های فراگیران")).toBeVisible();
  await expect(page.getByText("Candidate Demo")).toBeVisible();
  await page.getByLabel("بازخورد مدرس").fill(
    "مرز مسئولیت روشن است؛ در نسخه بعد شاخص Outcome و نقطه Escalation را دقیق‌تر کن.",
  );
  await page.getByRole("button", { name: "ثبت بازخورد" }).click();
  await expect(
    page.getByText("بازخورد ثبت شد. بازخورد آموزشی مستقیماً Capability را Proven نمی‌کند."),
  ).toBeVisible();

  await logout(page);
  await login(page, "candidate", candidatePassword);

  await expect(page.getByTestId("candidate-feedback")).toContainText("مرز مسئولیت روشن است");
  await expect(page.getByText("UNPROVEN").first()).toBeVisible();
});
