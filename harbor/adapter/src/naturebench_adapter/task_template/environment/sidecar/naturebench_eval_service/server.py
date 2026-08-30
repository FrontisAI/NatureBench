from __future__ import annotations

import argparse
import json
import logging
import os
import socketserver
import threading
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .evaluation import SingleTrialEvaluator

logger = logging.getLogger("naturebench.eval_service")


class EvaluationRequestHandler(BaseHTTPRequestHandler):
    service: SingleTrialEvaluator

    def log_message(self, format: str, *args: Any) -> None:
        logger.info(format, *args)

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2, default=str).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/health":
            self._send_json(200, {"status": "ok"})
        elif path == "/best_score":
            self._send_json(200, self.service.best_score_payload())
        elif path == "/time_remaining":
            self._send_json(200, self.service.timer.snapshot())
        else:
            self._send_json(404, {"error": "unknown endpoint"})

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/evaluate":
            self._send_json(404, {"error": "unknown endpoint"})
            return
        length = int(self.headers.get("Content-Length", "0"))
        if length:
            try:
                body = json.loads(self.rfile.read(length))
            except json.JSONDecodeError as error:
                self._send_json(400, {"error": f"invalid JSON: {error}"})
                return
            if not isinstance(body, dict):
                self._send_json(400, {"error": "request body must be a JSON object"})
                return
        try:
            self._send_json(200, self.service.evaluate())
        except Exception as error:
            logger.error("evaluation failed:\n%s", traceback.format_exc())
            self._send_json(500, {"error": f"evaluation failed: {error}"})


class ControlRequestHandler(socketserver.StreamRequestHandler):
    service: SingleTrialEvaluator

    def handle(self) -> None:
        try:
            request = json.loads(self.rfile.readline())
            action = request.get("action")
            if action == "start":
                result = self.service.timer.start(float(request["timeout_seconds"]))
            elif action == "wait_expired":
                result = self.service.timer.wait_expired()
            elif action == "stop":
                result = self.service.timer.stop()
            else:
                raise ValueError(f"unknown control action: {action}")
            response = {"ok": True, "result": result}
        except Exception as error:
            response = {"ok": False, "error": str(error)}
        self.wfile.write((json.dumps(response) + "\n").encode())


class ThreadingUnixServer(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True


def run_servers(
    service: SingleTrialEvaluator,
    host: str,
    port: int,
    control_socket: Path,
) -> None:
    control_socket.parent.mkdir(parents=True, exist_ok=True)
    control_socket.unlink(missing_ok=True)
    http_handler = type("BoundEvaluationHandler", (EvaluationRequestHandler,), {"service": service})
    control_handler = type("BoundControlHandler", (ControlRequestHandler,), {"service": service})
    control_server = ThreadingUnixServer(str(control_socket), control_handler)
    os.chmod(control_socket, 0o600)
    control_thread = threading.Thread(target=control_server.serve_forever, daemon=True)
    control_thread.start()
    http_server = ThreadingHTTPServer((host, port), http_handler)
    logger.info("agent API listening on %s:%d", host, port)
    try:
        http_server.serve_forever()
    finally:
        http_server.server_close()
        control_server.shutdown()
        control_server.server_close()
        control_socket.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-name", default=os.environ.get("NATUREBENCH_TASK_ID"))
    parser.add_argument("--metadata", type=Path, default=Path("/metadata.json"))
    parser.add_argument("--evaluation-dir", type=Path, default=Path("/evaluation"))
    parser.add_argument("--output-dir", type=Path, default=Path("/workspace/output"))
    parser.add_argument("--state-dir", type=Path, default=Path("/state"))
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--control-socket", type=Path, default=Path("/run/naturebench/control.sock"))
    args = parser.parse_args()
    if not args.task_name:
        parser.error("--task-name or NATUREBENCH_TASK_ID is required")
    args.state_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [NatureBenchEval] %(levelname)s %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(args.state_dir / "eval_service.log"),
        ],
    )
    service = SingleTrialEvaluator(
        task_name=args.task_name,
        metadata_path=args.metadata,
        output_dir=args.output_dir,
        state_dir=args.state_dir,
        evaluation_dir=args.evaluation_dir,
    )
    run_servers(service, args.host, args.port, args.control_socket)


if __name__ == "__main__":
    main()
