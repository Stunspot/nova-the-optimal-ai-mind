# Nova + MIND Free 2.0.3 public release verification

The public `v2.0.3` release was built from finalized `main` by `.github/workflows/publish-public-release.yml`.

## Published assets

- `nova-mind-free-v2.0.3.zip`
- `nova-mind-free-v2.0.3.zip.sha256`
- `release-manifest.json`
- `SHA256SUMS.txt`

## Final archive

- Product version: `2.0.3`
- Nova plugin version: `2.0.0`
- MIND plugin version: `2.1.1`
- Nova skills: `21`
- MIND skills: `20`
- Total portable skill packages: `41`
- MIND Faculties: `16`
- Reminder cards: `41`
- Reminder vectors: `246`
- Archive SHA-256: `ee5049a2a3c14baedd8fbdb49ee5e107f6c056b719ae64b68146081b9e21020a`

## Verification gates

The final publication run completed all of the following before replacing the public release assets:

1. source package verification;
2. deterministic customer package build;
3. release-tree verification, including portable ZIP shape;
4. MIND version-graph and integrated-fingerprint checks;
5. absence of the removed bundled MCP registration and runtime paths;
6. publication of the ZIP, checksum, release manifest, and checksum manifest;
7. upload of the same evidence packet as a GitHub Actions artifact.

- Publication workflow run: `30968698282`
- Publication job: `92188154541`
- Evidence artifact ID: `8915705308`
- Evidence artifact SHA-256: `063ce2f9bb360e7b0cae418170d0d703f0b5e9de687c522ceb8ef5e9b2cf0a45`

The release workflow checked out finalized `main`, reported source verification `PASS`, built the archive above, reported release verification `PASS` with no errors, and completed the GitHub Release upload successfully.
