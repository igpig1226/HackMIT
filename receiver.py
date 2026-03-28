#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import threading
import json
import urllib.request
import subprocess
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = "0.0.0.0"
PORT = 8000

ESP32_CAPTURE_URL = "http://192.168.0.202/capture"
POLL_INTERVAL = 10
HTTP_TIMEOUT = 8
MAX_IMAGE_SIZE = 5 * 1024 * 1024

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_CAT_PATH = os.path.join(BASE_DIR, "test_cat.jpg")
RUN_TFLITE = os.path.join(BASE_DIR, "run_tflite.py")

latest_pred_class = None   # 0=is cat, 1=not cat
latest_update_time = None
latest_status = "not_started"
latest_error = None

state_lock = threading.Lock()


def log(*args):
    print(time.strftime("[%Y-%m-%d %H:%M:%S]"), *args)


def fetch_image_once() -> bytes:
    req = urllib.request.Request(
        ESP32_CAPTURE_URL,
        headers={"User-Agent": "UnoQ-Cat-Receiver/1.0"}
    )

    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
        content_type = resp.headers.get("Content-Type", "")
        if "image/jpeg" not in content_type and "image/jpg" not in content_type:
            log("警告: /capture 返回的 Content-Type =", content_type)

        data = resp.read(MAX_IMAGE_SIZE + 1)
        if len(data) > MAX_IMAGE_SIZE:
            raise ValueError("image too large")

        return data


def save_as_test_cat(image_bytes: bytes):
    with open(TEST_CAT_PATH, "wb") as f:
        f.write(image_bytes)


def run_cat_classifier() -> int | None:
    """
    直接运行 python3 run_tflite.py
    要求它最终 stdout 输出 0 或 1
    """
    try:
        result = subprocess.run(
            ["python3", RUN_TFLITE],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=BASE_DIR
        )
    except Exception as e:
        log("run_tflite.py 调用失败:", e)
        return None

    stdout = (result.stdout or "").strip()
    stderr = (result.stderr or "").strip()

    if stderr:
        log("run_tflite stderr:", stderr)

    if result.returncode != 0:
        log("run_tflite 返回码异常:", result.returncode, "stdout=", stdout)
        return None

    lines = [x.strip() for x in stdout.splitlines() if x.strip()]
    if not lines:
        log("run_tflite 没有输出 pred_class")
        return None

    last = lines[-1]
    if last not in ("0", "1"):
        log("run_tflite 输出非法:", last)
        return None

    return int(last)


def poll_esp32_forever():
    global latest_pred_class, latest_update_time, latest_status, latest_error

    while True:
        try:
            image_bytes = fetch_image_once()
            save_as_test_cat(image_bytes)   # 覆盖写入 test_cat.jpg

            pred = run_cat_classifier()

            with state_lock:
                if pred is None:
                    latest_status = "classifier_failed"
                    latest_error = "run_tflite failed"
                else:
                    latest_pred_class = pred
                    latest_update_time = int(time.time())
                    latest_status = "ok"
                    latest_error = None

            if pred is None:
                log("本轮失败: 分类失败")
            else:
                log(f"本轮成功: pred_class={pred}")

        except Exception as e:
            with state_lock:
                latest_status = "fetch_failed"
                latest_error = str(e)
            log("抓取或保存图片失败:", e)

        time.sleep(POLL_INTERVAL)


class Handler(BaseHTTPRequestHandler):
    server_version = "UnoQPullReceiver/2.0"

    def send_json(self, code: int, obj: dict):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        global latest_pred_class, latest_update_time, latest_status, latest_error

        if self.path in ("/", "/health"):
            with state_lock:
                self.send_json(200, {
                    "status": "ok",
                    "service": "unoq cat receiver",
                    "time": int(time.time()),
                    "poll_interval": POLL_INTERVAL,
                    "capture_url": ESP32_CAPTURE_URL,
                    "latest_status": latest_status,
                    "has_result": latest_pred_class is not None
                })
            return

        if self.path == "/result":
            with state_lock:
                if latest_pred_class is None:
                    self.send_json(404, {
                        "error": "no result yet",
                        "latest_status": latest_status,
                        "latest_error": latest_error
                    })
                    return

                self.send_json(200, {
                    "status": "ok",
                    "pred_class": latest_pred_class,
                    "updated_at": latest_update_time,
                    "latest_status": latest_status
                })
            return

        self.send_json(404, {"error": "not found"})

    def log_message(self, fmt, *args):
        log(f"{self.client_address[0]} - {fmt % args}")


def main():
    if not os.path.exists(RUN_TFLITE):
        raise FileNotFoundError(f"未找到 {RUN_TFLITE}")

    t = threading.Thread(target=poll_esp32_forever, daemon=True)
    t.start()

    server = ThreadingHTTPServer((HOST, PORT), Handler)
    log(f"Listening on http://{HOST}:{PORT}")
    log(f"Polling {ESP32_CAPTURE_URL} every {POLL_INTERVAL}s")
    log(f"Saving latest image to {TEST_CAT_PATH}")
    server.serve_forever()


if __name__ == "__main__":
    main()