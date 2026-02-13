"""
Dummy HTTP servers to occupy project ports for testing run.sh port-kill logic.

Usage:
    python scripts/dummy_ports.py          # Start all dummy servers
    python scripts/dummy_ports.py 8000 7801  # Start on specific ports only

Press Ctrl+C to stop all.
"""

import sys
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler


class SilentHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"dummy")

    def log_message(self, format, *args):
        pass  # suppress request logs


DEFAULT_PORTS = {
    8000: "FastAPI Backend",
    5173: "Frontend Dev",
    7801: "MCP Server",
}


def start_server(port: int, label: str):
    try:
        server = HTTPServer(("0.0.0.0", port), SilentHandler)
        print(f"  [OK]  :{port}  ({label})")
        server.serve_forever()
    except OSError as e:
        print(f"  [FAIL] :{port}  ({label}) - {e}")


def main():
    if len(sys.argv) > 1:
        ports = {int(p): f"port {p}" for p in sys.argv[1:]}
    else:
        ports = DEFAULT_PORTS

    print("Starting dummy servers...\n")

    threads = []
    for port, label in ports.items():
        t = threading.Thread(target=start_server, args=(port, label), daemon=True)
        t.start()
        threads.append(t)

    print("\nAll dummy servers running. Press Ctrl+C to stop.\n")

    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
