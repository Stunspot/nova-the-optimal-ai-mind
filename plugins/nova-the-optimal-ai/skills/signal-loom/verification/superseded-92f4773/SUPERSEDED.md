# Superseded candidate evidence

Candidate `92f47735896b5baa3d37132880f5ea129079e189`, governed fingerprint `cbc7288c96cc10b0364583cdb9f72b1f94f6179f7a39c930e95db0a26157e29e`.

Hesperos and source/static accessibility passed. The subsequent independent TestForge challenge rejected the candidate because a concurrent source mutation could produce an archive whose payload did not match its manifest, and an interruption immediately after project-manifest replacement could leave the project manifest advanced while deleting the final archive. The single-artifact redesign in `9b8f116f32098db2420ccb51ea5ee7aa8e0fbd43` and final wording commit `17ed4f30975081b4a020dd8e28e6a35eb0edda1d` invalidate these receipts for the final candidate.