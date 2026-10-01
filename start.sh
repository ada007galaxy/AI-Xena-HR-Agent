#!/bin/bash

echo "Starting Xena MCP server..."

python mcp_server/server.py &

echo "Waiting for MCP server..."
sleep 5

echo "Starting Xena web application..."

exec gunicorn app:app --bind 0.0.0.0:${PORT} --workers 1 --threads 2 --timeout 120