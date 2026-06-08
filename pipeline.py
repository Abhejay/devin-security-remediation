#!/usr/bin/env python3
"""
Devin Security Remediation Pipeline

Scans a GitHub repository for open CodeQL alerts, triages by severity,
creates GitHub Issues for high/critical findings, and triggers Devin
sessions to autonomously remediate each vulnerability.

Environment variables:
    DEVIN_API_KEY   Devin service user API key (cog_...)
    DEVIN_ORG_ID    Devin organization ID
    GH_TOKEN        GitHub personal access token with repo + security_events scope
    REPO            Target repository in owner/repo format (e.g. Abhejay/superset)
"""

import os
import json
import logging
import urllib.request
import urllib.error

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
log = logging.getLogger(__name__)

DEVIN_API_KEY = os.environ["DEVIN_API_KEY"]
DEVIN_ORG_ID  = os.environ["DEVIN_ORG_ID"]
GH_TOKEN      = os.environ["GH_TOKEN"]
REPO          = os.environ["REPO"]

SEVERITY_THRESHOLD = {"high", "critical"}

def gh_get(path):
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={
            "Authorization": f"Bearer {GH_TOKEN}",
            "Accept": "application/vnd.github+json",
        },
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def gh_post(path, data):
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        data=json.dumps(data).encode(),
        headers={
            "Authorization": f"Bearer {GH_TOKEN}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())

def create_devin_session(prompt, tags):
    payload = {
        "prompt": prompt,
        "tags": [t for t in tags if t],
        "session_type": "refactoring_and_optimization",
    }
    req = urllib.request.Request(
        f"https://api.devin.ai/v3/organizations/{DEVIN_ORG_ID}/sessions",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {DEVIN_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        log.error("Devin API %s: %s", e.code, e.read().decode())
        return None

def main():
    log.info("Starting Devin Security Remediation Pipeline for %s", REPO)

    # 1. Fetch open CodeQL alerts
    alerts = gh_get(f"/repos/{REPO}/code-scanning/alerts?state=open&per_page=100")
    log.info("Found %d open CodeQL alerts", len(alerts))

    # 2. Triage — keep only high / critical
    actionable = []
    for alert in alerts:
        severity = (
            alert.get("rule", {}).get("security_severity_level")
            or alert.get("rule", {}).get("severity", "")
        ).lower()

        if severity not in SEVERITY_THRESHOLD:
            log.info("Skipping alert #%s — severity '%s' below threshold", alert["number"], severity)
            continue

        actionable.append({
            "number":   alert["number"],
            "severity": severity.upper(),
            "rule":     alert["rule"]["description"],
            "file":     alert["most_recent_instance"]["location"]["path"],
            "line":     alert["most_recent_instance"]["location"]["start_line"],
            "url":      alert["html_url"],
        })

    log.info("Triage complete — %d alerts queued for remediation", len(actionable))

    # 3. For each actionable alert: create issue + trigger Devin
    for alert in actionable:
        file_name = alert["file"].split("/")[-1]
        title = f"[Security] {alert['rule']} in {file_name}"

        body = (
            "## Summary\n"
            f"CodeQL detected a {alert['severity']}-severity vulnerability: {alert['rule']}\n\n"
            "This issue was automatically created by the Devin Security Remediation Pipeline.\n\n"
            "## Finding\n"
            f"- Rule: {alert['rule']}\n"
            f"- File: `{alert['file']}`\n"
            f"- Line: {alert['line']}\n"
            f"- Severity: {alert['severity']}\n"
            f"- CodeQL Alert: {alert['url']}\n\n"
            "## Expected Fix\n"
            "Investigate the vulnerability at the exact file and line above.\n"
            "Apply the correct fix using best practices for this vulnerability type.\n"
            "Follow CONTRIBUTING.md, ensure all tests pass, "
            "and add a regression test before opening the PR.\n\n"
            "## Acceptance Criteria\n"
            f"- [ ] CodeQL alert #{alert['number']} resolved\n"
            "- [ ] Fix uses the correct approach for this vulnerability type\n"
            "- [ ] All existing tests pass\n"
            "- [ ] Regression test added\n"
        )

        issue = gh_post(
            f"/repos/{REPO}/issues",
            {"title": title, "body": body, "labels": ["devin-remediate"]},
        )
        issue_number = issue["number"]
        issue_url    = issue["html_url"]
        log.info("Created issue #%s: %s", issue_number, title)

        # 4. Build prompt for Devin
        prompt = (
            f"Fix the following security vulnerability in https://github.com/{REPO}\n\n"
            f"Issue #{issue_number}: {title}\n\n"
            f"Rule:          {alert['rule']}\n"
            f"File:          {alert['file']}\n"
            f"Line:          {alert['line']}\n"
            f"Severity:      {alert['severity']}\n"
            f"CodeQL Alert:  {alert['url']}\n"
            f"GitHub Issue:  {issue_url}\n\n"
            "Instructions:\n"
            "1. Clone the repository and investigate the vulnerability at the exact location above.\n"
            "2. Fix it using best practices — not a naive patch; use the proper library or pattern.\n"
            "3. Follow conventions in CONTRIBUTING.md.\n"
            "4. Ensure all existing tests pass and add a regression test.\n"
            "5. Open a PR describing what the vulnerability was, what you changed, "
            "and why it is safe to merge.\n"
            f"6. Link the PR to issue #{issue_number}.\n"
        )

        tags = ["auto-remediation", "codeql", f"issue-{issue_number}", alert["severity"].lower()]

        session = create_devin_session(prompt, tags)
        if session:
            sid = session.get("session_id", "unknown")
            log.info("Devin session created: %s", sid)
            log.info("Track at: https://app.devin.ai/sessions/%s", sid)
        else:
            log.error("Failed to create Devin session for issue #%s", issue_number)

    log.info("Pipeline complete — %d Devin sessions triggered.", len(actionable))


if __name__ == "__main__":
    main()
