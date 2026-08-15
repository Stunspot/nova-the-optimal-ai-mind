# Public GitHub Actions preflight - Signal Loom

Capacity: GitHub official documentation observed 2026-08-12 states standard GitHub-hosted runners are free and unlimited for public repositories. Signal Loom is public and both workflows use `ubuntu-latest`. Private-repository allowance exhaustion is not consumed. Reserve: 0 billable minutes.

Expansion: feature push line-ending + pull-request line-ending + merged-main line-ending + Pages deploy = `4 trigger-job copies x 1 matrix job x 1 attempt x 360 ceiling minutes x 0 billable multiplier = 0 billed minutes`; conservative raw runner ceiling total 1,440 minutes.

Decision: `PROCEED`.

Substitute: local product, package, site, link, and line-ending checks pass. This substitute does not prove: GitHub runner/image, trigger/matrix, permission/secret, artifact, Pages deployment, and required-status integration.

Authority: the user's public-repository remediation request authorizes branch publication, PR, protected merge after checks, and Pages deployment. No paid spend or rule weakening is authorized or needed.
