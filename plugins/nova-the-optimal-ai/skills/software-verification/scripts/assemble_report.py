#!/usr/bin/env python3
"""Assemble a bounded verification report without dropping its evidence limits."""
from __future__ import annotations
import argparse,json
from pathlib import Path
from common.filesystem import load_data
from validate_manifest import validate

def inline(value):
    text=str(value).replace(chr(92),chr(92)*2).replace("|",chr(92)+"|").replace(chr(96),chr(92)+chr(96)).replace("\r"," ").replace("\n"," / ")
    return text.replace("<","&lt;").replace(">","&gt;")
def bullets(items):
    return "\n".join("- "+inline(x) for x in items) if items else "- None recorded"
def record(value):
    return "; ".join(f"{key}: {json.dumps(item, ensure_ascii=False) if isinstance(item,(list,dict)) else item}" for key,item in value.items())

def assemble(data: dict, root: Path | None = None) -> str:
    report=validate(data,root)
    if not report["valid"]:raise ValueError("manifest invalid: "+"; ".join(report["errors"]))
    target,scope,decision,review=(data[x] for x in ("target","scope","decision","review"))
    lines=["# Verification report","","## Decision","",f"**Status:** {inline(decision['status'])}",f"**Target:** {inline(target['name'])}",f"**Revision:** {inline(target['revision'])}",f"**Reviewer:** {inline(review['status'])}","","This is a technical verdict within the stated scope. It does not grant release, publication or other external-action authority.","","### Basis","",bullets(decision.get("basis",[])),"","## Scope"]
    for label,key in (("Included","included"),("Excluded","excluded"),("Constraints","constraints"),("Safety boundary","safety_boundary")):
        lines+=["","### "+label,"",bullets(scope.get(key,[]))]
    lines+=["","## Claims and uncertainty"]
    for key in ("observed","inferred","assumed","unresolved"):
        lines+=["","### "+key.capitalize(),"",bullets([record(x) for x in data["claim_custody"].get(key,[])])]
    lines+=["","## Critical invariants","",bullets([record(x) for x in data.get("invariants",[])]),"","## Risk register","",bullets([record(x) for x in data["risks"]]),"","## Scenarios and oracles","",bullets([record(x) for x in data["scenarios"]]),"","## Checks and applicability","",bullets([record(x) for x in data["tests"]]),"","## Execution and observation evidence"]
    for evidence in data["executions"]:
        lines+=["","### "+inline(evidence.get("id")),"",bullets([f"{key}: {json.dumps(value,ensure_ascii=False) if isinstance(value,(list,dict)) else value}" for key,value in evidence.items()])]
    lines+=["","## Findings","",bullets([record(x) for x in data["findings"]]),"","## Reviewer scope, findings and conditions","",bullets([f"{key}: {json.dumps(value,ensure_ascii=False) if isinstance(value,(list,dict)) else value}" for key,value in review.items()]),"","## Residual risk and follow-up","",bullets([record(x) for x in data["residual_risks"]]),"","## Authority still required","",bullets(decision.get("authority_required",[])),"","## Validation limits","",bullets(report.get("warnings",[])),"","File presence and a valid manifest do not authenticate a claimed observation. Supplied evidence remains supplied. Unexecuted checks and unobserved customer outcomes retain their explicit boundaries.",""]
    text="\n".join(lines)
    return text

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("manifest",type=Path);parser.add_argument("--output",required=True,type=Path);parser.add_argument("--evidence-root",type=Path);args=parser.parse_args()
    try:
        text=assemble(load_data(args.manifest),(args.evidence_root or args.manifest.parent).resolve())
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(text,encoding="utf-8");return 0
    except (OSError,ValueError,RuntimeError) as exc:parser.error(str(exc))
    return 2
if __name__=="__main__":raise SystemExit(main())