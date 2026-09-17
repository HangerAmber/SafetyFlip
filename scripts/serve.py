"""Serve only the project website on loopback; never expose the repository root."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--port", type=int, default=8765)
args = parser.parse_args()
site = Path(__file__).resolve().parents[1] / "site"
handler = partial(SimpleHTTPRequestHandler, directory=str(site))
print(f"SafetyFlip website: http://127.0.0.1:{args.port} (Ctrl+C to stop)", flush=True)
with ThreadingHTTPServer(("127.0.0.1", args.port), handler) as server:
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
