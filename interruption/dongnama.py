import base64
import re
import time

import cv2
import mss
import numpy as np
from openai import OpenAI

from gateway import *
import random  # gateway가 `from random import random`을 쓰므로 반드시 이후에 import (viol.py와 동일 패턴)

LIECHECK_MODEL = "liecheck_251129"
OCR_MODEL = "gpt-4o"

# dongnama 다이얼로그 bbox 대비 5개 선택지 행의 y 상대위치 (dongnamademo.mp4 실측)
DONGNAMA_ROW_Y_FRAC = [0.355, 0.488, 0.619, 0.749, 0.880]
DONGNAMA_MAX_ATTEMPTS = 3
DONGNAMA_DEADLINE = 18  # 인게임 20초 타이머 대비 여유

_client = OpenAI()


def _grab_region(x: int, y: int, w: int, h: int) -> np.ndarray:
    with mss.mss() as sct:
        return np.array(sct.grab({"top": y, "left": x, "width": w, "height": h}))[:, :, :3]


def _extract_sentence(image: np.ndarray) -> str:
    """이미지 속 한글 문장을 GPT-4o Vision OCR로 추출"""
    pad = 25
    padded = cv2.copyMakeBorder(image, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=[255, 255, 255])
    upscale = cv2.resize(padded, None, fx=1.8, fy=1.8, interpolation=cv2.INTER_CUBIC)
    _, img_bytes = cv2.imencode(".png", upscale)
    img_b64 = base64.b64encode(img_bytes).decode("utf-8")

    resp = _client.chat.completions.create(
        model=OCR_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are now operating STRICTLY as an OCR engine.\n"
                    "- Extract ALL Korean text exactly as visible.\n"
                    "- Ignore UI shapes, boxes, colors.\n"
                    "- Do NOT correct typos; keep exact characters.\n"
                    "- Output only text lines as seen."
                ),
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "한글 문장들을 가능한 한 정확히 추출하세요."},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
                ],
            },
        ],
    )
    return resp.choices[0].message.content


def _parse_choices(text: str) -> list:
    """OCR 결과에서 '올바른 문장을 선택해 주세요' 다음에 오는 5개 선택지만 추린다."""
    lines = [s.strip() for s in text.split("\n") if s.strip()]

    idx = -1
    for i, s in enumerate(lines):
        if "올바른 문장을 선택해 주세요" in s:
            idx = i
            break

    return lines[idx + 1: idx + 6] if idx >= 0 else []


def _pick_best_choice(choices: list) -> int:
    """5개 문장 중 가장 자연스러운 문장의 번호(1~5)를 GPT로 고른다."""
    prompt = "다음 한국어 문장 5개 중 가장 자연스러운 문장을 고르세요.\n"
    prompt += "- 이유 설명 금지\n- 문장 출력 금지\n- 오직 숫자(1~5)만 출력\n\n"
    for i, sent in enumerate(choices, start=1):
        prompt += f"{i}. {sent}\n"

    resp = _client.chat.completions.create(
        model=OCR_MODEL,
        messages=[
            {"role": "system", "content": "You MUST output ONLY ONE DIGIT (1~5). No other text allowed."},
            {"role": "user", "content": prompt},
        ],
    )
    raw = resp.choices[0].message.content.strip()
    m = re.search(r"[1-5]", raw)
    if not m:
        raise ValueError(f"GPT가 숫자를 반환하지 않음: {raw}")
    return int(m.group(0))


def handle_dongnama():
    deadline = time.time() + DONGNAMA_DEADLINE

    for attempt in range(DONGNAMA_MAX_ATTEMPTS):
        if time.time() > deadline:
            print("[dongnama] 시간 초과")
            break

        detections = [d for d in find_in_screen_yolo(LIECHECK_MODEL) if d["cls"] == "dongnama"]
        if not detections:
            print("[dongnama] bbox 감지 실패")
            break

        x, y, w, h = detections[0]["xywh"]
        crop = _grab_region(x, y, w, h)

        try:
            text = _extract_sentence(crop)
            choices = _parse_choices(text)

            if len(choices) != 5:
                print(f"[dongnama] attempt {attempt + 1}: 선택지 파싱 실패 -> {choices}")
                # 커서가 텍스트 위에 있어 가려졌을 수 있으니 치우고 재시도
                mouse_move(x + random.randint(-5, 5), y - 30 + random.randint(-5, 5))
                Rdelay_2(500)
                continue

            answer_num = _pick_best_choice(choices)
            print(f"[dongnama] 선택: #{answer_num} {choices[answer_num - 1]}")

        except Exception as e:
            print(f"[dongnama] attempt {attempt + 1}: 실패 - {e}")
            continue

        click_x = int(x + w * 0.5 + random.randint(-4, 4))
        click_y = int(y + h * DONGNAMA_ROW_Y_FRAC[answer_num - 1] + random.randint(-3, 3))
        mouse_click("left", 100, click_x, click_y)
        Rdelay_2(500)

        return "continue"

    print("[dongnama] 자동 처리 실패 - 수동 개입 대기")
    return "wait"
