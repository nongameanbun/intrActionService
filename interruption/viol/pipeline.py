import cv2
import numpy as np
import mss
from ultralytics import YOLO
from .hybrid_tracker import Tracker
import pyautogui as pya
import os
import time
import threading
from queue import Queue, LifoQueue
from gateway import *
import  random

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# 버튼 좌표 설정 (영상 내 좌표 기준)
BUTTON_BASE_X = 76      # 1번 버튼 중심 X
BUTTON_BASE_Y = 230     # 버튼 중심 Y  
BUTTON_GAP_X = 104      # 버튼 간 X 간격


# ============================================================
# 트리거 조건 함수 (직접 수정 가능)
# ============================================================

class ButtonTrigger:
    """
    버튼 영역의 파란색 픽셀 비율 기반 트리거
    
    영상 하단 5% 영역(x: 5%~95%)에서 파란색 픽셀이 일정 비율 이상이면 enabled로 판단
    """
    
    def __init__(self, blue_threshold: float = 0.05):
        """
        Args:
            blue_threshold: enabled 판정 파란색 픽셀 비율 임계값 (1% 이상이면 트리거)
        """
        self.blue_threshold = blue_threshold
        self.prev_state = 'disabled'
        
        # 파란색 범위 (HSV) - 넓은 범위
        self.blue_lower = np.array([90, 50, 50])
        self.blue_upper = np.array([130, 255, 255])
    
    def reset(self):
        """상태 초기화"""
        self.prev_state = 'disabled'
    
    def check(self, frame) -> tuple:
        """
        트리거 조건 체크
        Returns:
            tuple: (is_triggered: bool, debug_value: dict)
        """
        # 버튼1 위치를 find_in_screen으로 동적으로 탐지
        button1_result = find_in_screen("button1")
        if button1_result is not None:
            debug_value = {
                'button1': find_in_screen("button1"),
                'button2': find_in_screen("button2"),
                'button3': find_in_screen("button3"),
                'botton4' : find_in_screen("button4")
            }
            return True, debug_value
        else:
            return False, {}
        

# ============================================================


def iou(box1, box2):
    """두 박스의 IoU 계산 (x,y,w,h 형식)"""
    x1, y1, w1, h1 = box1
    x2, y2, w2, h2 = box2
    
    xi1 = max(x1, x2)
    yi1 = max(y1, y2)
    xi2 = min(x1 + w1, x2 + w2)
    yi2 = min(y1 + h1, y2 + h2)
    
    inter = max(0, xi2 - xi1) * max(0, yi2 - yi1)
    union = w1 * h1 + w2 * h2 - inter
    
    return inter / union if union > 0 else 0


def get_center(box):
    """박스 중심점 반환"""
    x, y, w, h = box
    return (x + w/2, y + h/2)


def point_in_box(point, box):
    """점이 박스 안에 있는지 확인"""
    px, py = point
    x, y, w, h = box
    return x <= px <= x + w and y <= py <= y + h


class NoonalPipeline:
    """
    Noonal 상태 기반 트래킹 파이프라인 (화면 캡처 기반) - Release 아키텍처 통합 버전
    """
    
    def __init__(self, viol_model_path: str, noonal_model_path: str, 
                 trigger: ButtonTrigger = None, screen_region: tuple = None, debug: bool = True):
        self.viol_model = YOLO(viol_model_path)
        self.noonal_model = YOLO(noonal_model_path)
        self.tracker = Tracker(4)
        self.trigger = trigger if trigger else ButtonTrigger()
        self.target_id = None
        self.round_results = []
        self.screen_region = screen_region  # (x, y, w, h) 화면 좌표
        self.debug = debug
        self.running = False
        self.stop_flag = None
        
    def detect_noonal(self, frame):
        """noonal 모델로 1개 객체 검출"""
        results = self.noonal_model.predict(frame, conf=0.25, iou=0.5, verbose=False)
        dets = []
        if results and len(results[0].boxes) > 0:
            for b in results[0].boxes.xywh.cpu().numpy():
                dets.append((int(b[0] - b[2]/2), int(b[1] - b[3]/2), int(b[2]), int(b[3])))
        return dets
    
    def find_target(self, viol_dets, noonal_dets):
        """noonal 객체와 겹치는 viol 객체 찾기"""
        if not noonal_dets or not self.tracker.init:
            return None
        
        noonal_box = noonal_dets[0]
        noonal_center = get_center(noonal_box)
        
        best_track = None
        best_iou = 0
        
        for t in self.tracker.ts:
            track_box = (int(t.cx - t.w/2), int(t.cy - t.h/2), int(t.w), int(t.h))
            
            curr_iou = iou(track_box, noonal_box)
            if curr_iou > best_iou:
                best_iou = curr_iou
                best_track = t.tid
            
            if point_in_box(noonal_center, track_box):
                return t.tid
        
        return best_track if best_iou > 0 else None
    
    def get_position_of_target(self):
        """타겟 ID가 왼쪽에서 몇 번째인지 반환 (1-based)"""
        if self.target_id is None or not self.tracker.init:
            return None
        
        order = self.tracker.order()
        if self.target_id in order:
            return order.index(self.target_id) + 1
        return None
    
    def _find_button1_position(self):
        """find_in_screen('button1')으로 1번 버튼의 화면 절대 좌표를 찾아 캐싱"""
        result = find_in_screen("button1")
        if result is not None:
            (cx, cy), (bx, by, bw, bh) = result
            self.button1_screen_pos = (cx, cy)
            print(f"[Pipeline] button1 위치 탐지 성공: center=({cx}, {cy}), box=({bx}, {by}, {bw}, {bh})")
        else:
            print("[Pipeline] button1 위치 탐지 실패 — 하드코딩 폴백 사용")
            if self.screen_region:
                region_x, region_y, _, _ = self.screen_region
                self.button1_screen_pos = (region_x + BUTTON_BASE_X, region_y + BUTTON_BASE_Y)
            else:
                self.button1_screen_pos = (BUTTON_BASE_X, BUTTON_BASE_Y)

    def click_button(self, position: int):
        """N번째 버튼 클릭 (화면 좌표 기준, find_in_screen 기반)"""
        img_info = find_in_screen(f"button{position}")['center']
        target_x = img_info[0] + random.randint(-4, 4)
        target_y = img_info[1] - random.randint(30, 50)
        
        mouse_click("left", 50, target_x, target_y)
        print(f"  → 클릭 완료: ({target_x}, {target_y}) - {position}번째")
    
    def run(self, num_rounds: int = 4, start_delay: float = 0):
        """
        비동기 고성능 파이프라인 (Release 아키텍처)
        """
        if self.screen_region is None:
             raise RuntimeError("screen_region is required.")

        x, y, w, h = self.screen_region
        monitor = {"top": y, "left": x, "width": w, "height": h}
        
        if start_delay > 0:
            print(f"[Pipeline] {start_delay}초 후 시작...")
            time.sleep(start_delay)

        # 버튼1 위치 탐지 (run 시작 시 1회)
        self._find_button1_position()

        # 공유 데이터 설정 (Release 패턴)
        self.frame_buffer = LifoQueue(maxsize=1)
        self.inference_results = Queue(maxsize=1)
        self.running = True
        self.target_id = None
        self.round_results = []
        
        # FPS 계산용 변수
        self.fps_avg = 0
        fps_start_time = time.time()
        fps_counter = 0

        # 1. Inference Thread (Release 버전 로직)
        def inference_worker():
            print("[Inference] Thread Started")
            while self.running:
                # stop_flag 체크
                if self.stop_flag and self.stop_flag.is_set():
                    break
                    
                try:
                    frame = self.frame_buffer.get(timeout=0.1)
                    
                    # Inference (half=True 가속 적용 시도)
                    # CUDA 사용 가능 여부에 따라 자동 처리됨
                    results = self.viol_model.predict(frame, conf=0.25, iou=0.5, verbose=False)
                    
                    dets = []
                    if results and len(results[0].boxes) > 0:
                        for b in results[0].boxes.xywh.cpu().numpy():
                            dets.append((int(b[0] - b[2]/2), int(b[1] - b[3]/2), int(b[2]), int(b[3])))
                    
                    # Target 초기 식별을 위한 Noonal 검출
                    noonal_dets = []
                    if self.target_id is None:
                        noonal_dets = self.detect_noonal(frame)
                    
                    if not self.inference_results.full():
                        self.inference_results.put((dets, noonal_dets))
                except:
                    continue
            print("[Inference] Thread Stopped")

        inf_thread = threading.Thread(target=inference_worker, daemon=True)
        inf_thread.start()

        # 2. Capture & Tracker Loop (Main Thread)
        print("[Tracking] Loop Started (High-Freq)")
        current_round = 0
        self.trigger.reset()
        
        try:
            with mss.mss() as sct:
                while current_round < num_rounds:
                    t_loop = time.time()
                    
                    # stop_flag 체크
                    if self.stop_flag and self.stop_flag.is_set():
                        print("[Pipeline] Stop signal received.")
                        break
                    
                    # 캡처 (MSS 활용)
                    img = sct.grab(monitor)
                    frame = cv2.cvtColor(np.array(img), cv2.COLOR_BGRA2BGR)
                    
                    # LIFO 버퍼 업데이트 (최신 프레임 1장만 유지)
                    if self.frame_buffer.full():
                        try: self.frame_buffer.get_nowait()
                        except: pass
                    self.frame_buffer.put(frame)

                    # 비동기 추론 결과 확인
                    snap_dets = []
                    noonal_dets = []
                    if not self.inference_results.empty():
                        snap_dets, noonal_dets = self.inference_results.get()
                        
                    # 트래커 업데이트
                    if snap_dets:
                        # Full Update (Correction)
                        self.tracker.update(snap_dets)
                        
                        # 타겟 최초 식별
                        if self.target_id is None and self.tracker.init:
                            new_target = self.find_target(snap_dets, noonal_dets)
                            if new_target:
                                self.target_id = new_target
                                print(f"Target Acquired: ID {self.target_id}")
                    else:
                        # Kalman Smoothing (Prediction Only)
                        if self.tracker.init:
                            for t in self.tracker.ts:
                                t.cx += t.vx
                                t.cy += t.vy

                    # 트리거 체크 (모든 캡처 프레임에서 수행 - 4초 데드라인 보장)
                    is_transition, debug = self.trigger.check(frame)
                    if is_transition:
                        current_round += 1
                        pos = self.get_position_of_target()
                        
                        self.round_results.append({
                            'round': current_round,
                            'target_id': self.target_id,
                            'position': pos
                        })
                        
                        print(f"▶ 라운드 {current_round}: 위치 {pos}번째")
                        if pos:
                            self.click_button(pos)

                    # FPS 계산
                    fps_counter += 1
                    if time.time() - fps_start_time >= 1.0:
                        self.fps_avg = fps_counter / (time.time() - fps_start_time)
                        print(f"[Pipeline] Current Performance: {self.fps_avg:.1f} FPS")
                        fps_counter = 0
                        fps_start_time = time.time()
                    
                    # 60 FPS 제어 (16.6ms 주기)
                    elapsed = (time.time() - t_loop)
                    wait = max(0.001, 0.016 - elapsed)
                    time.sleep(wait)
        finally:
            self.running = False
            inf_thread.join(timeout=1.0)
            
        return self.round_results
