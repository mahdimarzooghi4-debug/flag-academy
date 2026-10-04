# 38 — Stage v1: Ephemeral Acceptance Environment

**وضعیت:** FINAL  
**تاریخ تثبیت:** 2026-10-04

## تصمیم

Stage رسمی Parcham OS در v1 یک **Ephemeral Stage** داخل GitHub Actions است.

این تصمیم جایگزین نیاز به Persistent Paid Stage در فاز فعلی می‌شود، بدون اینکه معماری Application یا Domain تغییر کند.

## چرا

Persistent Stage فعلی به زیرساخت پولی وابسته می‌شود. برای جلوگیری از وابستگی مالی و در عین حال حفظ Production Parity در اجزای اصلی، Stage به‌صورت موقت و از صفر در هر اجرای Acceptance ساخته می‌شود.

## اجزای Stage

هر Run از محیط پاک این اجزا را بالا می‌آورد:

- PostgreSQL 16
- NATS JetStream
- Keycloak
- MinIO
- OpenTelemetry Collector
- FastAPI Backend
- Event Outbox Worker
- Read-model Projector
- React/Vite Frontend
- Playwright Browser Acceptance

## Stage Flow

**Clean Runner → Infrastructure → Migration → Seed → Workers → API → Frontend → Live OIDC → Browser Acceptance → Event/Projection Verification → Evidence Artifact → Destroy**

## Acceptance Gate

Stage فقط PASS است اگر:

1. Migration روی PostgreSQL خالی موفق شود.
2. Keycloak واقعی بالا بیاید و OIDC Authorization Code + PKCE کار کند.
3. Candidate Login کند و Candidate Home واقعی را ببیند.
4. Instructor Login کند و Instructor Home واقعی را ببیند.
5. Browser E2E سبز باشد.
6. Outbox eventها publish شده باشند.
7. Inbox consumer eventها را idempotently پردازش کرده باشد.
8. Candidate/Instructor read models ساخته شده باشند.
9. Evidence فایل Acceptance به‌عنوان GitHub Actions Artifact ذخیره شود.
10. محیط پس از پایان Run destroy شود.

## قواعد

- SQLite جای PostgreSQL Stage را نمی‌گیرد.
- دیتابیس پروژه دیگری برای Parcham Stage reuse نمی‌شود.
- Secret ثابت در Repository ذخیره نمی‌شود؛ Stage credentials در هر Run ephemeral تولید می‌شوند.
- Persistent Stage در آینده می‌تواند اضافه شود، اما نباید Contractهای Domain/Application را تغییر دهد.
- یک CI Unit/Build سبز به‌تنهایی Stage Acceptance نیست؛ Workflow مستقل Stage باید PASS باشد.

## Persistent Stage Later

وقتی زیرساخت مناسب در دسترس باشد، همان deployableها می‌توانند روی Persistent Stage اجرا شوند. Persistent Stage یک Infrastructure evolution است، نه بازطراحی Product یا Domain.
