# 07 — معماری Parcham Simulation Engine

**وضعیت:** FINAL  
**تاریخ تثبیت:** 2026-10-04

## اصل طراحی

> Simulator پرچم یک بازی آموزشی نیست؛ یک موتور تصمیم‌گیری و تولید Evidence است.

هدف Simulator صرفاً سرگرمی یا انتقال محتوا نیست. باید بتواند نشان دهد فرد چه تصمیمی گرفت، با چه اطلاعاتی، چرا، چه پیامدی ایجاد شد و این رفتار چه Evidenceای درباره شایستگی او تولید می‌کند.

## 1. واحد اصلی: Mission

هر Mission حداقل شامل این اجزاست:
- Context
- Objective
- Constraints
- Actors
- Information State
- Decision Points
- Consequences
- Evidence Opportunities

## 2. Simulator باید Stateful باشد

جهان شبیه‌سازی وضعیت دارد و هر تصمیم وضعیت آینده را تغییر می‌دهد.

نمونه State:
- Cash / Runway
- NPS
- Churn
- Engineering Capacity
- Team Morale
- CEO Trust
- Key Client Risk

اصل:
> هر تصمیم، آینده Simulator را تغییر می‌دهد.

## 3. تصمیم فقط انتخاب گزینه نیست

کاندیدا باید بتواند پیش از تصمیم:
- سؤال بپرسد؛
- داده درخواست کند؛
- فرضیه بسازد؛
- اطلاعات تکمیلی جمع کند.

Simulator باید هم «چه تصمیمی گرفت» و هم «پیش از تصمیم چه چیزی خواست بداند» را ثبت کند.

## 4. Information Economy

اطلاعات محدود و هزینه‌دار است. کاندیدا باید بین منابع تحقیق، زمان، توجه و ظرفیت انتخاب کند.

مثال:
- مصاحبه مشتری
- Funnel Analysis
- جلسه با Sales
- Competitor Review
- Technical Spike

هدف: مشاهده اولویت‌بندی اطلاعات و کیفیت Judgment.

## 5. Event Engine

Simulator می‌تواند Eventهای مختلف وارد کند:
- Market Event
- Customer Event
- Team Event
- Technical Event
- Management Event
- Financial Event
- Regulatory Event

برخی Eventها ناشی از تصمیم‌های قبلی فرد هستند و صرفاً Random نیستند.

## 6. Behavioral Triggers

برخی Eventها عمداً برای مشاهده یک Competency طراحی می‌شوند.

نمونه:
- Trust: فرصت گزارش یا پنهان‌کردن یک خطا
- Ownership: مسئله‌ای خارج از شرح وظیفه که مأموریت را تهدید می‌کند
- Learning: مسئله ساختاری مشابه بعد از Feedback
- Leadership: عضو تیم کم‌عملکرد اما محبوب

## 7. Actor Engine

هر Actor باید State و ویژگی داشته باشد.

مثال مدیرعامل:
- Risk Tolerance
- Patience
- Strategic Priority
- Trust Level

مثال مشتری:
- Revenue Value
- Churn Probability
- Feature Sensitivity
- Relationship Quality

مثال عضو تیم:
- Skill
- Motivation
- Burnout
- Trust
- Performance

## 8. Consequence Engine

پیامدها چندبعدی و Trade-off محورند.

تصمیم خوب الزاماً همه شاخص‌ها را بهتر نمی‌کند.

مثال Feature سریع برای مشتری بزرگ:
- Revenue ↑
- Customer Trust ↑
- Technical Debt ↑
- Team Burnout ↑
- Roadmap Delay ↑

## 9. Decision Log

هر تصمیم مهم باید ثبت کند:
- Situation
- Available Information
- Requested Information
- Decision
- Reasoning
- Expected Outcome
- Actual Outcome
- Reflection

Decision Log یکی از منابع اصلی Evidence برای Judgment است.

## 10. Evidence Engine

جریان استاندارد:

**Simulation Event → Observed Behavior → Evidence → Competency**

Simulator نباید نتیجه را مستقیماً به Score ساده تبدیل کند.

## 11. Hidden Scoring

استانداردهای کلی شفاف‌اند، اما نگاشت دقیق رفتار به امتیاز نباید به‌گونه‌ای آشکار باشد که Rubric به‌سادگی قابل Game کردن شود.

هدف مشاهده رفتار طبیعی و تصمیم واقعی است.

## 12. Failure باید ممکن باشد

کاندیدا می‌تواند:
- محصول را شکست دهد؛
- مشتری را از دست بدهد؛
- بودجه را تمام کند؛
- اعتماد تیم را خراب کند.

شکست پایان تجربه نیست. Post-mortem و رفتار پس از شکست خود Evidence مهمی برای Learning و Accountability است.

## 13. Replay هوشمند

Replay نباید همان سؤال را تکرار کند.

ساختار مسئله مشابه، Context متفاوت:
- Retention در B2C
- Renewal در B2B SaaS

هدف سنجش Transfer of Learning و Behaviour Change است.

## 14. Difficulty Engine

سطوح پایه:
- Level 1 — Clear Mission
- Level 2 — Ambiguous Problem
- Level 3 — Competing Stakeholders
- Level 4 — Crisis & Scarcity
- Level 5 — Strategic Complexity

Difficulty باید با مدل Level/Scope شایستگی قابل نگاشت باشد.

## 15. Simulator اختصاصی هر کسب‌وکار

هسته مشترک:

**Mission Engine + Actor Engine + Event Engine + Consequence Engine + Evidence Engine**

هر کسب‌وکار یک **Business Simulation Pack** اختصاصی دارد که World Model، KPIها، Actors، Constraints و Event Library خود را تعریف می‌کند.

نمونه:
- Marketplace: Supply, Demand, Liquidity, Take Rate, Fraud
- SaaS: MRR, Churn, Expansion, CAC, Seats, Support Load
- Logistics: Capacity, SLA, Cost per Delivery, Failure Rate

## اصل جمع‌بندی

> در Simulator پرچم، نتیجه تصمیم مهم است؛ اما کیفیت تصمیم، نحوه رسیدن به آن، واکنش به پیامد و یادگیری پس از آن مهم‌تر است.
