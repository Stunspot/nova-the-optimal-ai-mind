"""Rebuild the reproducible integrated MIND capability fingerprint."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SKILLS=ROOT/"skills"
OUTPUT=SKILLS/"augment-of-mind"/"assets"/"integrated-capability-fingerprint.json"
SELF_RELATIVE="assets/integrated-capability-fingerprint.json"
VERSIONS={"aesthetic-intelligence":"0.1.0","agent-dreaming":"0.1.2","agent-striving":"0.3.2","agentic-eros":"0.2.0","augment-of-mind":"2.1.1","capability-conductor":"0.1.0","capability-promotion":"0.1.0","cognitive-continuity":"0.1.3","creative-synthesis":"0.1.0","decision-intelligence":"0.1.0","deliberative-intelligence":"0.1.0","epistemic-regulation":"0.1.0","executive-function":"0.1.0","instrumental-agency":"0.1.0","kairos":"0.2.0","measurement-intelligence":"0.1.0","prosocial-influence":"0.1.0","sensemaking":"0.1.0","software-verification":"1.1.3","verification-reviewer":"1.1.3"}
def tree_sha256(name: str) -> tuple[str,int]:
    root=SKILLS/name
    files=[p for p in root.rglob("*") if p.is_file() and not (name=="augment-of-mind" and p.relative_to(root).as_posix()==SELF_RELATIVE) and "__pycache__" not in p.parts and p.suffix.lower() not in {".pyc",".pyo"}]
    digest=hashlib.sha256()
    for path in sorted(files,key=lambda p:p.relative_to(root).as_posix()):
        digest.update(path.relative_to(root).as_posix().encode("utf-8")); digest.update(b"\0"); digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest(),len(files)
def build() -> dict[str,object]:
    capabilities=[]
    for name in sorted(VERSIONS):
        tree_digest,file_count=tree_sha256(name)
        capabilities.append({"name":name,"version":VERSIONS[name],"integration_mode":"product-integration" if name=="augment-of-mind" else ("reminder-housekeeping-augment" if name=="capability-promotion" else ("faculty-derived-build" if name=="aesthetic-intelligence" else "faculty-suite-exact-copy")),"tree_file_count":file_count,"tree_sha256":tree_digest})
    aggregate_payload=json.dumps(capabilities,separators=(",",":"),ensure_ascii=False).encode("utf-8")
    return {"schema":"augment-of-mind-integrated-capability-fingerprint/v2","product_version":"2.1.1","capability_count":len(capabilities),"faculty_count":16,"attached_augment_count":3,"tree_algorithm":"sha256 over skill-relative UTF-8 POSIX path in ordinal exact-case order, one NUL byte, and raw 32-byte file sha256; cache files excluded","tree_self_exclusion":"augment-of-mind excludes assets/integrated-capability-fingerprint.json","aggregate_algorithm":"sha256 over compact UTF-8 JSON serialization of ordered capabilities","aggregate_sha256":hashlib.sha256(aggregate_payload).hexdigest(),"capabilities":capabilities}
def main() -> int:
    output=build(); OUTPUT.write_text(json.dumps(output,indent=2,ensure_ascii=False)+"\n",encoding="utf-8",newline="\n"); print(output["aggregate_sha256"]); return 0
if __name__=="__main__": raise SystemExit(main())
