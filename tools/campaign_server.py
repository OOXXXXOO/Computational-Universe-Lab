"""campaign_server — stdlib-only control+observability server for the runner.

Decoupled from the runner (separate process, robust): the runner writes files in
data/runtime/run/, this server just reads them and lets the dashboard write control commands.
No third-party deps.

  python tools/campaign_server.py [--port 8765]
  then open  http://localhost:8765/

Routes:
  GET  /                -> visualizations/dashboards/dashboard.html
  GET  /api/state       -> data/runtime/run/state.json
  GET  /api/best        -> data/runtime/run/best_rule.json
  POST /api/control     {"command":"run"|"pause"|"stop"}
  GET  /<file>          -> static files below the project root
"""
import os, json, time, tempfile, argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, unquote

PROJECT_ROOT = os.path.realpath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RUN = os.path.join(PROJECT_ROOT, "data", "runtime", "run")


def atomic_write(path, obj):
    os.makedirs(RUN, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=RUN, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(obj, f)
        os.replace(tmp, path)                 # atomic on POSIX; runner reads never see partials
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):        # quiet
        pass

    def _send(self, code, body, ctype="application/json"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body)
        data = body.encode() if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass                              # client went away mid-response; not our problem

    def _file(self, path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            return None

    def do_GET(self):
        p = unquote(urlsplit(self.path).path)
        if p == "/api/state":
            return self._send(200, self._file(os.path.join(RUN, "state.json")) or {"status": "idle"})
        if p == "/api/best":
            return self._send(200, self._file(os.path.join(RUN, "best_rule.json")) or {})
        rel = "visualizations/dashboards/dashboard.html" if p == "/" else p.lstrip("/")
        # containment: no dotfiles (.env!) and resolved path must live inside project root.
        if any(part.startswith(".") for part in rel.split("/")):
            return self._send(404, {"error": "not found", "path": rel})
        full = os.path.realpath(os.path.join(PROJECT_ROOT, rel))
        if not full.startswith(PROJECT_ROOT + os.sep) or not os.path.isfile(full):
            return self._send(404, {"error": "not found", "path": rel})
        ctype = {"html": "text/html", "js": "text/javascript", "css": "text/css",
                 "json": "application/json"}.get(rel.rsplit(".", 1)[-1], "application/octet-stream")
        with open(full, "rb") as f:
            return self._send(200, f.read(), ctype + "; charset=utf-8")

    def do_OPTIONS(self):
        self._send(200, {})

    def do_POST(self):
        if self.path.split("?")[0] != "/api/control":
            return self._send(404, {"error": "not found"})
        n = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return self._send(400, {"error": "bad json"})
        cmd = body.get("command")
        if cmd not in ("run", "pause", "stop"):
            return self._send(400, {"error": "command must be run|pause|stop"})
        atomic_write(os.path.join(RUN, "control.json"), {"command": cmd, "t": time.time()})
        return self._send(200, {"ok": True, "command": cmd})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    a = ap.parse_args()
    os.makedirs(RUN, exist_ok=True)
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), H)
    print(f"[server] http://localhost:{a.port}/   (serving project root, control -> data/runtime/run/control.json)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n[server] bye")


if __name__ == "__main__":
    main()
