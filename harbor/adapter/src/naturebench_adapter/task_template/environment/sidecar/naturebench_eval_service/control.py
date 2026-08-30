from __future__ import annotations

import argparse
import json
import socket
from pathlib import Path
from typing import Any

DEFAULT_SOCKET = Path("/run/naturebench/control.sock")


def control_request(request: dict[str, Any], socket_path: Path = DEFAULT_SOCKET) -> dict[str, Any]:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.connect(str(socket_path))
        client.sendall((json.dumps(request) + "\n").encode())
        stream = client.makefile("rb")
        response = json.loads(stream.readline())
    if not response.get("ok"):
        raise RuntimeError(response.get("error", "control request failed"))
    return response["result"]


def main() -> None:
    parser = argparse.ArgumentParser(prog="timerctl")
    parser.add_argument("--socket", type=Path, default=DEFAULT_SOCKET)
    subparsers = parser.add_subparsers(dest="command", required=True)
    start = subparsers.add_parser("start")
    start.add_argument("--timeout-seconds", type=float, required=True)
    subparsers.add_parser("wait-expired")
    subparsers.add_parser("stop")
    args = parser.parse_args()
    if args.command == "start":
        request = {"action": "start", "timeout_seconds": args.timeout_seconds}
    elif args.command == "wait-expired":
        request = {"action": "wait_expired"}
    else:
        request = {"action": "stop"}
    print(json.dumps(control_request(request, args.socket)))


if __name__ == "__main__":
    main()
