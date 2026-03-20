import threading
from gateway import *\
from pipeline import *

# 모델 경로 설정
VIOL_MODEL_PATH = "viol_250309.pt"
NOONAL_MODEL_PATH = "noonal.pt"

# 결과 저장 및 동기화용 전역 변수
_pipeline_result = None
_pipeline_done = threading.Event()
_stop_flag = threading.Event()  # supervisor가 pipeline을 중단시킬 때 사용


def _run_pipeline(x: int, y: int, w: int, h: int, debug: bool):
    """
    파이프라인 스레드: viol 추론 실행
    """
    global _pipeline_result
    
    try:
        pipeline = NoonalPipeline(
            viol_model_path=VIOL_MODEL_PATH,
            noonal_model_path=NOONAL_MODEL_PATH,
            trigger=ButtonTrigger(),
            screen_region=(x, y, w, h),
            debug=debug
        )
        
        # pipeline에 stop_flag 전달 (중단 가능하도록)
        pipeline.stop_flag = _stop_flag
        
        # 4라운드 실행
        results = pipeline.run(num_rounds=4)
        
        if results is None:
            send_message("You Died From Viol")
            _pipeline_result = None
        else:
            print(f"[ViolSolver] 완료! 결과: {[r['position'] for r in results]}")
            _pipeline_result = results
            
    except Exception as e:
        print(f"[ViolSolver] 에러 발생: {e}")
        _pipeline_result = None
    finally:
        _pipeline_done.set()


def _run_supervisor(check_interval: float = 3.0):
    """
    Supervisor 스레드: 주기적으로 위치 확인
    
    Args:
        check_interval: 위치 체크 주기 (초)
    """
    print("[Supervisor] 시작")
    
    while not _pipeline_done.is_set() and not _stop_flag.is_set():
        # 위치 확인 (3번 시도)
        pos_found = False
        for _ in range(3):
            pos = check_pos()
            if pos != (1050, 1050):
                pos_found = True
                break
            time.sleep(0.1)
        
        if not pos_found:
            print("[Supervisor] 내 위치를 찾을 수 없음. 파이프라인 중단 신호 전송.")
            _stop_flag.set()  # pipeline에 중단 신호
            break
        
        # 다음 체크까지 대기 (파이프라인 완료 여부 확인하면서)
        _pipeline_done.wait(timeout=check_interval)
    
    print("[Supervisor] 종료")


def solveViol(x: int=450, y: int=300, w: int=480, h: int=270, debug: bool=False):
    """
    Viol 문제 해결: Pipeline과 Supervisor가 병렬 실행
    
    구조:
    - Pipeline 스레드: viol 추론 및 클릭
    - Supervisor 스레드: 주기적으로 위치 체크, 실패 시 pipeline 중단
    """
    global _pipeline_result, _pipeline_done, _stop_flag
    
    # src/img/newlie.png 이 사라질때까지 반복문
    while True:
        detected_result = find_in_screen("notice_viol")
        if detected_result is None:
            break

    time.sleep(2)

    # 이벤트 초기화
    _pipeline_done.clear()
    _stop_flag.clear()
    _pipeline_result = None

    # 두 스레드 동시 시작
    print("[ViolSolver] Pipeline + Supervisor 병렬 시작...")
    
    pipeline_thread = threading.Thread(
        target=_run_pipeline, 
        args=(x, y, w, h, debug), 
        daemon=True
    )
    supervisor_thread = threading.Thread(
        target=_run_supervisor,
        args=(3.0,),  # 3초마다 체크
        daemon=True
    )
    
    pipeline_thread.start()
    supervisor_thread.start()
    
    # 결과 대기
    _pipeline_done.wait()
    
    if _pipeline_result is None:
        exit(0)
    
    return _pipeline_result
