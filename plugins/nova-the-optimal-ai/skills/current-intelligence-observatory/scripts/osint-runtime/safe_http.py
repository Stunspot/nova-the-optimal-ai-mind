"""Bound Maigret receipt/decoding and verify TLS in its curl and aiohttp routes.

Native decompression stays off; the checked decoder sees only a bounded body.
These adapters are installed in Maigret checking/activation, not globally in aiohttp.
"""
from __future__ import annotations
import importlib.metadata
import importlib.util
import re
import zlib
import io
import ssl

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
    from curl_cffi import CurlOpt, CurlError
    from curl_cffi.curl import CURL_WRITEFUNC_ERROR
    from curl_cffi.requests import AsyncSession

    class SafeAsyncSession(AsyncSession):
        def __init__(self, *args, **kwargs):
            if kwargs.get("verify") is False:
                raise UnsafeDecoder("TLS verification cannot be disabled")
            super().__init__(*args, **kwargs)

        async def request(self, *args, **kwargs):
            patched_brotli()
            if kwargs.get("stream") or kwargs.get("content_callback") is not None:
                raise UnsafeDecoder("Use the guarded bounded response, without a custom stream or callback")
            if kwargs.get("verify") is False or self.verify is False:
                raise UnsafeDecoder("TLS verification cannot be disabled")
            # curl_options are applied after ordinary request options. Bind the
            # security controls here so a caller cannot silently undo them.
            if any(key in self.curl_options for key in (CurlOpt.WRITEFUNCTION, CurlOpt.WRITEDATA)):
                raise UnsafeDecoder("A custom curl body sink cannot bypass the response limit")
            self.curl_options.update({CurlOpt.HTTP_CONTENT_DECODING: 0,
                                      CurlOpt.SSL_VERIFYPEER: 1, CurlOpt.SSL_VERIFYHOST: 2})
            body = bytearray()
            exceeded = False
            def receive(chunk):
                nonlocal exceeded
                if len(body) + len(chunk) > MAX_BODY:
                    exceeded = True
                    return CURL_WRITEFUNC_ERROR
                body.extend(chunk)
                return len(chunk)
            kwargs["content_callback"] = receive
            kwargs["accept_encoding"] = "gzip, deflate, br"
            try:
                response = await super().request(*args, **kwargs)
            except CurlError as exc:
                if exceeded:
                    raise UnsafeDecoder("HTTP response exceeds the 16 MiB safety limit during receipt") from exc
                raise
            method = str(kwargs.get("method", args[0] if args else "GET")).upper()
            response.content = bytes(body)
            if method != "HEAD" and response.status_code not in (204, 304):
                response.content = decode_body(response.content, response.headers.get("content-encoding", ""))
            return response
    return SafeAsyncSession


class _DecodedBody:
    """Lazily read one bounded encoded body, then expose its bounded clear bytes.

    aiohttp's own stream applies backpressure before we consume it. Keeping
    native auto-decompression off bounds that buffer even for compressed bombs.
    Both response.read()/text()/json() and Maigret's content.read() use this path.
    """
    def __init__(self, raw, encoding, close):
        self.raw, self.encoding, self.close = raw, encoding, close
        self.buffer = None

    def __getattr__(self, name):
        return getattr(self.raw, name)

    async def _prepare(self):
        if self.buffer is not None:
            return
        data = bytearray()
        try:
            while True:
                block = await self.raw.read(min(65536, MAX_BODY - len(data) + 1))
                if not block:
                    break
                if len(data) + len(block) > MAX_BODY:
                    raise UnsafeDecoder("HTTP response exceeds the 16 MiB safety limit during receipt")
                data.extend(block)
            self.buffer = io.BytesIO(decode_body(bytes(data), self.encoding))
        except BaseException:
            self.close()
            raise

    async def read(self, n=-1):
        if n == 0:
            return b""
        await self._prepare()
        return self.buffer.read(n)

    async def readany(self):
        return await self.read()

    async def readexactly(self, n):
        import asyncio
        data = await self.read(n)
        if len(data) != n:
            raise asyncio.IncompleteReadError(data, n)
        return data

    async def readline(self):
        await self._prepare()
        return self.buffer.readline()

    async def readchunk(self):
        return await self.read(), False

    async def iter_chunks(self):
        if block := await self.read():
            yield block, False

    def read_nowait(self, n=-1):
        if self.buffer is None:
            raise UnsafeDecoder("Read the guarded response asynchronously before synchronous access")
        return self.buffer.read(n)

    def at_eof(self):
        return self.buffer is not None and self.buffer.tell() == len(self.buffer.getbuffer())

    async def iter_chunked(self, n):
        if n <= 0:
            raise ValueError("Chunk size must be positive")
        while block := await self.read(n):
            yield block

    async def iter_any(self):
        if block := await self.read():
            yield block

    def __aiter__(self):
        return self

    async def __anext__(self):
        line = await self.readline()
        if not line:
            raise StopAsyncIteration
        return line


def safe_aiohttp_session_class():
    patched_brotli()
    from aiohttp import ClientResponse, ClientSession

    class SafeResponse(ClientResponse):
        async def start(self, connection):
            result = await super().start(connection)
            encoding = self.headers.get("Content-Encoding", "")
            no_body = self.method == "HEAD" or self.status in (204, 304)
            if not no_body and self.content_length is not None and self.content_length > MAX_BODY:
                self.close()
                raise UnsafeDecoder("HTTP response exceeds the 16 MiB safety limit before receipt")
            self.content = _DecodedBody(self.content, "" if no_body else encoding, self.close)
            return result

    class SafeClientSession:
        def __init__(self, *args, **kwargs):
            kwargs["response_class"] = SafeResponse
            kwargs["auto_decompress"] = False
            self.session = ClientSession(*args, **kwargs)

        def __getattr__(self, name):
            return getattr(self.session, name)

        async def __aenter__(self):
            await self.session.__aenter__()
            return self

        async def __aexit__(self, *args):
            return await self.session.__aexit__(*args)

        async def close(self):
            await self.session.close()

        def request(self, method, url, **kwargs):
            patched_brotli()
            context = kwargs.get("ssl")
            if isinstance(context, ssl.SSLContext):
                if not context.check_hostname or context.verify_mode != ssl.CERT_REQUIRED:
                    raise UnsafeDecoder("TLS certificate and hostname verification are required")
            elif context not in (None, True):
                raise UnsafeDecoder("TLS certificate and hostname verification are required")
            else:
                context = ssl.create_default_context()
            # An explicit verified context overrides Maigret's insecure connector
            # context while retaining its DNS resolver, proxy and timeouts.
            kwargs["ssl"] = context
            kwargs["auto_decompress"] = False
            return self.session.request(method, url, **kwargs)

        def get(self, url, **kwargs): return self.request("GET", url, **kwargs)
        def post(self, url, **kwargs): return self.request("POST", url, **kwargs)
        def head(self, url, **kwargs): return self.request("HEAD", url, **kwargs)
        def put(self, url, **kwargs): return self.request("PUT", url, **kwargs)
        def delete(self, url, **kwargs): return self.request("DELETE", url, **kwargs)
        def patch(self, url, **kwargs): return self.request("PATCH", url, **kwargs)
        def options(self, url, **kwargs): return self.request("OPTIONS", url, **kwargs)
    return SafeClientSession


def install_maigret_transport():
    protected = safe_session_class()
    protected_aiohttp = safe_aiohttp_session_class()
    import maigret.checking
    import maigret.activation
    if not all(hasattr(maigret.checking, name) for name in ("CurlCffiAsyncSession", "ClientSession", "SimpleAiohttpChecker")) or not hasattr(maigret.activation, "ClientSession"):
        raise UnsafeDecoder("Unsupported Maigret transport interface; update the Observatory environment before network work")
    maigret.checking.CurlCffiAsyncSession = protected
    maigret.checking.ClientSession = protected_aiohttp
    maigret.activation.ClientSession = protected_aiohttp
