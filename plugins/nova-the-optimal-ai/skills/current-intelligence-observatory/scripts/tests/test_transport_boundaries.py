"""Local-only response and TLS acceptance checks for both Maigret transports."""
import asyncio, gzip, importlib, json, shutil, ssl, subprocess, sys, tempfile, threading, unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "osint-runtime"))
import safe_http


class TransportBoundaries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.body = b'{"result":"useful evidence"}'
        cls.sent = {}
        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"
            def handle(self):
                try: super().handle()
                except (ConnectionResetError, ConnectionAbortedError): pass
            def do_GET(self):
                if self.path == "/redirect":
                    self.send_response(302); self.send_header("Location", "/gzip")
                    self.send_header("Content-Length", "0"); self.end_headers(); return
                if self.path in ("/large", "/chunked"):
                    self.send_response(200)
                    if self.path == "/large": self.send_header("Content-Length", str(1024 * 1024))
                    else: self.send_header("Transfer-Encoding", "chunked")
                    self.end_headers()
                    sent = 0
                    try:
                        for _ in range(1024):
                            block = b"x" * 1024
                            if self.path == "/chunked": block = b"400\r\n" + block + b"\r\n"
                            self.wfile.write(block); self.wfile.flush(); sent += 1024
                        if self.path == "/chunked": self.wfile.write(b"0\r\n\r\n")
                    except (ConnectionError, OSError): pass
                    cls.sent[self.path] = sent
                    return
                body = gzip.compress(b"x" * 65536) if self.path == "/bomb" else gzip.compress(cls.body) if self.path == "/gzip" else cls.body
                self.send_response(200)
                if self.path in ("/gzip", "/bomb"): self.send_header("Content-Encoding", "gzip")
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
            def do_POST(self):
                if int(self.headers.get("Content-Length", 0)): self.rfile.read(int(self.headers["Content-Length"]))
                self.do_GET()
            def do_HEAD(self):
                self.send_response(200); self.send_header("Content-Encoding", "br")
                self.send_header("Content-Length", "999999999"); self.end_headers()
            def log_message(self, *args): pass
        cls.http = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.http_thread = threading.Thread(target=cls.http.serve_forever, daemon=True); cls.http_thread.start()
        cls.url = "http://127.0.0.1:" + str(cls.http.server_port)
        cls.temp = tempfile.TemporaryDirectory(); cls.tls = None
        openssl = shutil.which("openssl") or (str(Path("C:/Program Files/Git/usr/bin/openssl.exe")) if Path("C:/Program Files/Git/usr/bin/openssl.exe").is_file() else None)
        if openssl:
            root = Path(cls.temp.name); cls.cert = root / "cert.pem"; key = root / "key.pem"
            subprocess.run([openssl, "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", str(key), "-out", str(cls.cert), "-days", "1", "-subj", "/CN=localhost", "-addext", "subjectAltName=DNS:localhost"], check=True, capture_output=True, timeout=30)
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); context.load_cert_chain(cls.cert, key)
            cls.tls = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
            cls.tls.socket = context.wrap_socket(cls.tls.socket, server_side=True)
            cls.tls_thread = threading.Thread(target=cls.tls.serve_forever, daemon=True); cls.tls_thread.start()
            cls.tls_url = "https://localhost:" + str(cls.tls.server_port)

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown(); cls.http.server_close(); cls.http_thread.join()
        if cls.tls: cls.tls.shutdown(); cls.tls.server_close(); cls.tls_thread.join()
        cls.temp.cleanup()

    def test_aiohttp_valid_json_gzip_redirect_head_and_direct_content(self):
        async def check():
            async with safe_http.safe_aiohttp_session_class()() as session:
                for endpoint in ("/plain", "/gzip", "/redirect"):
                    async with session.get(self.url + endpoint) as response:
                        self.assertEqual(await response.json(), {"result": "useful evidence"})
                async with session.get(self.url + "/gzip") as response:
                    self.assertEqual(await response.content.read(), self.body)
                async with session.head(self.url + "/plain") as response:
                    self.assertEqual(await response.read(), b"")
        asyncio.run(check())

    def test_both_routes_limit_declared_chunked_and_compressed_bodies(self):
        async def check():
            with patch.object(safe_http, "MAX_BODY", 4096):
                async with safe_http.safe_session_class()() as curl:
                    for endpoint in ("/large", "/chunked", "/bomb"):
                        with self.assertRaises(safe_http.UnsafeDecoder, msg="curl " + endpoint):
                            await curl.get(self.url + endpoint)
                async with safe_http.safe_aiohttp_session_class()() as aio:
                    for endpoint in ("/large", "/chunked", "/bomb"):
                        with self.assertRaises(safe_http.UnsafeDecoder, msg="aiohttp " + endpoint):
                            async with aio.get(self.url + endpoint) as response:
                                await response.content.read()
        asyncio.run(check())

    def test_curl_receipt_limit_aborts_before_full_download(self):
        # The callback receives at most a normal curl chunk beyond the cap and
        # never appends it; no complete response reaches the decoder.
        async def check():
            with patch.object(safe_http, "MAX_BODY", 4096), patch.object(safe_http, "decode_body") as decode:
                async with safe_http.safe_session_class()() as session:
                    with self.assertRaises(safe_http.UnsafeDecoder): await session.get(self.url + "/chunked")
                decode.assert_not_called()
        asyncio.run(check())

    def test_bad_tls_is_rejected_but_explicit_trusted_ca_is_supported(self):
        if not self.tls: self.skipTest("OpenSSL unavailable for local test certificate")
        from aiohttp import ClientConnectorCertificateError, TCPConnector
        from curl_cffi import CurlError
        async def check():
            # The exact upstream insecure connector remains present: our per-
            # request verified SSL context must supersede it.
            insecure = ssl.create_default_context(); insecure.check_hostname = False; insecure.verify_mode = ssl.CERT_NONE
            async with safe_http.safe_aiohttp_session_class()(connector=TCPConnector(ssl=insecure)) as session:
                with self.assertRaises(ClientConnectorCertificateError):
                    async with session.get(self.tls_url): pass
                trusted = ssl.create_default_context(cafile=str(self.cert))
                async with session.get(self.tls_url, ssl=trusted) as response:
                    self.assertEqual(await response.read(), self.body)
                with self.assertRaises(ClientConnectorCertificateError):
                    async with session.get(self.tls_url.replace("localhost", "127.0.0.1"), ssl=trusted): pass
            async with safe_http.safe_session_class()() as session:
                with self.assertRaises(CurlError): await session.get(self.tls_url)
                self.assertEqual((await session.get(self.tls_url, verify=str(self.cert))).content, self.body)
                with self.assertRaises(CurlError): await session.get(self.tls_url.replace("localhost", "127.0.0.1"), verify=str(self.cert))
        asyncio.run(check())

    def test_no_per_request_tls_or_decoder_bypass(self):
        async def check():
            async with safe_http.safe_aiohttp_session_class()() as session:
                with self.assertRaises(safe_http.UnsafeDecoder): session.get(self.url, ssl=False)
                async with session.get(self.url + "/gzip", auto_decompress=True) as response:
                    self.assertEqual(await response.content.read(), self.body)
            async with safe_http.safe_session_class()() as session:
                with self.assertRaises(safe_http.UnsafeDecoder): await session.get(self.url, verify=False)
        asyncio.run(check())

    def test_actual_maigret_both_checker_routes_are_guarded(self):
        import logging
        import maigret.checking as checking
        safe_http.install_maigret_transport()
        async def check():
            for checker_class in (checking.SimpleAiohttpChecker, checking.CurlCffiChecker):
                checker = checker_class(logger=logging.getLogger("fixture"))
                checker.prepare(self.url + "/gzip", timeout=5)
                result = await checker.check()
                self.assertEqual(result[:2], (self.body.decode(), 200))
                self.assertIsNone(result[2])
                with patch.object(safe_http, "MAX_BODY", 4096):
                    checker.prepare(self.url + "/chunked", timeout=5)
                    result = await checker.check()
                    self.assertEqual(result[1], 0); self.assertIsNotNone(result[2])
                if self.tls:
                    checker.prepare(self.tls_url, timeout=5)
                    result = await checker.check()
                    self.assertEqual(result[1], 0); self.assertIsNotNone(result[2])
        asyncio.run(check())

    def test_site_activation_uses_guarded_body_and_preserves_useful_result(self):
        import logging
        from types import SimpleNamespace
        import maigret.activation as activation
        safe_http.install_maigret_transport()
        async def check():
            site = SimpleNamespace(headers={}, activation={"url": self.url + "/gzip", "src": "result", "dst": "x-fixture"})
            await activation.ParsingActivator.twitter(site, logging.getLogger("fixture"), timeout=5)
            self.assertEqual(site.headers["x-fixture"], "useful evidence")
            site.activation["url"] = self.url + "/chunked"
            with patch.object(safe_http, "MAX_BODY", 4096), self.assertRaises(safe_http.UnsafeDecoder):
                await activation.ParsingActivator.twitter(site, logging.getLogger("fixture"), timeout=5)
        asyncio.run(check())

if __name__ == "__main__": unittest.main()
