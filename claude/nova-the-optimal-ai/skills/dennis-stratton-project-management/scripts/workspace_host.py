"""Portable, loopback-only workspace launcher. Vendored; no remote runtime."""
from __future__ import annotations
import argparse, hashlib, json, os, secrets, socket, subprocess, sys, threading, time, urllib.request, webbrowser
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.' + secrets.token_hex(6) + '.tmp')
    try:
        with temporary.open('x', encoding='utf-8', newline='\n') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)

@contextmanager
def write_lock(home):
    lock = Path(home) / '.workspace-write-lock'
    try:
        lock.mkdir()
    except FileExistsError:
        raise ValueError('Another write is in progress. Retry; if a crashed process left the lock, close the workspace before removing .workspace-write-lock.')
    try:
        yield
    finally:
        lock.rmdir()

def digest(root):
    h = hashlib.sha256()
    for folder in ('scripts', 'workspace'):
        for path in sorted((root / folder).rglob('*')):
            if path.is_file() and '__pycache__' not in path.parts:
                h.update(path.relative_to(root).as_posix().encode()); h.update(path.read_bytes())
    return h.hexdigest()[:20]

def health(port):
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/health', timeout=.8) as response:
            return json.load(response)
    except Exception:
        return None

def validate_data_home(home, root):
    home, root = Path(home).resolve(), Path(root).resolve()
    boundaries = [root]
    for parent in root.parents:
        if parent == parent.parent:
            break
        repository = (parent / '.git').exists()
        release = any((parent / name).is_file() for name in ('RELEASE-MANIFEST.json', 'release-manifest.json'))
        if repository or release or (parent / '.codex-plugin' / 'plugin.json').is_file():
            boundaries.append(parent)
        if repository or release:
            break
    if any(home == boundary or boundary in home.parents for boundary in boundaries):
        raise ValueError('Choose a persistent data folder outside this source or installation. No folder was created.')
    return home

def create_native_shortcut(product, root, home, launcher, desktop=None):
    """Bind the existing launcher and explicit project-record home to a native product icon."""
    root, home, launcher = Path(root), Path(home), Path(launcher)
    desktop = Path(desktop) if desktop is not None else Path(os.environ.get('USERPROFILE', str(Path.home()))) / 'Desktop'
    if not desktop.is_dir():
        raise ValueError(f'Desktop folder is unavailable: {desktop}')
    if os.name == 'nt':
        target = desktop / (product + '.lnk')
        if target.exists():
            raise ValueError(f'Shortcut already exists; not overwritten: {target}')
        icon = root / 'workspace' / 'assets' / 'dennis.ico'
        if not icon.is_file():
            raise ValueError('Product icon is unavailable.')
        executable = Path(sys.executable)
        windowless = executable.with_name('pythonw.exe')
        if executable.name.lower() == 'python.exe' and windowless.is_file():
            executable = windowless
        environment = dict(os.environ, DENNIS_NATIVE_LINK=str(target), DENNIS_NATIVE_TARGET=str(executable),
            DENNIS_NATIVE_ARGS=subprocess.list2cmdline([str(launcher), '--home', str(home)]),
            DENNIS_NATIVE_WORKDIR=str(root), DENNIS_NATIVE_ICON=str(icon))
        powershell = Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32' / 'WindowsPowerShell' / 'v1.0' / 'powershell.exe'
        command = "$ErrorActionPreference='Stop';$s=(New-Object -ComObject WScript.Shell).CreateShortcut($env:DENNIS_NATIVE_LINK);$s.TargetPath=$env:DENNIS_NATIVE_TARGET;$s.Arguments=$env:DENNIS_NATIVE_ARGS;$s.WorkingDirectory=$env:DENNIS_NATIVE_WORKDIR;$s.IconLocation=$env:DENNIS_NATIVE_ICON+',0';$s.Description='Open the Dennis project bridge';$s.Save()"
        subprocess.run([str(powershell), '-NoLogo', '-NoProfile', '-NonInteractive', '-Command', command],
            env=environment, check=True, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
        return target
    import shlex
    if sys.platform == 'darwin':
        import plistlib, shutil
        target = desktop / (product + '.app')
        if target.exists():
            raise ValueError(f'Shortcut already exists; not overwritten: {target}')
        temporary = desktop / ('.dennis-native-' + secrets.token_hex(6) + '.app')
        try:
            shutil.copytree(root / 'Dennis Project Bridge.app', temporary)
            script = temporary / 'Contents' / 'MacOS' / 'launch.command'
            script.write_text('#!/bin/sh\nexec ' + shlex.join([sys.executable, str(launcher), '--home', str(home)]) + '\n', encoding='utf-8', newline='\n')
            script.chmod(0o755)
            temporary.rename(target)
        finally:
            if temporary.exists():
                shutil.rmtree(temporary)
        return target
    target = desktop / (product + '.command')
    if target.exists():
        raise ValueError(f'Shortcut already exists; not overwritten: {target}')
    target.write_text('#!/bin/sh\nexec ' + shlex.join([sys.executable, str(launcher), '--home', str(home)]) + '\n', encoding='utf-8', newline='\n')
    target.chmod(0o755)
    return target

def run_workspace(product, version, root, resolve_home, read_state, mutate, preferred_port):
    parser = argparse.ArgumentParser(description=f'Open {product}; data remains outside the installation.')
    parser.add_argument('--home', '--store', dest='home')
    parser.add_argument('--serve', action='store_true')
    parser.add_argument('--port', type=int, default=preferred_port)
    parser.add_argument('--no-browser', action='store_true')
    parser.add_argument('--offer-shortcut', action='store_true')
    args = parser.parse_args()
    home = validate_data_home(resolve_home(args.home), root)
    home.mkdir(parents=True, exist_ok=True)
    runtime = home / '.workspace'; runtime.mkdir(exist_ok=True)
    identity = {'product': product, 'version': version, 'home': str(home), 'build': digest(root)}
    cache = runtime / 'service.json'
    if not args.serve:
        if args.offer_shortcut:
            answer = input('Create a desktop launch shortcut for this workspace? [y/N] ').strip().lower()
            if answer in ('y', 'yes'):
                try:
                    target = create_native_shortcut(product, root, home, Path(sys.argv[0]).resolve())
                    print(f'Created {target}')
                except Exception as exc:
                    print(f'Desktop icon was not created: {exc}. The workspace will still open.', file=sys.stderr)
        ports = []
        if cache.exists():
            try: ports.append(json.loads(cache.read_text(encoding='utf-8'))['port'])
            except (ValueError, KeyError): pass
        ports.extend(range(args.port, args.port + 40))
        for port in dict.fromkeys(ports):
            seen = health(port)
            if seen and all(seen.get(k) == v for k, v in identity.items()):
                url = f'http://127.0.0.1:{port}/'
                if not args.no_browser: webbrowser.open(url)
                print(url); return
        port = None
        for candidate in range(args.port, args.port + 40):
            with socket.socket() as probe:
                try: probe.bind(('127.0.0.1', candidate)); port = candidate; break
                except OSError: continue
        if port is None: raise ValueError('No free local workspace port. Close unused local services and retry.')
        command = [sys.executable, str(Path(sys.argv[0]).resolve()), '--serve', '--home', str(home), '--port', str(port)]
        with (runtime / 'service.log').open('ab') as log:
            flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            subprocess.Popen(command, stdout=log, stderr=log, stdin=subprocess.DEVNULL, creationflags=flags, start_new_session=os.name != 'nt')
        for _ in range(100):
            seen = health(port)
            if seen and all(seen.get(k) == v for k, v in identity.items()): break
            time.sleep(.1)
        else: raise ValueError(f'Workspace did not start. Read {runtime / "service.log"}')
        atomic_json(cache, {'port': port, **identity})
        url = f'http://127.0.0.1:{port}/'
        if not args.no_browser: webbrowser.open(url)
        print(url); return

    token = secrets.token_urlsafe(32)
    guard = threading.Lock()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args): pass
        def allowed(self):
            return self.headers.get('Host') == f'127.0.0.1:{args.port}'
        def send(self, value, status=200, content_type='application/json'):
            payload = json.dumps(value, ensure_ascii=False).encode() if content_type == 'application/json' else value
            self.send_response(status)
            self.send_header('Content-Type', content_type + '; charset=utf-8')
            self.send_header('Content-Length', str(len(payload)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers(); self.wfile.write(payload)
        def do_GET(self):
            if not self.allowed() or self.headers.get('Origin', f'http://127.0.0.1:{args.port}') != f'http://127.0.0.1:{args.port}': return self.send({'error': 'Unexpected host or origin'}, 403)
            try:
                path = self.path.split('?')[0]
                if path == '/health': return self.send(identity)
                if path == '/api/state': return self.send({'token': token, **read_state(home)})
                files = {'/': ('index.html', 'text/html'), '/app.js': ('app.js', 'text/javascript'), '/route.js': ('route.js', 'text/javascript'), '/skin.css': ('skin.css', 'text/css'), '/route.css': ('route.css', 'text/css'), '/proofspan.css': ('proofspan.css', 'text/css')}
                files.update({'/assets/dennis.png': ('assets/dennis.png', 'image/png'), '/favicon.ico': ('assets/dennis.ico', 'image/x-icon')})
                if path not in files: return self.send({'error': 'Not found'}, 404)
                name, mime = files[path]; self.send((root / 'workspace' / name).read_bytes(), content_type=mime)
            except Exception as exc: self.send({'error': str(exc)}, 500)
        def do_POST(self):
            if not self.allowed() or self.headers.get('Origin') != f'http://127.0.0.1:{args.port}' or self.headers.get('X-Workspace-Token') != token:
                return self.send({'error': 'Open the workspace itself before saving.'}, 403)
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 2_000_000: return self.send({'error': 'Request too large or empty'}, 413)
                value = json.loads(self.rfile.read(size))
                if self.path == '/api/stop':
                    self.send({'stopping': True}); threading.Thread(target=self.server.shutdown, daemon=True).start(); return
                if self.path != '/api/write': return self.send({'error': 'Not found'}, 404)
                with guard, write_lock(home): result = mutate(home, value)
                self.send(result)
            except (ValueError, FileExistsError, KeyError, TypeError) as exc: self.send({'error': str(exc)}, 409)
            except Exception as exc: self.send({'error': str(exc)}, 500)
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    atomic_json(cache, {'port': args.port, **identity})
    server.serve_forever()
