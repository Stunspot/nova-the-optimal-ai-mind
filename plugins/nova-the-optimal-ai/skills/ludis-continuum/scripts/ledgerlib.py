from __future__ import annotations
import json
from pathlib import Path
from typing import Any

STATUSES={"proposed","active_canon","disputed","superseded","quarantined","retired"}
VISIBILITY={"gm_only","player_safe"}

def load(path:Path)->dict[str,Any]:
    value=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value,dict): raise ValueError("ledger root must be an object")
    return value

def save(path:Path,value:dict[str,Any])->None:
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")

def validate(value:dict[str,Any])->list[str]:
    errors=[]
    for key in ("ludis_version","campaign","table_contract","objects","sessions","approvals","publication"):
        if key not in value: errors.append(f"missing top-level field: {key}")
    if value.get("ludis_version")!="0.1.0": errors.append("ludis_version must be 0.1.0")
    ids=set(); by_id={}
    for i,obj in enumerate(value.get("objects",[])):
        label=f"objects[{i}]"
        if not isinstance(obj,dict): errors.append(f"{label} must be an object"); continue
        oid=obj.get("id")
        if not isinstance(oid,str) or not oid: errors.append(f"{label}.id required")
        elif oid in ids: errors.append(f"duplicate id: {oid}")
        else: ids.add(oid); by_id[oid]=obj
        for field in ("kind","status","visibility","authority","provenance","confidence","tenure"):
            if field not in obj: errors.append(f"{label} missing {field}")
        if obj.get("status") not in STATUSES: errors.append(f"{label}.status invalid")
        if obj.get("visibility") not in VISIBILITY: errors.append(f"{label}.visibility invalid")
        if obj.get("status")=="active_canon" and obj.get("authority")!="gm_approved": errors.append(f"{label} active canon requires gm_approved authority")
    for oid,obj in by_id.items():
        for ref in obj.get("links",[]):
            if ref not in by_id: errors.append(f"broken link: {oid} -> {ref}")
        if obj.get("visibility")=="player_safe":
            for ref in obj.get("links",[]):
                if by_id.get(ref,{}).get("visibility")=="gm_only": errors.append(f"spoiler link: {oid} -> {ref}")
    seen={}
    for session in value.get("sessions",[]):
        when=session.get("scheduled_for")
        if when and when in seen: errors.append(f"session collision: {seen[when]} and {session.get('id')} at {when}")
        elif when: seen[when]=session.get("id")
    return errors
