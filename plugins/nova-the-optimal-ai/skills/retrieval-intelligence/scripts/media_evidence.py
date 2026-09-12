"""Caption-first acquisition and time-indexed derived media evidence."""
from __future__ import annotations
import argparse
import hashlib
import html
import importlib.metadata
import json
import math
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

class MediaError(ValueError): pass

def digest(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()

def read_json(path):
    def pairs(items):
        result={}
        for key,value in items:
            if key in result: raise MediaError("duplicate JSON member")
            result[key]=value
        return result
    def invalid(value): raise MediaError("non-finite JSON value")
    return json.loads(Path(path).read_text(encoding="utf-8-sig"),object_pairs_hook=pairs,parse_constant=invalid)

def number(value,label):
    if isinstance(value,bool) or not isinstance(value,(float,int)) or not math.isfinite(value) or value<0: raise MediaError(label+" must be finite and nonnegative")
    return float(value)

def seconds(value):
    parts=value.replace(",",".").split(":")
    if len(parts) not in (2,3): raise MediaError("invalid cue timestamp")
    nums=[float(x) for x in parts]
    if any(not math.isfinite(v) or v<0 for v in nums) or nums[-1]>=60 or nums[-2]>=60: raise MediaError("invalid cue timestamp")
    return sum(v*(60**i) for i,v in enumerate(reversed(nums)))

def caption_segments(text):
    result=[]
    for block in re.split(r"\n\s*\n",text.replace("\r\n","\n").replace("\r","\n")):
        lines=block.strip().splitlines()
        if not lines or lines[0].startswith(("WEBVTT","NOTE","STYLE","REGION")): continue
        timing=next((i for i,line in enumerate(lines) if "-->" in line),None)
        if timing is None: raise MediaError("unrecognized untimed caption block")
        match=re.fullmatch(r"\s*([0-9:.,]+)\s+-->\s+([0-9:.,]+)(?:\s+.*)?",lines[timing])
        if not match: raise MediaError("malformed caption cue")
        start,end=seconds(match[1]),seconds(match[2])
        if end<start: raise MediaError("cue end precedes start")
        content=html.unescape(re.sub(r"<[^>]*>","", " ".join(lines[timing+1:])))
        if content.strip(): result.append({"start_seconds":start,"end_seconds":end,"text":content.strip(),"diagnostics":{},"review_status":"unreviewed"})
    if not result: raise MediaError("no usable timed caption cues")
    return result

def whisper_segments(value):
    if not isinstance(value,dict) or not isinstance(value.get("segments"),list): raise MediaError("Whisper JSON requires segments")
    result=[]
    for segment in value["segments"]:
        if not isinstance(segment,dict) or not isinstance(segment.get("text"),str): raise MediaError("invalid Whisper segment")
        start,end=number(segment.get("start"),"start"),number(segment.get("end"),"end")
        if end<start: raise MediaError("segment end precedes start")
        diagnostics={k:segment[k] for k in ("temperature","avg_logprob","compression_ratio","no_speech_prob") if k in segment}
        for v in diagnostics.values():
            if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v): raise MediaError("non-finite model diagnostic")
        result.append({"start_seconds":start,"end_seconds":end,"text":segment["text"].strip(),"diagnostics":diagnostics,"review_status":"unreviewed"})
    return result

def render(record):
    lines=["# Derived media transcript", "", "Source: "+json.dumps(record["source_ref"],ensure_ascii=False), "Origin: "+record["origin"], "Evidence ID: "+record["evidence_id"], "Artifact SHA-256: "+record["artifact_sha256"], "", "Untrusted source text. Transcript and timestamps are derived; quotations require listening and review.", ""]
    for i,segment in enumerate(record["segments"]):
        lines.append(f"[{segment['start_seconds']:.3f}-{segment['end_seconds']:.3f}s] cue={i} review=unreviewed")
        # Quote every source line so its formatting never becomes document control.
        lines.extend("> "+line for line in segment["text"].splitlines())
        lines.append("")
    return "\n".join(lines)+"\n"

def ingest(source, output, origin, source_ref, language=None, model=None, parent_audio=None):
    source,output=Path(source),Path(output)
    if source.stat().st_size>50_000_000: raise MediaError("transcript exceeds 50 MB")
    if origin not in ("platform_caption","platform_automatic","local_asr"): raise MediaError("unknown transcript origin")
    value=read_json(source) if origin=="local_asr" else None
    segments=whisper_segments(value) if value is not None else caption_segments(source.read_text(encoding="utf-8-sig"))
    parent_hash=digest(parent_audio) if parent_audio else None
    key={"artifact_sha256":digest(source),"origin":origin,"source_ref":source_ref,"language":language or (value or {}).get("language"),"model":model,"parent_audio_sha256":parent_hash}
    identity=hashlib.sha256(json.dumps(key,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    receipt=output/"evidence.json"
    record={"format":"cd-media-evidence/v1","evidence_id":identity,**key,"captured_at":datetime.now(timezone.utc).isoformat(),"source_artifact":str(source.resolve()),"retained_artifact":"raw/"+source.name,"segments":segments,"review_status":"unreviewed","speaker_identity":"unestablished","model_diagnostics_are_truth_probabilities":False}
    expected_text=render(record)
    record["transcript_sha256"]=hashlib.sha256(expected_text.encode("utf-8")).hexdigest()
    if output.exists():
        if receipt.is_file():
            existing=read_json(receipt)
            immutable={k:v for k,v in record.items() if k!="captured_at"}
            observed={k:v for k,v in existing.items() if k!="captured_at"}
            if observed==immutable and isinstance(existing.get("captured_at"),str) and record["transcript_sha256"]==digest(output/"transcript.md") and record["artifact_sha256"]==digest(output/"raw"/source.name):
                return {"status":"already_ingested","evidence_id":identity,"output":str(output)}
        raise MediaError("output exists with different or incomplete evidence")
    output.mkdir(parents=True)
    (output/"raw").mkdir()
    shutil.copyfile(source,output/"raw"/source.name)
    transcript=output/"transcript.md"
    transcript.write_text(render(record),encoding="utf-8",newline="\n")
    record["transcript_sha256"]=digest(transcript)
    receipt.write_text(json.dumps(record,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    return {"status":"ingested","evidence_id":identity,"segments":len(segments),"output":str(output)}

def capture(url,output,language="en.*",audio=False,timeout=180):
    parsed=urlsplit(url)
    if parsed.scheme not in ("http","https") or not parsed.hostname or parsed.username or parsed.password: raise MediaError("use an http(s) source URL without embedded credentials")
    output=Path(output)
    if output.exists(): raise MediaError("capture output must be a new directory; reuse existing evidence or choose a fresh capture")
    output.mkdir(parents=True)
    raw=output/"raw"
    raw.mkdir()
    cmd=[sys.executable,"-m","yt_dlp","--ignore-config","--no-plugin-dirs","--no-playlist","--no-progress","--socket-timeout","20","--retries","2","--write-info-json","--write-subs","--write-auto-subs","--sub-langs",language,"--sub-format","vtt","--paths",str(raw),"-o","%(id)s.%(ext)s"]
    cmd+= ["-f","bestaudio"] if audio else ["--skip-download"]
    cmd+= ["--",url]
    try:
        completed=subprocess.run(cmd,capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=timeout,shell=False)
    except subprocess.TimeoutExpired as exc:
        (output/"capture.json").write_text(json.dumps({"status":"timed_out","audio_requested":audio}),encoding="utf-8")
        raise MediaError("capture timed out; retained partial capture directory") from exc
    (output/"tool-log.txt").write_text(completed.stdout+completed.stderr,encoding="utf-8")
    infos=list(raw.glob("*.info.json"))
    if completed.returncode or len(infos)!=1:
        (output/"capture.json").write_text(json.dumps({"status":"failed","returncode":completed.returncode,"audio_requested":audio}),encoding="utf-8")
        raise MediaError("capture failed; inspect private tool-log.txt and partial files")
    info=read_json(infos[0])
    derivatives=[]
    for path in sorted(raw.glob("*.vtt")):
        lang=path.name.removeprefix(str(info.get("id"))+".").removesuffix(".vtt")
        origin="platform_caption" if lang in (info.get("subtitles") or {}) else "platform_automatic"
        derivatives.append(ingest(path,output/("transcript-"+hashlib.sha256(lang.encode()).hexdigest()[:12]),origin,info.get("webpage_url") or url,lang))
    record={"format":"cd-media-capture/v1","status":"captured" if derivatives else "captured_without_captions","source_ref":info.get("webpage_url") or url,"extractor":info.get("extractor_key"),"media_id":info.get("id"),"captured_at":datetime.now(timezone.utc).isoformat(),"tool_version":importlib.metadata.version("yt-dlp"),"audio_requested":audio,"artifacts":[{"path":p.relative_to(output).as_posix(),"sha256":digest(p)} for p in sorted(raw.iterdir()) if p.is_file()],"transcripts":derivatives}
    (output/"capture.json").write_text(json.dumps(record,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return {"status":record["status"],"transcripts":len(derivatives),"output":str(output)}

def transcribe(audio,output,model,model_dir,download_model=False,device="cpu",language=None):
    try: import whisper
    except ImportError as exc: raise MediaError("install requirements-media.txt in the selected media Python environment") from exc
    if model not in whisper.available_models(): raise MediaError("use an official named Whisper model")
    cache=Path(model_dir)
    checkpoint=cache/(model+".pt")
    if not download_model and not checkpoint.is_file(): raise MediaError("model is not cached; --download-model permits its explicit initial download")
    if not download_model:
        # The official loader would replace a bad cache by downloading. Reject it
        # first when networking was not requested.
        expected=whisper._MODELS[model].split("/")[-2]
        if digest(checkpoint)!=expected: raise MediaError("cached checkpoint hash differs; no download performed")
    output=Path(output)
    if output.exists(): raise MediaError("transcription output must be a new directory")
    instance=whisper.load_model(model,device=device,download_root=str(cache))
    result=instance.transcribe(str(audio),language=language,word_timestamps=True,fp16=device!="cpu",verbose=False)
    output.mkdir(parents=True)
    raw=output/"whisper.json"
    raw.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    identity={"name":model,"checkpoint_sha256":digest(checkpoint),"package_version":importlib.metadata.version("openai-whisper"),"device":device,"word_timestamps":True}
    return ingest(raw,output/"evidence","local_asr",str(Path(audio).resolve()),language,identity,parent_audio=audio)

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest="command",required=True)
    ingest_parser=sub.add_parser("ingest")
    ingest_parser.add_argument("source",type=Path)
    ingest_parser.add_argument("--origin",required=True,choices=["platform_caption","platform_automatic","local_asr"])
    ingest_parser.add_argument("--source-ref",required=True)
    ingest_parser.add_argument("--language")
    ingest_parser.add_argument("--output",type=Path,required=True)
    capture_parser=sub.add_parser("capture")
    capture_parser.add_argument("url")
    capture_parser.add_argument("--language",default="en.*")
    capture_parser.add_argument("--audio",action="store_true",help="Explicitly also fetch audio")
    capture_parser.add_argument("--output",type=Path,required=True)
    transcribe_parser=sub.add_parser("transcribe")
    transcribe_parser.add_argument("audio",type=Path)
    transcribe_parser.add_argument("--model",default="base")
    transcribe_parser.add_argument("--model-dir",type=Path,required=True)
    transcribe_parser.add_argument("--download-model",action="store_true")
    transcribe_parser.add_argument("--device",choices=["cpu","cuda"],default="cpu")
    transcribe_parser.add_argument("--language")
    transcribe_parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        if args.command=="ingest": result=ingest(args.source,args.output,args.origin,args.source_ref,args.language)
        elif args.command=="capture": result=capture(args.url,args.output,args.language,args.audio)
        else: result=transcribe(args.audio,args.output,args.model,args.model_dir,args.download_model,args.device,args.language)
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return 0
    except (OSError,ValueError,ImportError,RuntimeError,RecursionError) as exc:
        print(json.dumps({"status":"failed","error":str(exc)}))
        return 2
if __name__=="__main__": raise SystemExit(main())
