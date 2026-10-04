import { expect, test, type Page } from "@playwright/test";

async function login(page: Page, username: string, password: string) {
  await page.goto("/");
  await page.getByRole("button", { name: "ورود به آکادمی" }).click();
  await page.locator("#username").fill(username);
  await page.locator("#password").fill(password);
  await page.locator("#kc-login").click();
}

test("candidate signs in through live OIDC and sees learning/proof workspace", async ({ page }) => {
  const password = process.env.PARCHAM_DEV_CANDIDATE_PASSWORD;
  if (!password) throw new Error("PARCHAM_DEV_CANDIDATE_PASSWORD is required");

  await login(page, "candidate", password);

  await expect(page.getByText("الان چه چیزی باید یاد بگیرم؟")).toBeVisible();
  await expect(page.getByText("الان چه چیزی باید اثبات کنم؟")).toBeVisible();
  await expect(page.getByText("Think & Own")).toBeVisible();
  await expect(page.getByText("UNPROVEN").first()).toBeVisible();
});

test("instructor signs in through live OIDC and sees assigned workspace", async ({ page }) => {
  const password = process.env.PARCHAM_DEV_INSTRUCTOR_PASSWORD;
  if (!password) throw new Error("PARCHAM_DEV_INSTRUCTOR_PASSWORD is required");

  await login(page, "instructor", password);

  await expect(page.getByText("فضای مدرس")).toBeVisible();
  await expect(page.getByText("کلاس‌های واگذارشده")).toBeVisible();
  await expect(page.getByText("Ownership & Accountability").first()).toBeVisible();
});
