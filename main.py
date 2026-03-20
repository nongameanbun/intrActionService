from fastapi import FastAPI
from threading import Thread, Lock
import uvicorn
import winsound
from interruptions import intr_functions
from gateway import *

app = FastAPI(title="IntrAction API", description="인터럽션 관리 서버")

current_intr_thread = None
intr_lock = Lock()
last_intr_result = None        # "normal" | "wait" | "go"

def cleanup_intr() :
    global current_intr_thread
    with intr_lock :
        if current_intr_thread and not current_intr_thread.is_alive() :
            print(f"[IntrAction] Cleaning up interrupt thread: {current_intr_thread}")
            current_intr_thread = None


def sound_alert():
    winsound.Beep(880, 400)
    winsound.Beep(880, 400)

def run_interruption(intr_func) :
    global last_intr_result, current_intr_thread

    for _ in range(3) :
        sound_alert()

    press_key_with_delay("f11", 100)
        
    try:
        releaseAll()
    
        res = intr_func()
    
        if res == "exit" :
            kill_main()
        elif res == "wait" :
            pass
        else :
            resume_main()
    finally:
        with intr_lock:
            current_intr_thread = None

@app.post("/add_intr/{intr_name}", summary="인터럽트 추가")
async def add_intr(intr_name : str) :
    print(f"[IntrAction/main.py] Received interrupt request: {intr_name}")
    global current_intr_thread

    cleanup_intr()

    intr_func = intr_functions.get(intr_name, None)
    if not intr_func :
        return {"resp": -1, "message": f"Unknown interrupt: {intr_name}"}

    if is_waiting_for_continue() :
        print("[IntrAction] Main process is not waiting for continue, cannot start interrupt")
        return {"resp": -1, "message": "Main process is not waiting for continue"}

    if not suspend_main() :
        return {"resp": -1, "message": "Failed to suspend main process"}

    with intr_lock :
        if current_intr_thread and current_intr_thread.is_alive() :
            # 실행 중인 인터럽트가 있는 경우 오류 반환
            return {"resp": -1, "message": "Another interrupt is already running"}

        current_intr_thread = Thread(target=run_interruption, args=(intr_func,), daemon=True)
        send_message(f"Interrupt '{intr_name}' started")
        current_intr_thread.start()

    return {"resp": 0, "message": f"Interrupt '{intr_name}' started"}

@app.post("/continue", summary="일시정지 해제")
async def continue_intr() :
    print("Continue requested")
    cleanup_intr()

    with intr_lock :
        if current_intr_thread and current_intr_thread.is_alive() :
            return {"resp": -1, "message": "Interrupt still running"}

    if resume_main() :
        return {"resp": 0, "message": "Main process resumed"}
    return {"resp": -1, "message": "No main process to resume"}

@app.post("/reset", summary="인터럽트 상태 완전 초기화")
async def reset_intr() :
    """빌드 시작/종료 시 호출 — intr 스레드·결과를 깨끗이 리셋"""
    global current_intr_thread, last_intr_result

    with intr_lock :
        if current_intr_thread and current_intr_thread.is_alive() :
            current_intr_thread.join(timeout=3.0)
        current_intr_thread = None
        last_intr_result = None

    return {"resp": 0, "message": "Interrupt state reset"}

@app.get("/status", summary="인터럽트 상태 조회")
async def get_intr_status() :
    cleanup_intr()
    with intr_lock :
        if current_intr_thread and current_intr_thread.is_alive() :
            return {"resp": 0, "status": "running"}
    return {"resp": 0, "status": "idle", "last_result": last_intr_result}

if __name__ == "__main__" :
    uvicorn.run(app, host="0.0.0.0", port=8003, log_level="warning")