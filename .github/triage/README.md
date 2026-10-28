# Issue triage

`.github/workflows/issue-triage.yml` labels a new issue, asks for what the form requires and is missing, links likely duplicates and matches `[RED]` log lines against `docs/agents/symptoms.md`. It uses the GitHub Copilot CLI, so it runs on a Copilot subscription (about one premium request per issue).

- **Setup:** add the Actions secret `COPILOT_TOKEN`: a fine-grained personal access token with only the account permission "Copilot Requests", from an account with Copilot. Without it the workflow skips with a notice. An optional repository variable `TRIAGE_MODEL` picks the model.
- **Labels it uses:** `game`, `build`, `launcher`, `ios`, `mac`, `idea`, `question`, `needs-info`, `duplicate`. It only adds those that exist; it never creates one. `no-triage` on an issue skips it.
- **Re-run:** Actions > issue-triage > Run workflow with the issue number. The earlier triage comment is updated.
- **Security:** `gather` (read-only, no secrets) writes the data; `analyze` (no permissions, the model token) can only read in an empty directory; `apply` (`issues: write`, no model token) accepts only JSON of the fixed shape: labels from the list, at most one comment with no @-mention, HTML or link except github.com/LNPANDY/NX2Apple and github.com/seedds/nxnative, duplicates that are real candidates. It never closes or edits an issue.
- **Scripts:** `.github/scripts/triage_*.py` (standard library only), tests in `.github/scripts/tests`, the prompt in `.github/triage/prompt.md`.
