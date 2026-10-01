#!/bin/bash

echo "Starting Xena MCP server..."

python mcp_server/server.py &
MCP_PID=$!

echo "Waiting for MCP server..."

python - <<'PY'
import socket
import sys
import time

for _ in range(60):
    try:
        with socket.create_connection(("127.0.0.1", 8000), timeout=1):
            print("MCP server is ready.")
            break
    except OSError:
        time.sleep(1)
else:
    print("MCP server failed to start.", file=sys.stderr)
    sys.exit(1)
PY

echo "Starting Xena web application..."

trap 'kill $MCP_PID 2>/dev/null || true' EXIT

exec gunicorn app:app \
    --bind 0.0.0.0:${PORT} \
    --workers 1 \
    --threads 2 \
    --timeout 120