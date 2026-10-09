# 98 — P23-09C live PostgreSQL + OIDC acceptance

**Date:** 2026-10-09  
**Scope:** Testing immutable Observation capture and current appointment authorization; *not* independent Evidence human review.

GitHub Actions E2E creates an ephemeral synthetic Session `00000000-0000-0000-0000-000000000243` in an isolated CI PostgreSQL database after its ordinary dev seed. This session is present-time only so a real Assessor's newly approved, active mandate and observed-at can both overlap its original Session interval; the original product/demo Session schedule remains unchanged.

In the pre-existing live Chromium + Keycloak + FastAPI + PostgreSQL scenario, Instructor is denied Observation POST; Assessor without mandate is denied GET; Academy Admin creates the exact class grant; actual Assessor concurrently sends two identical POST requests through real OIDC and expects one persisted Observation ID, reads exactly one row, confirms metadata/recording times, rejects changed replay and invalid person/session/class/future time, and then after Admin revocation must lose both read and write immediately.

The independent backend CI acceptance script queries the **same committed PostgreSQL records** after Playwright, checks exactly one append-only Observation and a single PERSON DomainEvent plus Outbox record with no private observed_fact, and uses privileged SQL UPDATE and DELETE inside savepoints to verify that PostgreSQL trigger blocks both operations. No mock in these checks, and the separate Unit tests remain intact.

Both scripts are CI-only and never included in `app.main` routes or operational seeds. The results are evidence of integrity and authentication behavior, not Academy Seed approval, formal Evidence acceptance, AI learning, Stage authorization or independent Code Review. The human reviewer and Evidence acceptance contract remains a separate bounded-context gate.
