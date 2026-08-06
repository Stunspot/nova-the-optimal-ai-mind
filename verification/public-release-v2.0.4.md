# Nova + MIND Free 2.0.4 public release verification

The public `v2.0.4` release was built from finalized `main` by `.github/workflows/publish-v2-0-4.yml` after the semantic Arm's Reach repair entered the default branch.

## Published assets

- `nova-mind-free-v2.0.4.zip`
- `nova-mind-free-v2.0.4.zip.sha256`
- `release-manifest.json`
- `SHA256SUMS.txt`

## Final archive

- Product version: `2.0.4`
- Nova plugin version: `2.0.1`
- MIND plugin version: `2.1.2`
- Nova skills: `21`
- MIND skills: `20`
- Total portable skill packages: `41`
- MIND Faculties: `16`
- Reminder cards: `41`
- Reminder vectors: `246`
- Archive size: `77,057,899` bytes
- Archive SHA-256: `90b33821fafa6d7b36356326c4b782c5993217fbf2060ef3b732c78339cf342d`

## Verification gates

The final publication run completed all of the following before publishing the public release assets:

1. seven semantic Arm's Reach regression tests;
2. regenerated integrated capability fingerprint verification;
3. source package verification;
4. deterministic customer package build;
5. release-tree and portable-package verification;
6. publication of the ZIP, checksum, release manifest, and checksum manifest;
7. upload of the same evidence packet as a GitHub Actions artifact.

- Source revision and release target: `5f3557d4205ced17d297149c4986a32984ddcf82`
- Publication workflow run: `31129545461`
- Publication job: `92715105290`
- Evidence artifact ID: `8975555585`
- Evidence artifact size: `76,669,076` bytes
- Evidence artifact digest: `sha256:e3245be8feaf8e622968fab95b5c3b87d0d700dc04408e8a6a8dfaa8dda675df`

The workflow reported success for semantic regressions, source regeneration and verification, deterministic package build and verification, GitHub Release publication, and evidence upload. The downloaded evidence artifact independently reproduced the published archive checksum above and contained the expected `2.0.4` release manifest with Nova `2.0.1` and MIND `2.1.2`.

## Post-publication cleanup

After publication evidence was recorded, the version-specific publisher was removed from the default branch. This record preserves the authoritative run, job, artifact, source revision, and archive identities without leaving a served one-release trigger active.
