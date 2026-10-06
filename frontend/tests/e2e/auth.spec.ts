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

async function currentAccessToken(page: Page): Promise<string> {
  const token = await page.evaluate(() => {
    for (const storage of [window.sessionStorage, window.localStorage]) {
      for (let index = 0; index < storage.length; index += 1) {
        const key = storage.key(index);
        if (!key) continue;
        const raw = storage.getItem(key);
        if (!raw) continue;
        try {
          const parsed = JSON.parse(raw) as { access_token?: unknown };
          if (typeof parsed.access_token === "string" && parsed.access_token.length > 0) {
            return parsed.access_token;
          }
        } catch {
          // ignore unrelated browser storage
        }
      }
    }
    return null;
  });
  if (!token) throw new Error("OIDC access token is not available in browser storage");
  return token;
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


test("academy admin authors, activates, and candidate runs a deterministic mission", async ({ page }) => {
  test.setTimeout(240_000);
  const adminPassword = process.env.PARCHAM_DEV_ADMIN_PASSWORD;
  const candidatePassword = process.env.PARCHAM_DEV_CANDIDATE_PASSWORD;
  const assessorPassword = process.env.PARCHAM_DEV_ASSESSOR_PASSWORD;
  if (!adminPassword || !candidatePassword || !assessorPassword) {
    throw new Error("Academy Admin, Candidate, and Assessor OIDC passwords are required");
  }

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

  await logout(page);
  await login(page, "candidate", candidatePassword);

  await expect(page.getByText("مأموریت‌های شبیه‌سازی")).toBeVisible();
  await expect(page.getByText("هنوز Mission فعال قابل اجرا وجود ندارد.")).toBeVisible();
  await expect(page.getByText("OWNERSHIP_RECOVERY_E2E")).not.toBeVisible();

  await logout(page);
  await login(page, "academy-admin", adminPassword);

  const activeMissionCard = page.locator(".assignment-card").filter({
    hasText: "OWNERSHIP_RECOVERY_E2E",
  });
  await activeMissionCard
    .getByLabel("Candidate برای Assignment")
    .selectOption({ label: "Candidate Demo" });
  await activeMissionCard.getByRole("button", { name: "اختصاص مأموریت" }).click();
  await expect(page.getByText("Mission Assignment ثبت شد.")).toBeVisible();
  await expect(activeMissionCard).toContainText("Candidate Demo · ASSIGNED");

  await logout(page);
  await login(page, "candidate", candidatePassword);

  await expect(page.getByText("مأموریت‌های شبیه‌سازی")).toBeVisible();
  const runtimeCard = page.locator(".mission-runtime-card").filter({
    hasText: "OWNERSHIP_RECOVERY_E2E",
  });
  await expect(runtimeCard).toBeVisible();
  await runtimeCard.getByRole("button", { name: "شروع مأموریت" }).click();
  await expect(runtimeCard.getByTestId("runtime-status")).toHaveText("RUNNING");
  await expect(runtimeCard).toContainText("Candidate-visible World State");
  await expect(runtimeCard.getByTestId("world-state")).toContainText('"error_rate_percent": 13');
  await expect(runtimeCard.getByTestId("world-state")).not.toContainText("root_cause_code");
  await expect(runtimeCard).not.toContainText("DOWNSTREAM_DEPENDENCY");
  await expect(runtimeCard).not.toContainText("Seed");

  const actorState = runtimeCard.getByTestId("actor-state-business_sponsor");
  await expect(runtimeCard).toContainText("Business Sponsor");
  await expect(actorState).toContainText('"trust_toward_candidate": 35');
  await expect(actorState).toContainText('"current_frustration": 70');
  await expect(actorState).toContainText('"commitment": "CONDITIONAL"');
  await expect(runtimeCard).not.toContainText("private_escalation_threshold");

  const deliveryLeadState = runtimeCard.getByTestId("actor-state-delivery_lead");
  await expect(runtimeCard).toContainText("Delivery Lead");
  await expect(deliveryLeadState).toContainText('"capacity_status": "AVAILABLE"');
  await expect(deliveryLeadState).toContainText('"commitment": "UNASSIGNED"');
  await expect(deliveryLeadState).toContainText('"delegated_responsibility": "NONE"');
  await expect(runtimeCard).not.toContainText("private_delivery_risk");
  await expect(runtimeCard.getByTestId("world-state")).toContainText(
    '"accountability_owner": "CANDIDATE"',
  );
  await expect(runtimeCard.getByTestId("world-state")).toContainText(
    '"recovery_coordinator": "CANDIDATE"',
  );
  await expect(runtimeCard.getByTestId("world-state")).toContainText(
    '"scope": "FULL_ROLLOUT"',
  );
  await expect(runtimeCard.getByTestId("world-state")).toContainText(
    '"scope_change_status": "NOT_CHANGED"',
  );
  await expect(runtimeCard.getByTestId("world-state")).toContainText(
    '"resource_allocation_status": "NOT_ALLOCATED"',
  );
  await expect(runtimeCard.getByTestId("world-state")).toContainText(
    '"experiment_status": "NOT_RUN"',
  );
  await expect(runtimeCard.getByTestId("world-state")).toContainText(
    '"available_units": 3',
  );
  await expect(runtimeCard.getByTestId("world-state")).toContainText(
    '"recovery_capacity_units": 0',
  );

  await runtimeCard
    .getByLabel("پیام به Business Sponsor")
    .fill(
      "مالکیت نتیجه با من است. rollback را کنترل‌شده پیش می‌برم و در checkpoint بعدی وضعیت و ریسک را شفاف گزارش می‌کنم.",
    );
  await runtimeCard
    .getByRole("button", { name: "پذیرش مالکیت و هم‌راستا کردن برنامه بازیابی" })
    .click();

  await expect(actorState).toContainText('"trust_toward_candidate": 60');
  await expect(actorState).toContainText('"current_frustration": 40');
  await expect(actorState).toContainText('"commitment": "SUPPORTIVE"');
  await expect(runtimeCard).toContainText("Actor v2");
  await expect(runtimeCard).toContainText("مالکیت روشن شد.");
  await expect(runtimeCard).not.toContainText("private_escalation_threshold");

  await runtimeCard.getByLabel("دلیل تغییر دامنه").fill(
    "برای کاهش blast radius دامنه recovery را به مشتریان حیاتی محدود می‌کنم و accountability نتیجه را حفظ می‌کنم.",
  );
  await runtimeCard
    .getByRole("button", {
      name: "محدودکردن recovery به مشتریان حیاتی · FULL_ROLLOUT → CRITICAL_CUSTOMERS_ONLY",
    })
    .click();

  await expect(runtimeCard.getByTestId("world-state")).toContainText(
    '"scope": "CRITICAL_CUSTOMERS_ONLY"',
  );
  await expect(runtimeCard.getByTestId("world-state")).toContainText(
    '"scope_change_status": "ACTIVE"',
  );
  await expect(runtimeCard.getByTestId("world-state")).toContainText(
    '"accountability_owner": "CANDIDATE"',
  );
  await expect(runtimeCard).toContainText(
    "دامنه recovery به مشتریان حیاتی محدود شد",
  );
  await expect(runtimeCard).toContainText("SCOPE_CHANGE_OBSERVED");
  await expect(runtimeCard).toContainText("FULL_ROLLOUT");
  await expect(runtimeCard).toContainText("CRITICAL_CUSTOMERS_ONLY");
  await expect(runtimeCard).not.toContainText("scope_path");
  await expect(runtimeCard).not.toContainText("world_effect_applied");

  const experimentContract = runtimeCard.getByTestId(
    "experiment-contract-RECOVERY_CANARY",
  );
  await expect(experimentContract).toContainText('"hypothesis"');
  await expect(experimentContract).toContainText('"decision_rule"');
  await expect(experimentContract).toContainText('"duration_stopping_rule"');
  await expect(experimentContract).toContainText('"status": "APPROVED"');

  await runtimeCard.getByLabel("دلیل اجرای آزمایش").fill(
    "قبل از تعهد منابع بیشتر، با یک canary محدود عدم‌قطعیت درباره اثر rollback بر error rate را کم می‌کنم.",
  );
  await runtimeCard
    .getByRole("button", { name: "اجرای canary بازیابی روی ۱۰٪ ترافیک" })
    .click();

  await expect(runtimeCard.getByTestId("world-state")).toContainText(
    '"experiment_status": "COMPLETED"',
  );
  const experimentResult = runtimeCard.getByTestId(
    "experiment-result-RECOVERY_CANARY",
  );
  await expect(experimentResult).toContainText('"error_rate_percent": 13');
  await expect(experimentResult).toContainText('"error_rate_percent": 5');
  await expect(experimentResult).toContainText('"customer_impact_percent": 1');
  await expect(runtimeCard).toContainText("EXPERIMENT_RESULT_OBSERVED");
  await expect(runtimeCard).toContainText(
    "تفسیر نتیجه با Candidate است",
  );
  await expect(runtimeCard).not.toContainText('"verdict"');
  await expect(runtimeCard).not.toContainText('"interpretation"');
  await expect(runtimeCard).not.toContainText('"evidence_strength"');
  await expect(runtimeCard).not.toContainText("world_effect_applied");

  await runtimeCard.getByLabel("دلیل تخصیص منبع").fill(
    "ظرفیت محدود مهندسی را به recovery متعهد می‌کنم چون کاهش ریسک مشتریان حیاتی نسبت به کارهای دیگر اولویت بالاتری دارد.",
  );
  await runtimeCard
    .getByRole("button", {
      name: "اختصاص ۲ واحد ظرفیت مهندسی به recovery · 2 ENGINEER_EQUIVALENT",
    })
    .click();

  await expect(runtimeCard.getByTestId("world-state")).toContainText(
    '"resource_allocation_status": "ACTIVE"',
  );
  await expect(runtimeCard.getByTestId("world-state")).toContainText(
    '"available_units": 1',
  );
  await expect(runtimeCard.getByTestId("world-state")).toContainText(
    '"recovery_capacity_units": 2',
  );
  await expect(runtimeCard.getByTestId("world-state")).toContainText(
    '"accountability_owner": "CANDIDATE"',
  );
  await expect(runtimeCard).toContainText(
    "دو واحد ظرفیت مهندسی به recovery متعهد شد",
  );
  await expect(runtimeCard).toContainText("RESOURCE_ALLOCATION_OBSERVED");
  await expect(runtimeCard).not.toContainText("available_path");
  await expect(runtimeCard).not.toContainText("allocated_path");
  await expect(runtimeCard).not.toContainText("resource_cost_applied");
  await expect(runtimeCard).not.toContainText("world_effect_applied");

  await runtimeCard.getByLabel("دلیل واگذاری").fill(
    "هماهنگی rollback و جمع‌آوری وضعیت را به Delivery Lead می‌سپارم؛ accountability نتیجه و تصمیم نهایی همچنان با من می‌ماند.",
  );
  await runtimeCard
    .getByRole("button", { name: "واگذاری هماهنگی بازیابی به Delivery Lead" })
    .click();

  await expect(deliveryLeadState).toContainText(
    '"commitment": "OWNS_RECOVERY_COORDINATION"',
  );
  await expect(deliveryLeadState).toContainText(
    '"delegated_responsibility": "RECOVERY_COORDINATION"',
  );
  await expect(runtimeCard).toContainText("Actor v2");
  await expect(runtimeCard.getByTestId("world-state")).toContainText(
    '"delegation_status": "ACTIVE"',
  );
  await expect(runtimeCard.getByTestId("world-state")).toContainText(
    '"accountability_owner": "CANDIDATE"',
  );
  await expect(runtimeCard.getByTestId("world-state")).toContainText(
    '"recovery_coordinator": "DELIVERY_LEAD"',
  );
  await expect(runtimeCard).toContainText(
    "accountability نتیجه همچنان با شما می‌ماند",
  );
  await expect(runtimeCard).toContainText("DELEGATION_OBSERVED");
  await expect(runtimeCard).not.toContainText("world_effect_applied");
  await expect(runtimeCard).not.toContainText("actor_effect_applied");
  await expect(runtimeCard).not.toContainText("private_delivery_risk");

  await runtimeCard.getByLabel("دلیل Escalation").fill(
    "ریسک rollout از مرز تصمیم تیم عبور کرده و Executive attention برای recovery checkpoint لازم است.",
  );
  await runtimeCard
    .getByRole("button", { name: "Escalate برنامه بازیابی به Business Sponsor" })
    .click();

  await expect(runtimeCard).toContainText("Actor v3");
  await expect(actorState).toContainText('"commitment": "EXECUTIVE_SPONSORSHIP"');
  await expect(runtimeCard.getByTestId("world-state")).toContainText(
    '"executive_attention": "ENGAGED"',
  );
  await expect(runtimeCard.getByTestId("world-state")).toContainText(
    '"escalation_status": "EXECUTIVE_REVIEW"',
  );
  await expect(runtimeCard).toContainText("Escalation پذیرفته شد.");
  await expect(runtimeCard).toContainText("ESCALATION_OBSERVED");
  await expect(runtimeCard).not.toContainText("world_effect_applied");
  await expect(runtimeCard).not.toContainText("actor_effect_applied");
  await expect(runtimeCard).toContainText("Executive recovery checkpoint");
  await expect(runtimeCard).toContainText("PENDING");
  await expect(runtimeCard.getByTestId("world-state")).toContainText(
    '"executive_checkpoint": "NOT_SCHEDULED"',
  );

  await runtimeCard
    .getByRole("button", { name: "اجرای رویداد بعدی جهان" })
    .click();

  await expect(runtimeCard).toContainText("APPLIED");
  await expect(runtimeCard.getByTestId("world-state")).toContainText(
    '"executive_checkpoint": "DUE"',
  );
  await expect(runtimeCard.getByTestId("world-state")).toContainText(
    '"escalation_status": "CHECKPOINT_DUE"',
  );
  await expect(runtimeCard).toContainText("SCHEDULED_EFFECT_OBSERVED");
  await expect(runtimeCard).not.toContainText("effect_applied");

  await runtimeCard.getByRole("button", { name: "درخواست Dependency trace" }).click();
  await expect(runtimeCard).toContainText("intermittent timeout spikes");

  await runtimeCard.getByLabel("منطق تصمیم").fill(
    "ریسک ادامه rollout از هزینه rollback بیشتر است؛ rollback کنترل‌شده را شروع می‌کنم و وضعیت را با checkpoint مشخص دوباره ارزیابی می‌کنم.",
  );
  await runtimeCard
    .getByRole("button", { name: "Rollback کنترل‌شده و برنامه بازیابی" })
    .click();

  await expect(runtimeCard.getByTestId("runtime-status")).toHaveText("COMPLETED");
  await expect(runtimeCard).toContainText("Assignment COMPLETED");
  const cancelledDeadline = runtimeCard.locator(".assignment-head").filter({
    hasText: "Recovery decision deadline",
  });
  await expect(cancelledDeadline.locator(".state")).toHaveText("CANCELLED");
  const appliedStateEffect = runtimeCard.locator(".assignment-head").filter({
    hasText: "Recovery commitment broadcast",
  });
  await expect(appliedStateEffect).toContainText("state-triggered");
  await expect(appliedStateEffect.locator(".state")).toHaveText("APPLIED");
  await expect(runtimeCard.getByTestId("world-state")).toContainText(
    '"recovery_signal": "BROADCAST"',
  );
  await expect(runtimeCard).toContainText("SCHEDULED_EFFECT_CANCELLED_OBSERVED");
  await expect(runtimeCard).toContainText("DECISION_COMMITTED");
  await expect(runtimeCard).not.toContainText("cancel_condition_matched");
  await expect(runtimeCard).not.toContainText("trigger_condition_matched");
  await expect(runtimeCard).not.toContainText("WORLD_STATE_EQUALS");
  await expect(runtimeCard.getByTestId("world-state")).toContainText('"rollback_started": true');
  await expect(runtimeCard.getByTestId("world-state")).not.toContainText("root_cause_code");
  await expect(runtimeCard).not.toContainText("DOWNSTREAM_DEPENDENCY");
  await expect(runtimeCard).toContainText("world state advanced from version 7 to 8");
  await expect(runtimeCard).toContainText("ACTOR_RESPONSE_OBSERVED");
  await expect(runtimeCard).not.toContainText("actor_effect_applied");

  // A second assignment proves that explicit NO_ACTION has a canonical cost of delay
  // and can end a Mission with TIME_EXPIRED without becoming Candidate failure/proof.
  await logout(page);
  await login(page, "academy-admin", adminPassword);

  const activeMissionCardForTimeout = page.locator(".assignment-card").filter({
    hasText: "OWNERSHIP_RECOVERY_E2E",
  });
  await activeMissionCardForTimeout
    .getByLabel("Candidate برای Assignment")
    .selectOption({ label: "Candidate Demo" });
  await activeMissionCardForTimeout
    .getByRole("button", { name: "اختصاص مأموریت" })
    .click();
  await expect(page.getByText("Mission Assignment ثبت شد.")).toBeVisible();

  await logout(page);
  await login(page, "candidate", candidatePassword);

  const timeoutCard = page
    .locator(".mission-runtime-card")
    .filter({ hasText: "OWNERSHIP_RECOVERY_E2E" })
    .first();
  await expect(timeoutCard).toContainText("Assignment ASSIGNED");
  await timeoutCard.getByRole("button", { name: "شروع مأموریت" }).click();
  await expect(timeoutCard.getByTestId("runtime-status")).toHaveText("RUNNING");

  await timeoutCard.getByLabel("دلیل Escalation").fill(
    "برای سنجش cost of delay، موضوع را به Business Sponsor می‌برم اما تصمیم عملیاتی جدیدی نمی‌گیرم.",
  );
  await timeoutCard
    .getByRole("button", { name: "Escalate برنامه بازیابی به Business Sponsor" })
    .click();
  await expect(timeoutCard).toContainText("Executive recovery checkpoint");
  await expect(timeoutCard).toContainText("Recovery decision deadline");

  await timeoutCard.getByLabel("دلیل عدم اقدام").fill(
    "فعلاً اقدام جدیدی انجام نمی‌دهم و آگاهانه تا پایان window تصمیم صبر می‌کنم.",
  );
  await timeoutCard
    .getByRole("button", { name: "۳۰ دقیقه بدون اقدام جدید صبر می‌کنم" })
    .click();

  await expect(timeoutCard.getByTestId("runtime-status")).toHaveText("TIME_EXPIRED");
  await expect(timeoutCard).toContainText("Assignment COMPLETED");
  const appliedDeadline = timeoutCard.locator(".assignment-head").filter({
    hasText: "Recovery decision deadline",
  });
  await expect(appliedDeadline.locator(".state")).toHaveText("APPLIED");
  const cancelledStateEffect = timeoutCard.locator(".assignment-head").filter({
    hasText: "Recovery commitment broadcast",
  });
  await expect(cancelledStateEffect).toContainText("state-triggered");
  await expect(cancelledStateEffect.locator(".state")).toHaveText("CANCELLED");
  await expect(timeoutCard.getByTestId("world-state")).toContainText(
    '"recovery_signal": "NOT_BROADCAST"',
  );
  await expect(timeoutCard.getByTestId("world-state")).toContainText('"level": "CRITICAL"');
  await expect(timeoutCard.getByTestId("world-state")).toContainText(
    '"decision_status": "EXPIRED"',
  );
  await expect(timeoutCard.getByTestId("world-state")).toContainText(
    '"escalation_status": "DEADLINE_MISSED"',
  );
  await expect(timeoutCard.getByTestId("world-state")).toContainText(
    '"executive_checkpoint": "DUE"',
  );
  await expect(timeoutCard).toContainText("NO_ACTION_OBSERVED");
  await expect(timeoutCard).toContainText("MISSION_TIME_EXPIRED");
  await expect(timeoutCard).toContainText("RECOVERY_DECISION_DEADLINE");
  await expect(timeoutCard).not.toContainText("trigger_condition_matched");
  await expect(timeoutCard).not.toContainText("WORLD_STATE_EQUALS");
  await expect(
    timeoutCard.getByRole("button", { name: "Rollback کنترل‌شده و برنامه بازیابی" }),
  ).toHaveCount(0);
  await expect(page.getByText("UNPROVEN").first()).toBeVisible();

  // Evidence Engine starts from sealed factual Observation and remains separate from Proof.
  await logout(page);
  await login(page, "assessor", assessorPassword);

  await expect(page.getByText("فضای ارزیاب Evidence")).toBeVisible();
  const evidenceCard = page
    .locator('[data-testid^="evidence-case-"]')
    .filter({ hasText: "EXPERIMENT_RESULT_OBSERVED" })
    .first();
  await expect(evidenceCard).toBeVisible();
  await expect(evidenceCard.locator(":scope > .assignment-head > .state")).toHaveText("DRAFT");
  await expect(evidenceCard).toContainText("SEALED");
  await expect(evidenceCard).toContainText('"error_rate_percent": 13');
  await expect(evidenceCard).toContainText('"error_rate_percent": 5');

  await evidenceCard.getByRole("button", { name: "ثبت Interpretation" }).click();
  await expect(evidenceCard.locator(":scope > .assignment-head > .state")).toHaveText("SUBMITTED");
  await expect(evidenceCard.getByTestId("assessor-interpretation")).toContainText(
    "METRIC_REASONING",
  );
  await expect(evidenceCard.getByTestId("assessor-interpretation")).toContainText(
    "AI NONE",
  );

  const evidenceCaseTestId = await evidenceCard.getAttribute("data-testid");
  if (!evidenceCaseTestId) throw new Error("Evidence Case test id is missing");
  const evidenceCaseId = evidenceCaseTestId.replace("evidence-case-", "");
  const assessorAccessToken = await currentAccessToken(page);
  const staleReview = await page.context().request.post(
    `http://localhost:8000/api/v1/evidence-cases/${evidenceCaseId}/reviews`,
    {
      headers: {
        Authorization: `Bearer ${assessorAccessToken}`,
      },
      data: {
        expected_version: 1,
        rationale: "Stale command must be rejected before human review starts.",
      },
    },
  );
  expect(staleReview.status()).toBe(409);
  expect((await staleReview.json()).code).toBe("VERSION_CONFLICT");

  await evidenceCard.getByRole("button", { name: "شروع Review" }).click();
  await expect(evidenceCard.locator(":scope > .assignment-head > .state")).toHaveText("UNDER_REVIEW");
  await evidenceCard
    .getByRole("button", { name: "درخواست Context از Candidate" })
    .click();
  await expect(evidenceCard.locator(":scope > .assignment-head > .state")).toHaveText("NEEDS_CONTEXT");

  await logout(page);
  await login(page, "candidate", candidatePassword);

  const candidateEvidenceCard = page
    .locator('[data-testid^="candidate-evidence-case-"]')
    .filter({ hasText: "EXPERIMENT_RESULT_OBSERVED" })
    .first();
  await expect(candidateEvidenceCard).toBeVisible();
  await expect(candidateEvidenceCard.locator(":scope > .assignment-head > .state")).toHaveText("NEEDS_CONTEXT");
  await expect(candidateEvidenceCard.getByTestId("candidate-context-request")).toContainText(
    "Result چگونه روی تصمیم بعدی تو اثر گذاشت",
  );
  await expect(candidateEvidenceCard).not.toContainText("METRIC_REASONING");
  await expect(candidateEvidenceCard).not.toContainText(
    "Source lineage and interpretation contract reviewed.",
  );

  const candidateAccessToken = await currentAccessToken(page);
  const assessorOnlyRead = await page.context().request.get(
    `http://localhost:8000/api/v1/evidence-cases/${evidenceCaseId}`,
    {
      headers: {
        Authorization: `Bearer ${candidateAccessToken}`,
      },
    },
  );
  expect(assessorOnlyRead.status()).toBe(403);

  await candidateEvidenceCard
    .getByLabel("پاسخ Context Evidence")
    .fill(
      "Result را فقط به‌عنوان measurement استفاده کردم؛ کاهش error rate به‌تنهایی Proof نیست و تصمیم rollback را با guardrail و context مأموریت سنجیدم.",
    );
  await candidateEvidenceCard.getByRole("button", { name: "ارسال Context" }).click();
  await expect(candidateEvidenceCard).toContainText(
    "کاهش error rate به‌تنهایی Proof نیست",
  );
  await expect(page.getByText("UNPROVEN").first()).toBeVisible();

  await logout(page);
  await login(page, "assessor", assessorPassword);

  const reviewedEvidenceCard = page
    .locator('[data-testid^="evidence-case-"]')
    .filter({ hasText: "EXPERIMENT_RESULT_OBSERVED" })
    .first();
  await expect(reviewedEvidenceCard).toContainText(
    "کاهش error rate به‌تنهایی Proof نیست",
  );
  await reviewedEvidenceCard.getByRole("button", { name: "بازگشت به Review" }).click();
  await expect(reviewedEvidenceCard.locator(":scope > .assignment-head > .state")).toHaveText("UNDER_REVIEW");
  await reviewedEvidenceCard.getByRole("button", { name: "پذیرش Evidence" }).click();
  await expect(reviewedEvidenceCard.locator(":scope > .assignment-head > .state")).toHaveText("ACCEPTED");

  await logout(page);
  await login(page, "candidate", candidatePassword);

  const acceptedEvidenceCard = page
    .locator('[data-testid^="candidate-evidence-case-"]')
    .filter({ hasText: "EXPERIMENT_RESULT_OBSERVED" })
    .first();
  await expect(acceptedEvidenceCard.locator(":scope > .assignment-head > .state")).toHaveText("ACCEPTED");
  await expect(
    acceptedEvidenceCard.getByTestId("candidate-accepted-interpretation"),
  ).toContainText("METRIC_REASONING");
  await expect(
    acceptedEvidenceCard.getByTestId("candidate-accepted-interpretation"),
  ).toContainText("Reviewed Evidence");
  await expect(page.getByText("UNPROVEN").first()).toBeVisible();

  // Pattern Engine continues only from Accepted Evidence and remains separate from Proof.
  await logout(page);
  await login(page, "assessor", assessorPassword);

  await expect(page.getByText("فضای ارزیاب Pattern")).toBeVisible();
  const patternWorkspace = page.getByTestId("assessor-pattern-workspace");
  await expect(patternWorkspace).toContainText("EXPERIMENT_RESULT_OBSERVED");
  await patternWorkspace.getByLabel(`انتخاب Evidence ${evidenceCaseId}`).check();
  await patternWorkspace.getByRole("button", { name: "ساخت Evidence Set" }).click();
  await expect(
    patternWorkspace.getByTestId("pattern-evidence-set-created"),
  ).toContainText("Evidence Set v1");

  await patternWorkspace
    .getByLabel(/رابطه Evidence/)
    .selectOption("SUPPORTING");
  await patternWorkspace
    .getByLabel("Pattern status پیشنهادی")
    .selectOption("REPEATED");
  await patternWorkspace
    .getByLabel("منطق Pattern Candidate")
    .fill(
      "Accepted Evidence is assembled with explicit lineage; this human proposal does not alter proof state.",
    );
  await patternWorkspace
    .getByRole("button", { name: "ساخت Pattern Candidate" })
    .click();
  await expect(
    patternWorkspace.getByTestId("pattern-candidate-created"),
  ).toContainText("REPEATED");

  await patternWorkspace
    .getByLabel("Reviewed Pattern status")
    .selectOption("REPEATED");
  await patternWorkspace
    .getByLabel("منطق Human Review Pattern")
    .fill(
      "Full accepted-Evidence lineage reviewed; supporting relationship is explicit and no downstream proof mutation is authorized.",
    );
  await patternWorkspace
    .getByRole("button", { name: "ثبت Reviewed Behaviour Pattern" })
    .click();
  await expect(
    patternWorkspace.getByTestId("reviewed-pattern-created"),
  ).toContainText("REPEATED");

  const reviewedPatternCard = patternWorkspace
    .locator(".pattern-reviewed-card")
    .filter({ hasText: "METRIC_REASONING" })
    .first();
  await expect(reviewedPatternCard).toContainText("REPEATED");
  await reviewedPatternCard.getByRole("button", { name: "مشاهده Lineage" }).click();

  const patternLineage = patternWorkspace.getByTestId("pattern-lineage");
  await expect(patternLineage).toContainText("METRIC_REASONING");
  await expect(patternLineage).toContainText("REPEATED");
  await expect(patternLineage).toContainText("SUPPORTING");
  await expect(patternLineage).toContainText("EXPERIMENT_RESULT_OBSERVED");
  await expect(patternLineage).toContainText("MISSION_RUNTIME");
  await expect(patternLineage).toContainText("Evidence Set v1");

  await logout(page);
  await login(page, "candidate", candidatePassword);

  const candidatePatternToken = await currentAccessToken(page);
  const candidatePatternsResponse = await page.context().request.get(
    "http://localhost:8000/api/v1/me/patterns",
    {
      headers: {
        Authorization: `Bearer ${candidatePatternToken}`,
      },
    },
  );
  expect(candidatePatternsResponse.status()).toBe(200);
  const candidatePatterns = (await candidatePatternsResponse.json()) as Array<
    Record<string, unknown>
  >;
  const candidatePattern = candidatePatterns.find(
    (item) => item.behaviour_code === "METRIC_REASONING",
  );
  expect(candidatePattern).toBeTruthy();
  expect(candidatePattern?.pattern_status).toBe("REPEATED");
  expect(candidatePattern).not.toHaveProperty("reviewed_by");
  expect(candidatePattern).not.toHaveProperty("rationale");
  expect(candidatePattern).not.toHaveProperty("evidence");
  expect(candidatePattern).not.toHaveProperty("source_lineage");

  const candidateLineageResponse = await page.context().request.get(
    `http://localhost:8000/api/v1/patterns/${candidatePattern?.id}/lineage`,
    {
      headers: {
        Authorization: `Bearer ${candidatePatternToken}`,
      },
    },
  );
  expect(candidateLineageResponse.status()).toBe(403);

  // Reviewed Pattern is informative only; it must not promote proof/profile/gate state.
  await expect(page.getByText("UNPROVEN").first()).toBeVisible();
});
