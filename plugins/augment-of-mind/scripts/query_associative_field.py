"""Compile one MIND arm's-reach field through the portable H0 adapter."""

from __future__ import annotations

import argparse, hashlib, json, sys, urllib.request, uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mind_core import MindCore
from mind_core.constants import PROTOCOL_VERSION
from mind_core.util import canonical_json, timestamp

DEFAULT_DATABASE = Path.home() / ".codex" / "data" / "stores" / "mind_core.sqlite"
DEFAULT_MODEL = "qwen3-embedding:0.6b"

def embed(text: str, model: str, url: str) -> list[float]:
    body = json.dumps({"model":model,"input":text}).encode("utf-8")
    request = urllib.request.Request(url.rstrip("/")+"/api/embed",data=body,headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(request,timeout=180) as response:
        payload=json.load(response)
    values=payload.get("embeddings")
    if not isinstance(values,list) or len(values)!=1 or not isinstance(values[0],list):
        raise RuntimeError("embedding provider returned an invalid response")
    return values[0]

def parser() -> argparse.ArgumentParser:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("text",nargs="?")
    p.add_argument("--input-file",type=Path)
    p.add_argument("--hint",action="append",default=[])
    p.add_argument("--database",type=Path,default=DEFAULT_DATABASE)
    p.add_argument("--model",default=DEFAULT_MODEL)
    p.add_argument("--ollama-url",default="http://127.0.0.1:11434")
    p.add_argument("--anchor-kind",default="task")
    p.add_argument("--agent-instance-id",default="agent:mind-h0")
    p.add_argument("--field-only",action="store_true")
    return p

def main() -> int:
    args=parser().parse_args()
    if (args.text is None)==(args.input_file is None):
        raise SystemExit("supply exactly one text argument or --input-file")
    text=args.text if args.text is not None else args.input_file.read_text(encoding="utf-8")
    if not text.strip():
        raise SystemExit("anchor text must be non-empty")
    vector=embed(text,args.model,args.ollama_url)
    now=datetime.now(timezone.utc)
    session_id="session:mind-h0:"+uuid.uuid4().hex
    with MindCore(args.database) as core:
        snapshot=core.reminders.active_snapshot_binding()
        if not snapshot["current"]:
            raise RuntimeError("active associative snapshot is not current")
        if args.model != snapshot["model_id"]:
            raise RuntimeError("requested model does not match the active snapshot profile")
        core.hosts.handshake({
            "agent_instance_id":args.agent_instance_id,"host_session_id":session_id,
            "host_id":"host:codex-desktop-h0","external_session_id":session_id,"session_epoch":1,
            "persona_id":None,"profile_id":"profile:mind-associative-h0","adapter_id":"adapter:mind-h0-cli",
            "adapter_version":"1.0.0","protocol_version":PROTOCOL_VERSION,"declared_conformance_level":"H0",
            "catalog_snapshot_hash":snapshot["snapshot_digest"],
            "catalog_snapshot_expires_at":timestamp(now+timedelta(minutes=15)),
            "permission_observation_hash":hashlib.sha256(b"h0-permission-not-observed").hexdigest(),
            "authentication_observation_hash":hashlib.sha256(b"h0-authentication-not-observed").hexdigest(),
            "observed_at":timestamp(now),"expires_at":timestamp(now+timedelta(minutes=15)),
        })
        token=core.reminders.issue_session_capability(args.agent_instance_id,session_id)["session_capability"]
        anchor={"anchor_id":"anchor:current","anchor_kind":args.anchor_kind,"vector":vector}
        if args.hint:
            anchor["lexical_hints"]=args.hint
        result=core.reminders.neighborhood(token,snapshot["associative_index_snapshot_id"],[anchor])
    if args.field_only:
        print(result["representations"]["canonical"]["text"])
    else:
        print(canonical_json(result))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
