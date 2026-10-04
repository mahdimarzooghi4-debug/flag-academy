# 20 — Capability 10: Product Economics

**وضعیت:** FINAL  
**تاریخ تثبیت:** 2026-10-04

## تعریف

> **Product Economics یعنی توانایی فهم و مدل‌کردن اینکه تصمیم‌های محصول چگونه به درآمد، هزینه، Margin، Cash، CAC، LTV، Retention، Pricing و در نهایت پایداری اقتصادی کسب‌وکار متصل می‌شوند.**

Product Manager لازم نیست CFO باشد؛ اما باید بفهمد هر تصمیم محصول چه چیزی را در ماشین اقتصادی شرکت حرکت می‌دهد.

## خروجی Capability

فرد باید بتواند:
- Business Model محصول را توضیح دهد؛
- Revenue Driverها و Cost Driverها را بشناسد؛
- Unit Economics را محاسبه و تفسیر کند؛
- Growth را از Profitable Growth جدا کند؛
- Pricing را به Value و Economics متصل کند؛
- اثر Retention بر LTV را بفهمد؛
- Trade-off میان Growth / Margin / Cash را ببیند؛
- Product Decision را به Economic Hypothesis تبدیل کند؛
- Forecast را با Assumption و Uncertainty ببیند، نه Fact قطعی.

## مدل اقتصادی پایه

زنجیره مفهومی:

**Customer Acquisition → Activation → Monetization → Retention → Expansion → Cost to Serve → Margin → Cash**

Economic Model باید متناسب با Business Model باشد.

### مثال SaaS
- MRR / ARR
- Churn
- Expansion
- CAC
- Payback

### مثال Marketplace
- GMV
- Take Rate
- Liquidity
- Contribution Margin
- Incentive Cost

### مثال Commerce
- AOV
- Purchase Frequency
- Gross Margin
- Fulfillment Cost
- Returns

اصل:
> یک مدل اقتصادی واحد برای همه کسب‌وکارها وجود ندارد؛ هر Business باید Economic Model متناسب با خودش داشته باشد.

## Mission Ladder

### M1 — Revenue Is Not Profit
Revenue بالا رفته اما Cost to Serve و Discount نیز رشد کرده‌اند.

هدف:
- تفکیک Revenue، Gross Margin و Contribution Margin
- جلوگیری از Revenue-only thinking

### M2 — CAC Trap
Acquisition رشد کرده اما Retention کاربران جدید ضعیف است.

هدف:
- بررسی CAC در برابر Expected LTV
- Payback Period
- جلوگیری از Growth-at-any-cost

### M3 — Retention Economics
یک Initiative Conversion را بالا می‌برد و دیگری Retention را.

هدف:
- فهم اثر Compound شده Retention
- اتصال Behavior → Retention → LTV → Economics

### M4 — Pricing Decision
چند مدل Pricing مطرح است.

هدف:
- Value Metric
- Willingness to Pay
- Cost Structure
- Customer Segment
- Sales Motion
- Expansion Potential

### M5 — Growth vs Margin
رشد سریع با Subsidy در برابر Economics بهتر با Growth آهسته‌تر.

هدف:
- فهم اینکه Subsidy می‌تواند Investment باشد یا فقط Scale کردن Loss
- اتصال به Strategy و Runway

### M6 — Cash Shock
Business روی کاغذ سودده است اما Cash مشکل دارد.

هدف:
- تفکیک Profit و Cash
- فهم Timing جریان پول
- اثر تصمیم محصول بر Working Capital / Cash Timing

### M7 — Economic Product Decision
فرد باید برای یک Initiative واقعی Economic Case بسازد.

هدف:
- Build Cost
- Revenue / Expansion Impact
- Support Complexity
- Adoption
- Margin
- Opportunity Cost

## Artifactهای اصلی

- Business Model Map
- Revenue Driver Tree
- Cost Driver Tree
- Unit Economics Model
- LTV / CAC Analysis
- Payback Analysis
- Contribution Margin View
- Pricing Hypothesis
- Economic Sensitivity Analysis
- Initiative Business Case
- Economic Post-mortem

اصل:
> مدل اقتصادی زمانی ارزش دارد که Decision را تغییر دهد؛ Spreadsheet به‌تنهایی Evidence نیست.

## Unit Economics

فرد باید Unit مناسب Business را تشخیص دهد.

نمونه Unit:
- Customer
- Order
- Delivery
- Seat
- Transaction
- Subscription
- Seller

سؤال:
> این Unit در طول عمرش چه Value ایجاد می‌کند و چه Costی دارد؟

اصل:
> **Scaling a broken unit economy scales the problem.**

## LTV و CAC

### CAC
بسته به Business Model می‌تواند شامل این موارد باشد:
- Advertising Cost
- Sales Cost
- Commission
- Incentive
- Onboarding Cost

### LTV
نباید با فرضیات غیرواقعی قطعی فرض شود.

اگر Retention هنوز نامطمئن است، LTV باید با Confidence پایین یا Range گزارش شود.

Parcham OS و Parcham AI باید برای Economic Metricها تا حد امکان این موارد را نگه دارند:
- Assumption
- Range
- Confidence
- Key Drivers

## Pricing

Pricing بخشی از Product Design است، نه صرفاً Finance یا Sales.

فرد باید بررسی کند:
- Value Metric چیست؟
- Buyer چه کسی است؟
- Segmentها چه تفاوتی در Willingness to Pay دارند؟
- Pricing چگونه رفتار محصول را تغییر می‌دهد؟
- آیا Pricing با Customer Value هم‌راستا است یا Misalignment ایجاد می‌کند؟

## Sensitivity Thinking

Business Case نباید یک Forecast واحد داشته باشد.

حداقل:
- Base
- Upside
- Downside

باید مشخص شود:
- اگر Adoption نصف شود چه؟
- اگر Cost دو برابر شود چه؟
- اگر Retention پایین‌تر باشد چه؟
- اگر Launch دیر شود چه؟

هدف:
> فهم اینکه کدام Assumption بیشترین اثر را بر Economics دارد.

## Red Flagها

- Revenue-only thinking
- Growth بدون Unit Economics
- LTV غیرواقعی
- نادیده‌گرفتن Cost to Serve
- Forecast به‌عنوان Fact
- Pricing فقط براساس Competitor
- فراموش‌کردن Cash Timing
- عدم لحاظ Opportunity Cost
- Sunk Cost justification
- Business Case صرفاً برای Approval
- «اگر Scale کنیم، بعداً Economics درست می‌شود» بدون Mechanism روشن

## نقش Parcham AI

### Learn Mode
آموزش:
- Business Model
- Unit Economics
- Margin
- LTV
- CAC
- Payback
- Pricing
- Cash

### Practice Mode
Challengeهای نمونه:
- اگر Retention 20٪ کمتر شود LTV چه می‌شود؟
- این Revenue چه Cost اضافی ایجاد می‌کند؟
- کدام Assumption بیشترین اثر را بر Business Case دارد؟

### Assessment Mode
AI نباید Initiative اقتصادی بهتر را انتخاب کند.

وظیفه:
- اجرای Economic World
- ارائه داده‌های مالی
- شبیه‌سازی Segment behavior
- Pricing reaction
- Cost consequence

### Real Project Mode
AI Economic Copilot می‌تواند هشدار دهد:
- Acquisition رشد کرده اما Contribution Margin بدتر شده
- Business Case بیش‌ازحد به Assumption کم‌اعتماد وابسته است
- Payback خارج از محدوده قابل قبول است
- Cost Driver جدید نادیده گرفته شده

مالک تصمیم Product Manager است.

## AI و Economic Forecasting

اصل:
> **AI Forecast حقیقت نیست؛ Scenario Generator است.**

هر Forecast تولیدشده با AI باید حداقل نشان دهد:
- Assumptions
- Range
- Confidence
- Key Drivers

نباید یک عدد دقیق و بی‌پشتوانه به‌عنوان حقیقت ارائه شود.

## اتصال به Simulator

تصمیم‌های Product Manager باید Economics جهان را در طول زمان تغییر دهند.

نمونه:
### Discount
- Acquisition ↑
- Conversion ↑
- Margin ↓
- Cash Burn ↑
- Price Sensitivity ↑

### کاهش Support
- Cost ↓
- Response Time ↑
- Churn Risk ↑

Simulator باید پیامدهای اقتصادی کوتاه‌مدت و بلندمدت را قابل مشاهده کند.

## شرایط عبور

برای عبور، باید در چند Context مختلف Evidence وجود داشته باشد که فرد:
- Business Model و Unit Economic مناسب را توضیح می‌دهد؛
- Revenue و Margin را جدا می‌کند؛
- CAC / LTV را با Assumptionهای روشن تحلیل می‌کند؛
- Cost to Serve و Cash Timing را لحاظ می‌کند؛
- Pricing را به Value و Economics وصل می‌کند؛
- Business Case را با Base / Upside / Downside می‌سازد؛
- حداقل یک تصمیم ظاهراً جذاب از نظر Growth را به‌دلیل Economics ضعیف رد یا اصلاح می‌کند؛
- و حداقل یک بار با تغییر Assumption کلیدی، Recommendation خود را تغییر می‌دهد.

## اصل فرهنگی

> **پرچمدار فقط محصولی نمی‌سازد که استفاده شود؛ محصولی می‌سازد که ارزش پایدار برای مشتری و کسب‌وکار ایجاد کند.**
