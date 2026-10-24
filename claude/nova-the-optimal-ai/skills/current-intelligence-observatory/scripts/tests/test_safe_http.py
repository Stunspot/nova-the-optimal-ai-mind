import asyncio, gzip, importlib.util, sys, threading, unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"osint-runtime"))
import safe_http

class SafeHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import brotli
        cls.body=b"<html>same useful site result</html>"
        cls.br=brotli.compress(cls.body)
        cls.requests=[]
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                cls.requests.append(self.path)
                if self.path=="/redirect":
                    self.send_response(302);self.send_header("Location","/br");self.send_header("Content-Length","0");self.end_headers();return
                payload=cls.br if self.path=="/br" else gzip.compress(cls.body) if self.path=="/gzip" else cls.body
                self.send_response(200)
                if self.path in ("/br","/gzip"):self.send_header("Content-Encoding",self.path[1:])
                self.send_header("Content-Length",str(len(payload)));self.end_headers();self.wfile.write(payload)
            def do_HEAD(self):
                self.send_response(200);self.send_header("Content-Encoding","br");self.send_header("Content-Length","123");self.end_headers()
            def log_message(self,*args):pass
        cls.server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.url="http://127.0.0.1:"+str(cls.server.server_port)
    @classmethod
    def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.thread.join()

    def test_valid_brotli_reaches_checked_python_decoder_as_compressed_bytes(self):
        from curl_cffi import CurlOpt
        observed=[];original=safe_http.decode_body
        def capture(data,encoding):observed.append((data,encoding));return original(data,encoding)
        async def exercise():
            async with safe_http.safe_session_class()(curl_options={CurlOpt.HTTP_CONTENT_DECODING:1}) as session:
                session.curl_options[CurlOpt.HTTP_CONTENT_DECODING]=1
                with patch.object(safe_http,"decode_body",side_effect=capture):
                    response=await session.get(self.url+"/br",accept_encoding="identity")
                self.assertEqual(response.content,self.body)
                self.assertEqual(session.curl_options[CurlOpt.HTTP_CONTENT_DECODING],0)
        asyncio.run(exercise())
        self.assertEqual(observed,[(self.br,"br")])

    def test_identity_gzip_redirect_and_head_keep_working(self):
        async def exercise():
            async with safe_http.safe_session_class()() as session:
                for path in ("/identity","/gzip","/redirect"):
                    response=await session.get(self.url+path)
                    self.assertEqual(response.content,self.body,path)
                self.assertEqual((await session.head(self.url+"/br")).content,b"")
        asyncio.run(exercise())

    def test_unsafe_python_decoder_stops_before_network(self):
        cls=safe_http.safe_session_class();before=len(self.requests)
        async def exercise():
            async with cls() as session:
                with patch.object(safe_http.importlib.metadata,"version",return_value="1.2.0"):
                    with self.assertRaises(safe_http.UnsafeDecoder):await session.get(self.url+"/br")
        asyncio.run(exercise());self.assertEqual(len(self.requests),before)

    def test_unsafe_optional_aiohttp_decoder_is_refused(self):
        with patch.object(safe_http.importlib.util,"find_spec",return_value=object()), patch.object(safe_http.importlib.metadata,"version",side_effect=lambda name:"1.2.1" if name=="Brotli" else "1.2.0.0"):
            with self.assertRaises(safe_http.UnsafeDecoder):safe_http.patched_brotli()

    def test_streaming_cannot_bypass_response_guard(self):
        before=len(self.requests)
        async def exercise():
            async with safe_http.safe_session_class()() as session:
                with self.assertRaises(safe_http.UnsafeDecoder):await session.get(self.url+"/br",stream=True)
        asyncio.run(exercise());self.assertEqual(len(self.requests),before)

    def test_decoded_size_limit_and_invalid_encoding(self):
        import brotli
        with patch.object(safe_http,"MAX_BODY",128):
            for encoding,data in (("br",brotli.compress(b"x"*1024)),("gzip",gzip.compress(b"x"*1024))):
                with self.assertRaises(safe_http.UnsafeDecoder):safe_http.decode_body(data,encoding)
        with self.assertRaises(safe_http.UnsafeDecoder):safe_http.decode_body(b"plain","unknown")

if __name__=="__main__":unittest.main()
