import os
import time
import threading
from datetime import datetime
from gateway import *
import random

import mss        # type: ignore
import cv2        # type: ignore
import numpy as np  # type: ignore

ROUND_COUNT   = 4
DISABLED_IMGS = ["1_disabled", "2_disabled", "3_disabled", "4_disabled"]
ENABLED_IMGS  = ["1_enabled",  "2_enabled",  "3_enabled",  "4_enabled"]
VIOL_REGION   = "450, 325, 930, 565"  # x1,y1,x2,y2  (xywh 450,325,480,240 변환)

DEBUG_VIOL     = False
DEBUG_INTERVAL = 0.5   # 캡처 주기 (초)
_DEBUG_DIR     = os.path.join(os.path.dirname(__file__), "..", "..", "debug_tmp")
_VIOL_RNG      = list(map(int, VIOL_REGION.split(",")))  # [450, 325, 930, 565]

_BTN_BASE_X = 76
_BTN_BASE_Y = 215
_BTN_GAP_X  = 104


def _click_viol_button(position: int) -> None:
    x = _VIOL_RNG[0] + _BTN_BASE_X + _BTN_GAP_X * (position - 1) + random.randint(-4, 4)
    y = _VIOL_RNG[1] + _BTN_BASE_Y + random.randint(-3, 3)
    mouse_click("left", 50, x, y)
    print(f"[viol] click position={position} → ({x}, {y})")

_COLOR = {
    "enabled":  (0, 255, 0),
    "disabled": (180, 180, 180),
    "notice":   (0, 0, 255),
}

_debug_stop = threading.Event()


def _debug_save_frame():
    """화면(VIOL_REGION) 캡처 + disabled/enabled/notice_viol 감지 박스 그려서 저장."""
    try:
        os.makedirs(_DEBUG_DIR, exist_ok=True)
        sx, sy, ex, ey = _VIOL_RNG
        with mss.mss() as sct:
            frame = cv2.cvtColor(
                np.array(sct.grab({"top": sy, "left": sx, "width": ex - sx, "height": ey - sy})),
                cv2.COLOR_BGRA2BGR,
            )

        all_keys = ", ".join(DISABLED_IMGS + ENABLED_IMGS + ["notice_viol"])
        result = find_in_screen_multiple(all_keys, xywh=VIOL_REGION) or {}

        for name, detections in result.items():
            if not detections:
                continue
            color = _COLOR["enabled"] if "enabled" in name else \
                    _COLOR["notice"]  if "notice"  in name else \
                    _COLOR["disabled"]
            for det in detections:
                x, y, w, h = det["xywh"]
                cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                cv2.putText(frame, name, (x, max(0, y - 4)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

        ts = datetime.now().strftime("%H%M%S_%f")[:10]
        cv2.imwrite(os.path.join(_DEBUG_DIR, f"viol_{ts}.png"), frame)
    except Exception as e:
        print(f"[debug] frame save failed: {e}")


def _debug_loop():
    while not _debug_stop.is_set():
        _debug_save_frame()
        _debug_stop.wait(DEBUG_INTERVAL)


# ── 폴링 헬퍼 ──────────────────────────────────────────────────────────────

def _wait_notice_viol_gone(timeout: float = 60.0) -> bool:
    """notice_viol 이미지가 화면에서 사라질 때까지 대기. timeout 초과 시 False."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not find_in_screen("notice_viol"):
            return True
        time.sleep(0.2)
    return False


def _wait_notice_viol_present(timeout: float = 60.0) -> bool:
    """notice_viol 이미지가 화면에 나타날 때까지 대기. timeout 초과 시 False."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if find_in_screen("notice_viol"):
            return True
        time.sleep(0.2)
    return False


def _wait_all_disabled(timeout: float = 15.0) -> bool:
    """[1_disabled ~ 4_disabled] 4개가 모두 화면에 보일 때까지 대기."""
    keys_str = ", ".join(DISABLED_IMGS)
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = find_in_screen_multiple(keys_str, xywh=VIOL_REGION) or {}
        if all(result.get(k) for k in DISABLED_IMGS):
            return True
        time.sleep(0.1)
    return False


def _wait_any_enabled(timeout: float = 10.0) -> bool:
    """[1_enabled ~ 4_enabled] 중 하나라도 화면에 보일 때까지 대기."""
    keys_str = ", ".join(ENABLED_IMGS)
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = find_in_screen_multiple(keys_str, xywh=VIOL_REGION) or {}
        if any(result.get(k) for k in ENABLED_IMGS):
            return True
        time.sleep(0.05)
    return False


# ── 메인 핸들러 ────────────────────────────────────────────────────────────

def handle_viol():
    if DEBUG_VIOL:
        _debug_stop.clear()
        threading.Thread(target=_debug_loop, daemon=True).start()

    try:
        # [1] ready
        viol_ready()

        # [2~3] notice_viol 소멸 대기 + true positive 확인 루프
        while True:
            # [2] notice_viol이 사라질 때까지 대기
            if not _wait_notice_viol_gone(timeout=60):
                print("[viol] notice_viol 소멸 timeout → exception")
                viol_exception()
                return "wait"

            # [3+4] appear 시도 — violSolver 내부에서 noonal YOLO로 true positive 확인
            resp = viol_appear()
            if isinstance(resp, dict) and resp.get("initial_id") is not None:
                print(f"[viol] appear 성공: initial_id={resp['initial_id']}")
                break

            # false positive → notice_viol 재등장 대기 후 2단계 재시도
            print("[viol] noonal 미감지 (false positive) → notice_viol 재감지 대기")
            if not _wait_notice_viol_present(timeout=60):
                print("[viol] notice_viol 재등장 timeout → exception")
                viol_exception()
                return "wait"

        # [5] 셔플 라운드 루프 (4회)
        for round_num in range(1, ROUND_COUNT + 1):

            # [5a] disabled 버튼 4개 모두 감지 대기
            if not _wait_all_disabled(timeout=40):
                print(f"[viol] round {round_num}: disabled 버튼 timeout → exception")
                viol_exception()
                return "wait"

            # [5b] shuffle_start
            viol_shuffle_start()
            print(f"[viol] round {round_num}: shuffle_start")

            # [5c] enabled 버튼 감지 대기
            if not _wait_any_enabled(timeout=40):
                print(f"[viol] round {round_num}: enabled 버튼 timeout → exception (교도소 추정)")
                viol_exception()
                return "wait"

            # [5d] shuffle_stop → 결과 출력
            result = viol_shuffle_stop()
            print(f"[viol] round {round_num}: {result}")

            # [5e] true_viol 위치 버튼 클릭
            true_viol = result.get("true_viol") if isinstance(result, dict) else None
            if not true_viol:
                print(f"[viol] round {round_num}: true_viol 없음 → exception")
                viol_exception()
                return "wait"
            _click_viol_button(true_viol)

        # [6] game_end
        viol_game_end()
        print("[viol] 게임 정상 완료")
        time.sleep(5)
        press_key_with_delay("enter", 100)

    except Exception as e:
        print(f"[viol] 예외 발생: {e}")
        viol_exception()

    finally:
        _debug_stop.set()

    return "continue"
