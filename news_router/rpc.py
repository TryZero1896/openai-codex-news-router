"""Minimal JSON-RPC-over-stdio client for `codex app-server`."""
from __future__ import annotations
import json
import queue
import subprocess
import threading
import time

class RpcError(RuntimeError):
    pass

class AppServer:
    def __init__(self, executable: str = "codex"):
        self.executable = executable
        self.proc = None
        self.responses = queue.Queue()
        self.next_id = 0

    def __enter__(self):
        self.proc = subprocess.Popen([self.executable, "app-server"], stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                     text=True, encoding="utf-8", bufsize=1)
        threading.Thread(target=self._reader, daemon=True).start()
        self.call("initialize", {"clientInfo": {"name": "openai_news_router", "title": "OpenAI News Router", "version": "0.1.0"}})
        self.notify("initialized", {})
        return self

    def _reader(self):
        try:
            for line in self.proc.stdout:
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if "id" in obj and ("result" in obj or "error" in obj):
                    self.responses.put(obj)
        finally:
            self.responses.put({"_eof": True})

    def _send(self, obj: dict):
        if not self.proc or self.proc.poll() is not None:
            raise RpcError("Codex App Server läuft nicht")
        self.proc.stdin.write(json.dumps(obj, ensure_ascii=False) + "\n")
        self.proc.stdin.flush()

    def notify(self, method: str, params: dict):
        self._send({"method": method, "params": params})

    def call(self, method: str, params: dict, timeout: float = 25) -> dict:
        self.next_id += 1
        id_ = self.next_id
        self._send({"id": id_, "method": method, "params": params})
        deadline = time.monotonic() + timeout
        while True:
            try:
                response = self.responses.get(timeout=max(0.01, deadline - time.monotonic()))
            except queue.Empty as exc:
                raise RpcError(f"Timeout bei {method}") from exc
            if response.get("_eof"):
                raise RpcError("Codex App Server unerwartet beendet")
            if response.get("id") != id_:
                raise RpcError("Unerwartete RPC-Antwort-ID")
            if "error" in response:
                raise RpcError(f"{method}: {response['error']}")
            return response["result"]

    def __exit__(self, *_):
        if self.proc:
            try:
                self.proc.stdin.close()
                self.proc.terminate()
                self.proc.wait(timeout=4)
            except Exception:
                self.proc.kill()
