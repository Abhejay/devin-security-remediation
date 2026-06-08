# Devin Security Remediation Pipeline

An event-driven automation that scans a GitHub repository for open CodeQL security alerts, triages them by severity, creates structured GitHub Issues, and triggers Devin sessions to autonomously remediate each vulnerability — producing pull requests your engineers only need to review.

## How it works

```
CodeQL Alert
    │
    ▼
Triage Gate ──── severity < high ──▶ Skip
    │
    ▼
GitHub Issue (auto-created with full context)
    │
    ▼
Devin Session (autonomous engineer)
    │  • Clones the repo
    │  • Investigates the vulnerability
    │  • Applies the correct fix
    │  • Writes regression tests
    │  • Opens a PR with explanation
    ▼
Pull Request → Human Review → Merge
```

**Devin is the core primitive** — it does the engineering judgment work that no other tool does: identifying the right fix pattern, checking existing dependencies, writing tests, and documenting why the fix is correct. The pipeline orchestrates everything around it.

## Prerequisites

- [Devin](https://app.devin.ai) account with a service user created (Settings → Service Users)
- GitHub repository with CodeQL code scanning enabled
- GitHub personal access token with `repo` and `security_events` scopes
- Docker installed locally

## Quick start

**1. Clone this repo**
```bash
git clone https://github.com/YOUR_USERNAME/devin-security-remediation
cd devin-security-remediation
```

**2. Create a `.env` file**
```bash
DEVIN_API_KEY=cog_your_service_user_token
DEVIN_ORG_ID=your_devin_org_id
GH_TOKEN=your_github_personal_access_token
REPO=owner/repository
```

**3. Build and run**
```bash
docker build -t devin-remediation .
docker run --env-file .env devin-remediation
```

Or with docker-compose:
```bash
docker compose up
```

The pipeline will scan your repo's CodeQL alerts, create GitHub Issues for High and Critical findings, and spin up a Devin session for each one.

## GitHub Actions (production)

The `devin-remediation.yml` workflow in the Apache Superset fork automates this end-to-end. Add these secrets to your repository:

| Secret | Description |
|--------|-------------|
| `DEVIN_API_KEY` | Devin service user token (`cog_...`) |
| `DEVIN_ORG_ID` | Devin organization ID |

The `Devin Security Remediation Pipeline` workflow (`auto-create-issues.yml`) runs on demand and fans out sessions for all high/critical findings in parallel.

The `Devin Auto-Remediation` workflow (`devin-remediation.yml`) fires whenever an issue is labeled `devin-remediate`, enabling manual escalation of individual findings.

## Devin configuration

Three layers of context are configured in Devin to ensure consistent, production-quality output:

**Knowledge** (Settings → Knowledge): Superset-specific context including preferred sanitization libraries (`nh3`), test commands, and contribution standards. Recalled automatically based on trigger descriptions.

**Playbook** (Settings → Playbooks): Step-by-step task instructions for security remediation — investigate root cause, use existing dependencies, write regression tests, document the fix. Loaded for every session.

**Blueprint** (Settings → Repositories): Pre-configured environment snapshot with all Superset dependencies pre-installed so Devin spends time fixing code, not setting up.

## Observability

The `Security Remediation Observability Report` workflow (`security-observability-report.yml`) runs every Monday and posts a metrics report to a pinned GitHub Issue:

- Alerts scanned and triaged
- Sessions created and completed
- PRs opened and merged
- MTTR (alert → PR)
- Estimated engineering hours saved

## Repository links

- **This solution**: [github.com/YOUR_USERNAME/devin-security-remediation](https://github.com/YOUR_USERNAME/devin-security-remediation)
- **Apache Superset fork**: [github.com/Abhejay/superset](https://github.com/Abhejay/superset)
  - [Open issues](https://github.com/Abhejay/superset/issues) — automatically created by the pipeline
  - [Pull requests](https://github.com/Abhejay/superset/pulls) — opened by Devin
  - [Security alerts](https://github.com/Abhejay/superset/security/code-scanning) — 87 alerts scanned, 7 high/critical remediated
  - [Hero PR #2](https://github.com/Abhejay/superset/pull/2) — merged fix replacing regex HTML sanitization with `nh3`

## Why Devin

Every existing tool in this space either finds vulnerabilities (CodeQL, Dependabot) or helps a human fix them (GitHub Copilot). None of them autonomously do the engineering judgment work — reading the codebase, choosing the right library, writing tests, and explaining why the fix is correct.

Devin does. That's not a productivity improvement. It's risk reduction that happens whether or not your team has capacity.
