"""Protect Maigret HTTP decoding while its fingerprinting libcurl embeds old Brotli.

libcurl receives HTTP_CONTENT_DECODING=0 for every request, including redirects.
A separately version-checked decoder handles the buffered response afterwards.
"""
from __future__ import annotations
import importlib.metadata
import importlib.util
import re
import zlib

MAX_BODY = 16 * 1024 * 1024

class UnsafeDecoder(RuntimeError):
    pass

def patched_brotli():
    try:
        version = importlib.metadata.version("Brotli")
        import brotli
    except (ImportError, importlib.metadata.PackageNotFoundError) as exc:
        raise UnsafeDecoder("Install the Observatory media safety dependency: Brotli==1.2.1; no request was sent.") from exc
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", version)
    if not match or tuple(map(int, match.groups())) < (1, 2, 1):
        raise UnsafeDecoder("Observatory requires Brotli 1.2.1 or newer before network work; no request was sent.")
    # aiohttp/requests can prefer this optional binding over Brotli. Refuse an
    # unsafe alternate before importing Maigret or sending any provider request.
    if importlib.util.find_spec("brotlicffi") is not None:
        try: alternate = importlib.metadata.version("brotlicffi")
        except importlib.metadata.PackageNotFoundError as exc:
            raise UnsafeDecoder("Unidentified brotlicffi binding; repair the Maigret environment before network work") from exc
        pieces = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)(?:\.(\d+))?", alternate)
        if not pieces or tuple(int(x or 0) for x in pieces.groups()) < (1, 2, 1, 0):
            raise UnsafeDecoder("Upgrade brotlicffi to 1.2.1.0 or remove it from the isolated Maigret environment before network work")
    return brotli

def decode_body(data, encoding):
    if len(data) > MAX_BODY:
        raise UnsafeDecoder("HTTP response exceeds the 16 MiB safety limit")
    for kind in reversed([x.strip().lower() for x in encoding.split(",") if x.strip()]):
        if kind == "identity":
            continue
        if kind == "br":
            decoder = patched_brotli().Decompressor()
            parts = [decoder.process(data, output_buffer_limit=MAX_BODY + 1)]
            size = len(parts[0])
            while not decoder.is_finished():
                if size > MAX_BODY:
                    raise UnsafeDecoder("Decoded response exceeds the 16 MiB safety limit")
                if decoder.can_accept_more_data():
                    raise UnsafeDecoder("Incomplete Brotli response")
                block = decoder.process(b"", output_buffer_limit=MAX_BODY - size + 1)
                if not block and not decoder.is_finished():
                    raise UnsafeDecoder("Incomplete Brotli response")
                parts.append(block)
                size += len(block)
            data = b"".join(parts)
        elif kind in ("gzip", "x-gzip", "deflate"):
            decoder = zlib.decompressobj(31 if kind in ("gzip", "x-gzip") else 15)
            try:
                decoded = decoder.decompress(data, MAX_BODY + 1)
            except zlib.error:
                if kind != "deflate":
                    raise
                decoder = zlib.decompressobj(-15)
                decoded = decoder.decompress(data, MAX_BODY + 1)
            if len(decoded) > MAX_BODY or decoder.unconsumed_tail:
                raise UnsafeDecoder("Decoded response exceeds the 16 MiB safety limit")
            if not decoder.eof or decoder.unused_data:
                raise UnsafeDecoder("Incomplete or trailing compressed HTTP response")
            data = decoded
        else:
            raise UnsafeDecoder("Unsupported HTTP content encoding: " + kind)
        if len(data) > MAX_BODY:
            raise UnsafeDecoder("Decoded response exceeds the 16 MiB safety limit")
    return data

def safe_session_class():
    patched_brotli()
    from curl_cffi import CurlOpt
    from curl_cffi.requests import AsyncSession

    class SafeAsyncSession(AsyncSession):
        def __init__(self, *args, **kwargs):
            options = dict(kwargs.pop("curl_options", None) or {})
            options[CurlOpt.HTTP_CONTENT_DECODING] = 0
            kwargs["curl_options"] = options
            super().__init__(*args, **kwargs)

        async def request(self, *args, **kwargs):
            patched_brotli()
            if kwargs.get("stream"):
                raise UnsafeDecoder("Observatory's guarded Maigret transport requires buffered responses")
            self.curl_options[CurlOpt.HTTP_CONTENT_DECODING] = 0
            kwargs["accept_encoding"] = "gzip, deflate, br"
            response = await super().request(*args, **kwargs)
            method = str(kwargs.get("method", args[0] if args else "GET")).upper()
            if method != "HEAD" and response.status_code not in (204, 304):
                response.content = decode_body(response.content, response.headers.get("content-encoding", ""))
            return response
    return SafeAsyncSession

def install_maigret_transport():
    protected = safe_session_class()
    import maigret.checking
    if not hasattr(maigret.checking, "CurlCffiAsyncSession"):
        raise UnsafeDecoder("Unsupported Maigret transport interface; update the Observatory environment before network work")
    maigret.checking.CurlCffiAsyncSession = protected
