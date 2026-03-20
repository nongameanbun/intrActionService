from random import random
import time
import dotenv
import os
import requests
import psutil

import os, dotenv

dotenv.load_dotenv()

inputHandler_API_URL = f"http://127.0.0.1:{int(os.getenv('inputHandler_API_PORT'))}"
statusChecker_API_URL = f"http://127.0.0.1:{int(os.getenv('statusChecker_API_PORT'))}"
alarmHandler_API_URL = f"http://127.0.0.1:{int(os.getenv('alarmHandler_API_PORT'))}"
intrAction_API_URL = f"http://127.0.0.1:{int(os.getenv('intrAction_API_PORT'))}"
mainAction_API_URL = f"http://127.0.0.1:{int(os.getenv('mainAction_API_PORT'))}"
subaction_API_URL = f"http://127.0.0.1:{int(os.getenv('subaction_API_PORT'))}"
streaning_API_URL = f"http://127.0.0.1:{int(os.getenv('streaning_API_PORT'))}"
objectDetector_API_URL = f"http://127.0.0.1:{int(os.getenv('objectDetector_API_PORT'))}"
runeSolver_API_URL = f"http://127.0.0.1:{int(os.getenv('runeSolver_API_PORT'))}"

# ─── helpers ───

def _safe_post(url, timeout=60):
    """POST 요청 후 JSON 반환. 실패 시 None."""
    try:
        r = requests.post(url, timeout=timeout)
        return r.json()
    except Exception as e:
        print(f"[gateway] POST {url} failed: {e}")
        return None

def _safe_get(url, timeout=5):
    """GET 요청 후 JSON 반환. 실패 시 None."""
    try:
        r = requests.get(url, timeout=timeout)
        return r.json()
    except Exception as e:
        print(f"[gateway] GET {url} failed: {e}")
        return None

def _resp_val(data, key="resp", default=None):
    """JSON dict에서 key 꺼내기. data가 None이거나 key 없으면 default."""
    if data is None:
        return default
    return data.get(key, default)

def __precise_wait(duration, start_time):
    wait_time = duration - (time.perf_counter() - start_time)
    if wait_time <= 0:
        return
    if wait_time > 0.015:
        time.sleep(wait_time - 0.015)
    while (time.perf_counter() - start_time) < duration:
        pass

def _post_and_wait(url):
    """POST → resp(ms) 파싱 → precise_wait. resp 파싱 실패 시 대기 생략."""
    start_t = time.perf_counter()
    data = _safe_post(url)
    resp = _resp_val(data, "resp", 0)
    try:
        __precise_wait(int(resp) / 1000, start_t)
    except (TypeError, ValueError):
        pass

# ─── inputHandler ───

def on():
    _safe_post(f"{inputHandler_API_URL}/on")

def off():
    _safe_post(f"{inputHandler_API_URL}/off")

def press_key(key_name):
    _post_and_wait(f"{inputHandler_API_URL}/press_key?key_name={key_name}")

def release_key(key_name):
    _post_and_wait(f"{inputHandler_API_URL}/release_key?key_name={key_name}")

def releaseAll():
    _post_and_wait(f"{inputHandler_API_URL}/releaseAll")

def press_key_with_delay(key_name, delay):
    _post_and_wait(f"{inputHandler_API_URL}/press_key_with_delay?key_name={key_name}&delay={delay}")

def press_two_key(key1, key2):
    _post_and_wait(f"{inputHandler_API_URL}/press_two_key?key1={key1}&key2={key2}")

def mouse_move(x, y):
    _post_and_wait(f"{inputHandler_API_URL}/mouse/move?x={x}&y={y}")

def mouse_click(click_mode, delay, x=None, y=None):
    url = f"{inputHandler_API_URL}/mouse/click?click_mode={click_mode}&delay={delay}"
    if x is not None and y is not None:
        url += f"&x={x}&y={y}"
    _post_and_wait(url)

def Rdelay(delay):
    _post_and_wait(f"{inputHandler_API_URL}/delay?delay={delay}")

def Rdelay_2(delay):
    Rdelay(delay)

# ─── statusChecker ───

def get_status(mode=None):
    data = _safe_get(f"{statusChecker_API_URL}/status/get")
    resp = _resp_val(data)
    if resp is None:
        return 0.0 if mode else {}
    if mode:
        return resp.get(mode, 0.0)
    return resp

def clear_status():
    _safe_post(f"{statusChecker_API_URL}/status/clear")

def check_rune():
    data = _safe_get(f"{statusChecker_API_URL}/info/rune")
    return _resp_val(data)

def clear_rune():
    _safe_post(f"{statusChecker_API_URL}/info/rune_clear")

def check_pos():
    data = _safe_get(f"{statusChecker_API_URL}/info/mypos")
    return _resp_val(data)

def get_exp_cycle():
    data = _safe_get(f"{statusChecker_API_URL}/cycle/get")
    return _resp_val(data, default=0)

def set_exp_cycle(cycle):
    _safe_post(f"{statusChecker_API_URL}/cycle/set?cycle={cycle}")

def capture_on():
    _safe_post(f"{statusChecker_API_URL}/capture/on", timeout=3)

def capture_off():
    _safe_post(f"{statusChecker_API_URL}/capture/off", timeout=3)

# ─── alarmHandler ───

def send_message(message, token=None):
    url = f"{alarmHandler_API_URL}/send_message?message={message}"
    if token is not None:
        url += f"&token={token}"
    try:
        response = requests.post(url, timeout=5)
        return response.status_code == 200
    except Exception as e:
        print(f"[gateway] send_message failed: {e}")
        return False

def clear_alarm():
    pass  # alarmHandler에 reset_cooldown 엔드포인트 없음 — 필요 시 추가

# ─── intrAction ───

def continue_main():
    _safe_post(f"{intrAction_API_URL}/continue")

def clear_intr():
    _safe_post(f"{intrAction_API_URL}/reset", timeout=10)

def add_intr(intr):
    return _safe_post(f"{intrAction_API_URL}/add_intr/{intr}", timeout=10)

def get_intr_status():
    data = _safe_get(f"{intrAction_API_URL}/status", timeout=10)
    return data if data else {}

# ─── runeSolver ───

def awake_rune_solver():
    _safe_post(f"{runeSolver_API_URL}/awake_model")

def solve_rune():
    data = _safe_get(f"{runeSolver_API_URL}/solve_rune")
    return _resp_val(data)

# ─── objectDetector ───

def find_in_screen(target: str, xywh: str | None = None, conf: str | None = None):
    res = find_in_screen_multiple(target, xywh, conf).get(target)
    return res[0] if res else None

def find_in_screen_yolo(model: str):
    data = _safe_get(f"{objectDetector_API_URL}/detect/yolo?req_model={model}")
    return _resp_val(data, default=[])

def find_in_screen_multiple(targets: str, xywh: str | None = None, confs: str | None = None) -> dict:
    url = f"{objectDetector_API_URL}/detect/img_multiple?req_imgs={targets}"
    if xywh is not None:
        url += f"&xywh={xywh}"
    if confs is not None:
        url += f"&confs={confs}"
    data = _safe_get(url)
    return _resp_val(data, default={})

# ─── mainAction / process ───

def get_main_pid():
    data = _safe_get(f"{mainAction_API_URL}/pid", timeout=2)
    if data and data.get("resp") == 0:
        return data.get("pid")
    return None


def get_running_build():
    resp = _safe_get(f"{mainAction_API_URL}/weeing/running_build")
    if resp :
        return resp
    return {}

def goto_point(x, y, tolerance = 1):
    resp = _safe_post(f"{mainAction_API_URL}/goto_point?x={x}&y={y}&tolerance={tolerance}")
    assert resp is not None, "Failed to call goto_point API"


def get_main_process():
    try:
        pid = get_main_pid()
        if pid is None:
            return None
        proc = psutil.Process(pid)
        if proc.is_running():
            return proc
    except psutil.NoSuchProcess:
        pass
    return None

def suspend_main():
    proc = get_main_process()
    if proc:
        proc.suspend()
        print(f"[process] Suspended PID {proc.pid}")
        return True
    print("[process] No main process to suspend")
    return False

def resume_main():
    clear_status()
    clear_intr()
    proc = get_main_process()
    if proc:
        proc.resume()
        print(f"[process] Resumed PID {proc.pid}")
        return True
    print("[process] No main process to resume")
    return False

def kill_main():
    proc = get_main_process()
    if proc:
        proc.kill()
        print(f"[process] Killed PID {proc.pid}")
        return True
    print("[process] No main process to kill")
    return False

# ─── misc ───

def prob(percent):
    return random() < percent / 100

def reset_external_states():
    """외부 서비스 상태를 모두 초기화 (시작/종료 시 호출)"""
    Error_list = []
    pipeline = [
        capture_off, 
        releaseAll,
        off,
        clear_status,
        clear_rune,
        clear_alarm,
        clear_intr
    ]

    for func in pipeline:
        try:
            func()
        except Exception:
            Error_list.append(func.__name__)

    if Error_list:
        print(f"[gateway] WARNING: reset_external_states had errors in: {', '.join(Error_list)}")
