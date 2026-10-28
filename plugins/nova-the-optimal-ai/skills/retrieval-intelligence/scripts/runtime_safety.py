"""Fail before media network work when a selected native Brotli decoder is unsafe."""
from __future__ import annotations
import importlib.util, importlib.metadata, json, re, shutil, subprocess

class UnsafeRuntime(RuntimeError):pass

def release(value):
    match=re.fullmatch(r"(\d+)\.(\d+)\.(\d+)(?:\.(\d+))?",value)
    if not match:raise UnsafeRuntime('Unrecognized decoder version; use the documented media environment')
    return tuple(int(x or 0) for x in match.groups())

def check_decoders():
    found={}
    for module,package,floor in (('brotli','Brotli',(1,2,1,0)),('brotlicffi','brotlicffi',(1,2,1,0))):
        if importlib.util.find_spec(module) is None:continue
        try:value=importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError as exc:raise UnsafeRuntime('Unidentified '+module+' decoder; recreate the documented media environment') from exc
        if release(value)<floor:raise UnsafeRuntime('Unsafe '+package+' '+value+'; install Brotli>=1.2.1 or brotlicffi>=1.2.1.0 before capture')
        found[package]=value
    if importlib.util.find_spec('curl_cffi') is not None:
        from curl_cffi import Curl
        curl=Curl()
        try:value=curl.version().decode('ascii','replace')
        finally:curl.close()
        match=re.search(r'\bbrotli/(\d+\.\d+\.\d+)\b',value)
        if match and release(match.group(1))<(1,2,1,0):
            raise UnsafeRuntime('curl_cffi embeds unsafe Brotli '+match.group(1)+'; use a separate media environment without curl_cffi')
        if 'brotli/' in value.lower() and not match:raise UnsafeRuntime('Cannot identify curl_cffi Brotli; use the documented media environment')
        found['curl_cffi']=value
    return found

def select_javascript_runtime():
    deno=shutil.which('deno')
    if deno:
        # yt-dlp's EJS runtime contract requires Deno 2.3.0 or newer.
        # This is a compatibility probe, not a claim about every Deno decoder.
        try:
            result=subprocess.run([deno,'--version'],capture_output=True,text=True,timeout=15,check=True)
            match=re.search(r'^deno (\d+\.\d+\.\d+)(?:[ \t]|$)',result.stdout,re.MULTILINE)
            if not match or release(match.group(1))<(2,3,0,0):
                raise UnsafeRuntime('Selected Deno is unidentified or older than 2.3.0; choose a supported Deno before capture')
        except (OSError,subprocess.SubprocessError) as exc:
            raise UnsafeRuntime('Cannot verify selected Deno runtime; repair that runtime before capture') from exc
        return ['--no-js-runtimes','--js-runtimes','deno:'+deno]
    node=shutil.which('node')
    if not node:return ['--no-js-runtimes']
    try:
        result=subprocess.run([node,'-e','console.log(JSON.stringify({node:process.versions.node,fix:require("node:zlib").constants.BROTLI_DECODER_ERROR_FORMAT_BLOCK_SWITCH}))'],capture_output=True,text=True,timeout=15,check=True)
        value=json.loads(result.stdout)
    except (OSError,subprocess.SubprocessError,ValueError) as exc:raise UnsafeRuntime('Cannot verify selected Node runtime; install Node 24.22.1+ or use Deno') from exc
    if value.get('fix')!=-17:raise UnsafeRuntime('Selected Node runtime has an unsafe Brotli decoder; install Node 24.22.1+ or use Deno')
    return ['--no-js-runtimes','--js-runtimes','node:'+node]

def media_runtime():
    decoders=check_decoders()
    return {'decoders':decoders,'javascript':select_javascript_runtime()}
