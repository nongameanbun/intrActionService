# find_in_screen_yolo(model: liecheck_251129)
# {0: 'click', 1: 'type', 2: 'dongnama'} 검출되는 모델임

import time

from gateway import *
import random  # gateway가 `from random import random`을 쓰므로 반드시 이후에 import (viol.py와 동일 패턴)
from interruption.dongnama import handle_dongnama

LIECHECK_MODEL = "liecheck_251129"


def handle_type():
    return "wait"


def handle_liecheck():
    def handle_object_click(stack=0):
        if stack > 3:
            return False

        detections = find_in_screen_yolo(LIECHECK_MODEL)
        if not detections:
            return handle_object_click(stack + 1)

        det = detections[0]
        if det["cls"] == "type" or det["cls"] == "dongnama":
            return det["cls"]
        else:
            return det["xywh"]

    timestamp = time.time()
    while time.time() - timestamp < 60:
        ret = handle_object_click()

        if ret is False:
            return "continue"
        elif ret == "type":
            return handle_type()
        elif ret == "dongnama":
            return handle_dongnama()
        else:
            x, y, w, h = ret
            rx, ry = x + random.randint(0, w), y + random.randint(0, h)
            mouse_click("left", 100, rx, ry)
            Rdelay_2(500)

    return "wait"
