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


test("academy admin authors, activates, and candidate runs a deterministic mission", async ({ page }) => {
  test.setTimeout(180_000);
  const adminPassword = process.env.PARCHAM_DEV_ADMIN_PASSWORD;
  const candidatePassword = process.env.PARCHAM_DEV_CANDIDATE_PASSWORD;
  if (!adminPassword || !candidatePassword) {
    throw new Error("Academy Admin and Candidate OIDC passwords are required");
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
  await expect(runtimeCard).toContainText("world state advanced from version 4 to 5");
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
});
