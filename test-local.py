import json
from pathlib import Path
import subprocess
import sys


def main():
    here = Path(__file__).resolve().parent
    server = subprocess.Popen(
        [sys.executable, str(here / "sky-mcp-server.py")],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=str(here),
    )

    def call(message):
        assert server.stdin is not None
        assert server.stdout is not None
        server.stdin.write(json.dumps(message) + "\n")
        server.stdin.flush()
        line = server.stdout.readline()
        if not line:
            stderr = server.stderr.read() if server.stderr else ""
            raise RuntimeError("Server exited early:\n" + stderr)
        return json.loads(line)

    try:
        print(json.dumps(call({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}), indent=2))
        print(json.dumps(call({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}), indent=2))
        print(json.dumps(call({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "status", "arguments": {}},
        }), indent=2, ensure_ascii=False))
    finally:
        server.kill()


if __name__ == "__main__":
    main()
