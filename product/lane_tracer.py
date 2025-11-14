"""
Line Tracer Integrated - 통합 라인 트레이서
교차로 감지 + 객체 인식 + 키보드 제어 통합 시스템

수정 사항 (2024-11-12):
- main() 함수명을 lane_follow_loop()으로 변경 (main.py와 연동)
- HSV 색상 범위 확장: [65, 20, 20] ~ [115, 255, 255]
- 픽셀 임계값 고정값 사용: 1200
- 라인 트레이싱 로직 단순화
"""
import cv2
import numpy as np
import time
import sys
import select
from gpiozero import DigitalOutputDevice, PWMOutputDevice
from collections import deque

# shared_state import 시도
try:
    import shared_state
    OBJECT_DETECTION_ENABLED = True
except ImportError:
    OBJECT_DETECTION_ENABLED = False
    pass

# ============================================================
# 표지판 인식 큐 시스템
# ============================================================
recognized_signs = deque(maxlen=5)  # 최근 5개 표지판만 저장
last_sign_time = 0  # 마지막 표지판 인식 시간
SIGN_COOLDOWN = 3.0  # 동일 표지판 재인식 방지 시간 (초)

# ============================================================
# 객체 감지 안정성 설정
# ============================================================
DETECTION_FRAME_THRESHOLD = 10  # 연속 N 프레임 이상 감지되어야 동작 실행 (약 0.66초)

# ============================================================
# 로그 최적화를 위한 상태 추적 변수
# ============================================================
last_detected_objects = set()  # 이전 프레임에서 감지된 객체
last_cooldown_warnings = {}  # 쿨다운 경고 마지막 출력 시간

# ============================================================
# 모터 / 부저 설정 (Lazy Initialization)
# ============================================================
# GPIO 객체들을 None으로 초기화 (실제 초기화는 init_gpio에서)
PWMA = None
AIN1 = None
AIN2 = None

PWMB = None
BIN1 = None
BIN2 = None

BUZZER = None

def init_gpio():
    """GPIO 초기화 - 프로그램 시작 시 한 번 호출"""
    global PWMA, AIN1, AIN2, PWMB, BIN1, BIN2, BUZZER

    try:
        # 기존 GPIO 정리 (있다면)
        if PWMA is not None:
            PWMA.close()
        if AIN1 is not None:
            AIN1.close()
        if AIN2 is not None:
            AIN2.close()
        if PWMB is not None:
            PWMB.close()
        if BIN1 is not None:
            BIN1.close()
        if BIN2 is not None:
            BIN2.close()
        if BUZZER is not None:
            BUZZER.close()
    except:
        pass

    # 새로 초기화
    PWMA = PWMOutputDevice(18)
    AIN1 = DigitalOutputDevice(22)
    AIN2 = DigitalOutputDevice(27)

    PWMB = PWMOutputDevice(23)
    BIN1 = DigitalOutputDevice(25)
    BIN2 = DigitalOutputDevice(24)

    # 부저 설정
    try:
        BUZZER = DigitalOutputDevice(12)
    except Exception:
        BUZZER = None
        pass

# 속도 프로파일 (단순화 버전과 동일)
SPEED_FORWARD_DEFAULT = 0.75  # 기본 직진 속도
SPEED_TURN_DEFAULT = 0.55     # 기본 회전 속도
SPEED_SLOW_FORWARD = 0.25     # 감속 직진
SPEED_SLOW_TURN = 0.20         # 감속 회전

# 현재 속도 (동적 변경용)
SPEED_FORWARD = SPEED_FORWARD_DEFAULT
SPEED_TURN = SPEED_TURN_DEFAULT

# ============================================================
# 모터 제어 함수
# ============================================================
def motor_forward():
    """전진"""
    AIN1.value = 0
    AIN2.value = 1
    PWMA.value = SPEED_FORWARD
    BIN1.value = 0
    BIN2.value = 1
    PWMB.value = SPEED_FORWARD

def motor_left(intensity=1.0):
    """좌회전 - intensity로 회전 강도 조절 (0.0~1.0)"""
    # 급격한 회전: 안쪽 바퀴를 후진시킴 (intensity > 0.5일 때)
    if intensity > 0.5:
        # 제자리 회전에 가까운 동작
        AIN1.value = 1  # 왼쪽 후진
        AIN2.value = 0
        PWMA.value = SPEED_TURN * 0.3 * intensity
        BIN1.value = 0  # 오른쪽 전진
        BIN2.value = 1
        PWMB.value = SPEED_TURN * 1.2 * intensity
    else:
        # 일반 회전: 안쪽 바퀴 느리게
        left_ratio = 0.0  # 안쪽 바퀴 정지
        right_ratio = 1.2 * intensity  # 바깥쪽 바퀴 더 빠르게
        AIN1.value = 0
        AIN2.value = 1
        PWMA.value = SPEED_TURN * left_ratio
        BIN1.value = 0
        BIN2.value = 1
        PWMB.value = SPEED_TURN * right_ratio

def motor_right(intensity=1.0):
    """우회전 - intensity로 회전 강도 조절 (0.0~1.0)"""
    # 급격한 회전: 안쪽 바퀴를 후진시킴 (intensity > 0.5일 때)
    if intensity > 0.5:
        # 제자리 회전에 가까운 동작
        AIN1.value = 0  # 왼쪽 전진
        AIN2.value = 1
        PWMA.value = SPEED_TURN * 1.2 * intensity
        BIN1.value = 1  # 오른쪽 후진
        BIN2.value = 0
        PWMB.value = SPEED_TURN * 0.3 * intensity
    else:
        # 일반 회전: 안쪽 바퀴 느리게
        left_ratio = 1.2 * intensity  # 바깥쪽 바퀴 더 빠르게
        right_ratio = 0.0  # 안쪽 바퀴 정지
        AIN1.value = 0
        AIN2.value = 1
        PWMA.value = SPEED_TURN * left_ratio
        BIN1.value = 0
        BIN2.value = 1
        PWMB.value = SPEED_TURN * right_ratio

def motor_stop():
    """정지 - 완전한 브레이크 모드"""
    AIN1.value = 0
    AIN2.value = 0  # 왼쪽 모터 브레이크
    PWMA.value = 0.0
    BIN1.value = 0
    BIN2.value = 0  # 오른쪽 모터 브레이크
    PWMB.value = 0.0

def motor_backward():
    """후진 - 비정상 픽셀 값 감지 시"""
    AIN1.value = 1
    AIN2.value = 0
    PWMA.value = SPEED_FORWARD * 0.5  # 느리게 후진
    BIN1.value = 1
    BIN2.value = 0
    PWMB.value = SPEED_FORWARD * 0.5

def set_slow_mode():
    """감속 모드 설정"""
    global SPEED_FORWARD, SPEED_TURN
    SPEED_FORWARD = SPEED_SLOW_FORWARD
    SPEED_TURN = SPEED_SLOW_TURN
    pass

def restore_speed():
    """정상 속도 복원"""
    global SPEED_FORWARD, SPEED_TURN
    SPEED_FORWARD = SPEED_FORWARD_DEFAULT
    SPEED_TURN = SPEED_TURN_DEFAULT
    pass

def beep(sec=1.0):
    """부저 울리기"""
    if BUZZER:
        BUZZER.value = 1
        time.sleep(sec)
        BUZZER.value = 0
    else:
        pass
        time.sleep(sec)

# ============================================================
# 유틸리티 함수
# ============================================================
def get_user_input():
    """사용자 입력 확인 (non-blocking)"""
    if select.select([sys.stdin], [], [], 0)[0]:
        try:
            key = sys.stdin.read(1).lower()
            return key
        except:
            return None
    return None

# ============================================================
# 객체 인식 트리거 처리 (shared_state 기반)
# ============================================================
def handle_runtime_triggers(frame_count=0):
    """주행 중 객체 인식 트리거 처리"""
    global SPEED_FORWARD, last_detected_objects  # 함수 시작 부분에 global 선언

    if not OBJECT_DETECTION_ENABLED:
        return False

    handled = False
    timestamp = time.strftime("%H:%M:%S")

    with shared_state.lock:
        obj_state = shared_state.object_state.copy()
        trig = shared_state.last_trigger
        # 신뢰도 및 프레임 카운트 정보 가져오기
        confidence = getattr(shared_state, 'confidence', {})
        detection_frames = getattr(shared_state, 'detection_frames', {})

    # 객체 상태 확인 및 알림 (상태 변경 시에만)
    current_detected = set([k for k, v in obj_state.items() if v])

    if current_detected:
        # 새로 감지된 객체만 알림
        new_objects = current_detected - last_detected_objects

        if new_objects:
            for obj in new_objects:
                # 객체별 명확한 알림
                obj_names = {
                    'stop': '🛑 STOP',
                    'slow': '⚠️ SLOW',
                    'horn': '📢 HORN',
                    'traffic': '🚦 신호등',
                    'go_straight': '⬆️ 직진',
                    'turn_left': '⬅️ 좌회전',
                    'turn_right': '➡️ 우회전'
                }
                obj_display = obj_names.get(obj, obj.upper())
                conf = confidence.get(obj, 0) if confidence else 0

                # 간결한 알림
                conf_str = f" (신뢰도: {conf:.1%})" if conf > 0 else ""
                pass

        last_detected_objects = current_detected
    else:
        # 객체가 사라지면 상태 리셋
        if last_detected_objects:
            last_detected_objects = set()
            try:
                with shared_state.lock:
                    # 저장된 표지판 플래그도 리셋
                    if hasattr(shared_state, 'stop_sign_stored'):
                        delattr(shared_state, 'stop_sign_stored')
                    if hasattr(shared_state, 'traffic_light_stored'):
                        delattr(shared_state, 'traffic_light_stored')
                    if hasattr(shared_state, 'slow_mode_active'):
                        delattr(shared_state, 'slow_mode_active')
                    # 알림 플래그 리셋
                    for attr in dir(shared_state):
                        if attr.endswith('_notified'):
                            delattr(shared_state, attr)
            except:
                pass  # 플래그 리셋 실패는 무시

    # STOP 표지판 - 즉시 정지 (연속 프레임 체크 + 중복 실행 방지)
    if obj_state.get("stop"):
        frames = detection_frames.get("stop", 0)

        # 연속 프레임 임계값 체크
        if frames < DETECTION_FRAME_THRESHOLD:
            return handled  # 임계값 미달 시 처리 안 함

        conf = confidence.get("stop", 0) if confidence else 0
        current_time = time.time()

        # 중복 실행 체크
        can_execute = True
        with shared_state.lock:
            if "stop" in shared_state.action_last_time:
                time_since = current_time - shared_state.action_last_time["stop"]
                if time_since < shared_state.ACTION_COOLDOWN:
                    can_execute = False
                    # 쿨다운 경고는 첫 1회만 출력
                    if "stop" not in last_cooldown_warnings or (current_time - last_cooldown_warnings["stop"]) > 5:
                        pass
                        last_cooldown_warnings["stop"] = current_time

        if can_execute:
            pass
            pass

            # 즉시 정지
            motor_stop()
            pass
            time.sleep(2.0)  # 2초 정지

            # 정지 후 천천히 출발
            pass
            # 속도를 낮춰서 천천히 출발
            old_speed = SPEED_FORWARD
            SPEED_FORWARD = SPEED_SLOW_FORWARD
            motor_forward()
            time.sleep(0.5)
            SPEED_FORWARD = old_speed  # 원래 속도로 복구

            # 마지막 실행 시간 기록
            with shared_state.lock:
                shared_state.action_last_time["stop"] = current_time

        handled = True

    # SLOW 표지판 - 즉시 감속하지만 블로킹하지 않음 (연속 프레임 체크)
    elif obj_state.get("slow"):
        frames = detection_frames.get("slow", 0)

        # 연속 프레임 임계값 체크
        if frames >= DETECTION_FRAME_THRESHOLD:
            conf = confidence.get("slow", 0) if confidence else 0

            try:
                with shared_state.lock:
                    if not getattr(shared_state, 'slow_mode_active', False):
                        pass
                        pass
                        set_slow_mode()
                        # 3초 후 속도 복구를 위한 타이머 설정 (블로킹하지 않음)
                        shared_state.slow_mode_until = time.time() + 3.0
                        shared_state.slow_mode_active = True
            except:
                pass
        handled = True

    # HORN 표지판 (연속 프레임 체크 + 중복 실행 방지)
    elif obj_state.get("horn"):
        frames = detection_frames.get("horn", 0)

        # 연속 프레임 임계값 체크
        if frames < DETECTION_FRAME_THRESHOLD:
            return handled

        conf = confidence.get("horn", 0) if confidence else 0
        current_time = time.time()

        # 중복 실행 체크
        can_execute = True
        with shared_state.lock:
            if "horn" in shared_state.action_last_time:
                time_since = current_time - shared_state.action_last_time["horn"]
                if time_since < shared_state.ACTION_COOLDOWN:
                    can_execute = False
                    # 쿨다운 경고는 5초마다만 출력
                    if "horn" not in last_cooldown_warnings or (current_time - last_cooldown_warnings["horn"]) > 5:
                        pass
                        last_cooldown_warnings["horn"] = current_time

        if can_execute:
            pass
            pass
            beep(1.0)
            pass

            # 마지막 실행 시간 기록
            with shared_state.lock:
                shared_state.action_last_time["horn"] = current_time

        handled = True

    # 신호등 - 큐에 저장 (방향 표지판과 동일하게 처리)
    # store_direction_signs에서 처리됨

    # SLOW 모드 자동 해제 체크 (비블로킹 처리)
    try:
        with shared_state.lock:
            if hasattr(shared_state, 'slow_mode_until'):
                if time.time() > shared_state.slow_mode_until:
                    restore_speed()
                    delattr(shared_state, 'slow_mode_until')
                    shared_state.slow_mode_active = False
                    pass
    except:
        pass

    if handled:
        with shared_state.lock:
            shared_state.last_trigger = None
        pass

    return handled

# ============================================================
# 카메라 초기화
# ============================================================
def init_camera():
    """카메라 초기화 - 640x480 해상도"""
    max_retries = 3
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            from picamera2 import Picamera2
            pass

            # 카메라가 사용 중일 수 있으므로 잠시 대기
            if attempt > 0:
                pass
                time.sleep(retry_delay)

                # 카메라 관련 프로세스 종료 시도
                import subprocess
                subprocess.run(['pkill', '-f', 'libcamera'], capture_output=True)
                time.sleep(0.5)

            picam2 = Picamera2()
            config = picam2.create_preview_configuration(
                main={"format": "RGB888", "size": (640, 480)}
            )
            picam2.configure(config)
            picam2.start()
            time.sleep(2)

            pass

            class CameraWrapper:
                def read(self):
                    frame = picam2.capture_array()
                    # RGB 그대로 사용 (BGR 변환 제거)
                    return True, frame

                def release(self):
                    picam2.stop()

            return CameraWrapper()

        except Exception as e:
            pass

            if "Pipeline handler in use" in str(e):
                pass
                if attempt < max_retries - 1:
                    pass
                else:
                    pass
                    pass
                    pass
                    pass
                    pass
                    pass

    return None

# ============================================================
# 표지판 관리 함수
# ============================================================
def store_direction_signs(frame_count=0):
    """방향 표지판을 인식하여 큐에 저장만 함"""
    if not OBJECT_DETECTION_ENABLED:
        return

    global last_sign_time
    current_time = time.time()

    # 쿨다운 체크
    if current_time - last_sign_time < SIGN_COOLDOWN:
        return

    with shared_state.lock:
        obj_state = shared_state.object_state.copy()
        confidence = getattr(shared_state, 'confidence', {})
        detection_frames = getattr(shared_state, 'detection_frames', {})

    timestamp = time.strftime("%H:%M:%S")
    direction_signs = ["go_straight", "turn_left", "turn_right", "traffic"]  # 신호등 추가

    for sign in direction_signs:
        if obj_state.get(sign):
            frames = detection_frames.get(sign, 0)

            # 연속 프레임 임계값 체크
            if frames < DETECTION_FRAME_THRESHOLD:
                continue  # 임계값 미달 시 다음 표지판 체크

            conf = confidence.get(sign, 0) if confidence else 0

            # 신호등은 신뢰도 90% 이상만 저장
            if sign == "traffic" and conf < 0.90:
                continue

            sign_info = {
                'type': sign,
                'confidence': conf,
                'time': current_time,
                'timestamp': timestamp,
                'frame': frame_count,
                'detection_frames': frames  # 감지 프레임 수 저장
            }

            # 큐에 저장 (중복 방지)
            if not recognized_signs or recognized_signs[-1]['type'] != sign:
                recognized_signs.append(sign_info)
                last_sign_time = current_time

                # 간결한 인식 로그
                sign_icons = {
                    "go_straight": "⬆️ 직진",
                    "turn_left": "⬅️ 좌회전",
                    "turn_right": "➡️ 우회전",
                    "traffic": "🚦 신호등"  # 신호등 추가
                }
                sign_name = sign_icons.get(sign, sign)
                conf_str = f" (신뢰도: {conf:.2f})" if conf > 0 else ""
                pass
                break  # 한 번에 하나만 저장

# ============================================================
# 균형 바 생성
# ============================================================
def create_balance_bar(left_ratio, right_ratio):
    """좌우 균형 시각화 바 생성"""
    bar_length = 20

    if left_ratio == 0 and right_ratio == 0:
        return "[" + " " * bar_length + "]"

    left_bars = int(left_ratio * bar_length)
    right_bars = int(right_ratio * bar_length)

    bar = "L[" + "█" * left_bars + " " * (bar_length - left_bars) + "|" + \
          "█" * right_bars + " " * (bar_length - right_bars) + "]R"

    return bar

# ============================================================
# 메인 루프
# ============================================================
def lane_follow_loop():
    """통합 라인 트레이서 메인 루프"""
    pass
    pass
    pass

    # GPIO 초기화 (중요: 프로그램 시작 시 GPIO 설정)
    pass
    init_gpio()
    pass

    pass
    pass
    pass
    pass
    pass
    pass
    pass
    pass
    pass
    pass
    pass
    pass

    if OBJECT_DETECTION_ENABLED:
        pass
        pass
        pass
        pass

        # shared_state 초기 상태 확인
        try:
            with shared_state.lock:
                _ = shared_state.object_state.copy()  # 연결 테스트
            pass
        except Exception as e:
            pass
    else:
        pass

    pass
    pass
    pass

    camera = init_camera()
    if not camera:
        return

    # HSV 범위 - 청록색(Cyan) 라인용 (확장된 범위)
    lower_cyan = np.array([65, 20, 20])
    upper_cyan = np.array([115, 255, 255])

    start_time = time.time()
    frame_count = 0
    action_stats = {"FORWARD": 0, "LEFT": 0, "RIGHT": 0, "STOP": 0, "INTERSECTION": 0, "BACKWARD": 0}

    # 현재 동작 상태 초기화 (오류 수정)
    action = "STOP"

    # 동적 균형 임계값 (속도 기반 - 개선된 버전)
    BASE_BALANCE_THRESHOLD = 0.35  # 기본 균형 임계값 (저속/중속)
    HIGH_SPEED_BALANCE_THRESHOLD = 0.25  # 고속 시 균형 임계값 (더 민감)

    # 박스 크기 설정 (해상도에 맞춰)
    BOX_WIDTH_RATIO = 0.25   # 화면 너비의 25%
    BOX_HEIGHT_RATIO = 0.25  # 화면 높이의 25%

    # 박스 크기 초기화 (640x480 기준)
    width = 640
    height = 480
    BOX_WIDTH = int(width * BOX_WIDTH_RATIO)
    BOX_HEIGHT = int(height * BOX_HEIGHT_RATIO)

    # 픽셀 임계값 (고정값)
    PIXEL_THRESHOLD = 800  # 라인 감지 임계값 (더 민감하게 조정)
    CENTER_THRESHOLD = 5000  # 교차로 감지 임계값 (고정)

    # 한쪽 라인 없을 때 직진 타이머 (개선된 버전)
    one_side_missing_time = None
    one_side_missing_direction = None
    STRAIGHT_DURATION = 0.5  # 한쪽 없을 때 직진 시간

    # 라인 탐색 방향 (마지막으로 본 방향)
    last_seen_side = None  # 'LEFT' or 'RIGHT'

    # 교차로 모드 관련 변수
    intersection_mode = False
    intersection_exit_time = None
    intersection_wait_start = None  # 교차로 대기 시작 시간
    INTERSECTION_EXIT_DURATION = 2.0
    INTERSECTION_TIMEOUT = 5.0  # 교차로 대기 타임아웃 (5초)

    # 라인 손실 관련
    line_lost_time = None

    # 차량 상태 관련
    vehicle_stopped = False  # 차량 정지 상태
    stop_reason = None  # 정지 이유

    # 높은 픽셀 값 감지 및 후진 모드
    HIGH_PIXEL_THRESHOLD = 12000  # 비정상 픽셀 값 임계값
    HIGH_PIXEL_DURATION = 0.5     # 0.5초 이상 지속 시 후진
    high_pixel_start_time = None  # 높은 픽셀 값 감지 시작 시간
    reverse_mode = False          # 후진 모드 플래그

    try:
        while True:
            ret, frame = camera.read()
            if not ret:
                pass
                break

            frame_count += 1

            # 이미지 뒤집기
            frame = cv2.flip(frame, -1)

            # 전체 프레임 크기
            height, width = frame.shape[:2]

            # ====== 차량 정지 상태 판단 ======
            # 교차로 모드일 때만 vehicle_stopped 사용
            if intersection_mode:
                if not vehicle_stopped:
                    vehicle_stopped = True
                    stop_reason = "교차로 대기"
            else:
                if vehicle_stopped and stop_reason == "교차로 대기":
                    vehicle_stopped = False
                    stop_reason = None

            # shared_state에 프레임 전달 (객체 인식용) - 정지 중에도 객체 인식은 계속
            if OBJECT_DETECTION_ENABLED and frame_count % 3 == 0:
                try:
                    with shared_state.lock:
                        shared_state.latest_frame = frame.copy()
                        # 차량 주행 중일 때만 로깅 (90프레임마다)
                        if not vehicle_stopped and frame_count % 90 == 0:
                            obj_module_active = getattr(shared_state, 'detector_active', False)
                            status = "활성" if obj_module_active else "대기"
                            pass
                except Exception as e:
                    if not vehicle_stopped and frame_count % 90 == 0:
                        pass

            # ====== 방향 표지판을 큐에 저장 (주행 중에도 계속 인식) ======
            if OBJECT_DETECTION_ENABLED and frame_count % 5 == 0:
                store_direction_signs(frame_count)

                # 객체 인식 상태 디버그 (60프레임마다, 간결하게)
                if frame_count % 60 == 0:
                    with shared_state.lock:
                        active_objects = [k for k, v in shared_state.object_state.items() if v]
                        if active_objects or recognized_signs:
                            obj_str = f"활성: {', '.join(active_objects)}" if active_objects else "없음"
                            queue_str = f"큐: {len(recognized_signs)}개" if recognized_signs else ""
                            pass

            # ====== 교차로에서만 특별 처리 ======
            if vehicle_stopped and stop_reason == "교차로 대기":
                # 교차로에서는 라인 인식 건너뛰기
                left_pixels = 0
                right_pixels = 0
                center_pixels = 0
                total_pixels = 0
                left_ratio = 0.0
                right_ratio = 0.0
                diff = 0.0

                # 박스 크기 계산
                BOX_WIDTH = int(width * BOX_WIDTH_RATIO)
                BOX_HEIGHT = int(height * BOX_HEIGHT_RATIO)

            else:
                # ====== 정상 주행 - 라인 인식 수행 ======
                # 동적 박스 크기 계산
                BOX_WIDTH = int(width * BOX_WIDTH_RATIO)
                BOX_HEIGHT = int(height * BOX_HEIGHT_RATIO)

                # PIXEL_THRESHOLD는 이미 고정값으로 설정됨 (1200)

                # 좌하단 박스
                left_box_x1 = 0
                left_box_y1 = height - BOX_HEIGHT
                left_box_x2 = BOX_WIDTH
                left_box_y2 = height
                left_box = frame[left_box_y1:left_box_y2, left_box_x1:left_box_x2]

                # 우하단 박스
                right_box_x1 = width - BOX_WIDTH
                right_box_y1 = height - BOX_HEIGHT
                right_box_x2 = width
                right_box_y2 = height
                right_box = frame[right_box_y1:right_box_y2, right_box_x1:right_box_x2]

                # 전방 중앙 박스 (교차로 감지용)
                center_box_width = int(width * 0.6)  # 화면 너비의 60%
                center_box_height = int(height * 0.15)  # 화면 높이의 15%
                center_box_x1 = (width - center_box_width) // 2
                center_box_y1 = int(height * 0.3)  # 화면 상단 30% 위치
                center_box_x2 = center_box_x1 + center_box_width
                center_box_y2 = center_box_y1 + center_box_height

                # ====== HSV 변환 최적화: 전체 프레임 1회 변환 ======
                hsv_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)

                # 좌측 박스 처리 (HSV 프레임에서 슬라이싱)
                hsv_left = hsv_frame[left_box_y1:left_box_y2, left_box_x1:left_box_x2]
                mask_left = cv2.inRange(hsv_left, lower_cyan, upper_cyan)

                # 노이즈 제거
                kernel = np.ones((3, 3), np.uint8)
                mask_left = cv2.erode(mask_left, kernel, iterations=2)
                mask_left = cv2.dilate(mask_left, kernel, iterations=3)

                # 우측 박스 처리 (HSV 프레임에서 슬라이싱)
                hsv_right = hsv_frame[right_box_y1:right_box_y2, right_box_x1:right_box_x2]
                mask_right = cv2.inRange(hsv_right, lower_cyan, upper_cyan)
                mask_right = cv2.erode(mask_right, kernel, iterations=2)
                mask_right = cv2.dilate(mask_right, kernel, iterations=3)

                # 전방 중앙 박스 처리 (HSV 프레임에서 슬라이싱)
                hsv_center = hsv_frame[center_box_y1:center_box_y2, center_box_x1:center_box_x2]
                mask_center = cv2.inRange(hsv_center, lower_cyan, upper_cyan)
                mask_center = cv2.erode(mask_center, kernel, iterations=2)
                mask_center = cv2.dilate(mask_center, kernel, iterations=3)

                # 픽셀 수 계산
                left_pixels = cv2.countNonZero(mask_left)
                right_pixels = cv2.countNonZero(mask_right)
                center_pixels = cv2.countNonZero(mask_center)
                total_pixels = left_pixels + right_pixels

                # CENTER_THRESHOLD는 이미 고정값으로 설정됨 (5000)

                # 좌우 비율 계산
                if total_pixels > 0:
                    left_ratio = left_pixels / total_pixels
                    right_ratio = right_pixels / total_pixels
                else:
                    left_ratio = 0.0
                    right_ratio = 0.0

                # 좌우 차이
                diff = abs(left_ratio - right_ratio)

            # 균형 임계값은 고정값 사용 (BALANCE_THRESHOLD)

            # ====== 높은 픽셀 값 감지 및 후진 처리 ======
            if left_pixels > HIGH_PIXEL_THRESHOLD or right_pixels > HIGH_PIXEL_THRESHOLD:
                # 높은 픽셀 값 감지
                if high_pixel_start_time is None:
                    high_pixel_start_time = time.time()
                    pass
                elif time.time() - high_pixel_start_time >= HIGH_PIXEL_DURATION:
                    # 0.5초 이상 지속됨 → 후진 모드 활성화
                    if not reverse_mode:
                        reverse_mode = True
                        pass
            else:
                # 정상 픽셀 값으로 복귀
                if reverse_mode:
                    reverse_mode = False
                    high_pixel_start_time = None
                    pass
                elif high_pixel_start_time is not None:
                    # 타이머만 리셋 (0.5초 전에 정상 복귀)
                    high_pixel_start_time = None

            # ====== 후진 모드 실행 ======
            if reverse_mode:
                motor_backward()
                action = "BACKWARD"
                pass
                # 후진 모드일 때는 다른 조향 결정 건너뛰기
                action_stats[action] += 1
                time.sleep(0.02)
                continue

            # 조향 결정
            action = "STOP"


            # ====== 교차로 모드에서 키보드 입력 처리 ======
            if intersection_mode:
                # 먼저 저장된 표지판 확인하여 자동 키 입력으로 변환
                user_input = None
                if OBJECT_DETECTION_ENABLED and recognized_signs:
                    sign_info = recognized_signs[0]  # 가장 먼저 저장된 표지판 확인
                    sign_type = sign_info['type']

                    # 표지판을 키 입력으로 변환
                    sign_to_key = {
                        'go_straight': 'w',
                        'turn_left': 'a',
                        'turn_right': 'd',
                        'traffic': 'd'  # 신호등은 우회전
                    }

                    if sign_type in sign_to_key:
                        user_input = sign_to_key[sign_type]
                        recognized_signs.popleft()  # 큐에서 제거
                        pass

                # 타임아웃 체크 (5초 경과 시 자동 직진)
                if not user_input and intersection_wait_start:
                    wait_time = time.time() - intersection_wait_start

                    if wait_time >= INTERSECTION_TIMEOUT:
                        pass
                        motor_forward()
                        action = "FORWARD"
                        intersection_mode = False
                        intersection_exit_time = time.time()
                        intersection_wait_start = None
                        vehicle_stopped = False
                        continue

                # 수동 키보드 입력 확인 (자동 입력이 없을 경우에만)
                if not user_input:
                    user_input = get_user_input()
                if user_input:
                    pass

                    if user_input == 'w':
                        motor_forward()
                        action = "FORWARD"
                        pass
                        intersection_mode = False
                        intersection_exit_time = time.time()
                        intersection_wait_start = None
                        vehicle_stopped = False
                    elif user_input == 'a':
                        pass
                        motor_forward()
                        time.sleep(0.5)  # 직진으로 접근
                        motor_left(1.0)  # 좌회전
                        time.sleep(1.2)  # 회전 시간 (충분히 회전)
                        motor_forward()
                        time.sleep(0.5)  # 라인 복귀 직진
                        action = "LEFT"
                        intersection_mode = False
                        intersection_exit_time = time.time()
                        intersection_wait_start = None
                        vehicle_stopped = False
                    elif user_input == 'd':
                        pass
                        motor_forward()
                        time.sleep(0.5)  # 직진으로 접근
                        motor_right(1.0)  # 우회전
                        time.sleep(1.2)  # 회전 시간 (충분히 회전)
                        motor_forward()
                        time.sleep(0.5)  # 라인 복귀 직진
                        action = "RIGHT"
                        intersection_mode = False
                        intersection_exit_time = time.time()
                        intersection_wait_start = None
                        vehicle_stopped = False
                    elif user_input == 's':
                        motor_stop()
                        action = "STOP"
                        pass
                else:
                    # 키보드 입력 대기 중
                    motor_stop()
                    action = "INTERSECTION"
                continue

            # ====== 교차로 탈출 중이면 일정 시간 교차로 감지 무시 ======
            if intersection_exit_time:
                elapsed = time.time() - intersection_exit_time
                if elapsed < INTERSECTION_EXIT_DURATION:
                    # 교차로 탈출 중 - 이전 동작 유지
                    pass
                else:
                    # 탈출 완료
                    intersection_exit_time = None

            # ====== 교차로 감지 (전방에 수평선이 있고 좌우 픽셀이 적을 때) ======
            elif not intersection_exit_time and center_pixels > CENTER_THRESHOLD and total_pixels < PIXEL_THRESHOLD * 2:
                if not intersection_mode:
                    motor_stop()
                    action = "INTERSECTION"
                    intersection_mode = True
                    intersection_wait_start = time.time()  # 타이머 시작
                    pass

                    # 저장된 표지판 확인
                    if OBJECT_DETECTION_ENABLED:
                        if recognized_signs:
                            pass
                            for i, sign in enumerate(recognized_signs):
                                sign_names = {
                                    'go_straight': '직진',
                                    'turn_left': '좌회전',
                                    'turn_right': '우회전',
                                    'traffic': '신호등(우회전)'
                                }
                                name = sign_names.get(sign['type'], sign['type'])
                                pass
                        else:
                            pass

                    pass
                    pass

            # ====== 라인이 거의 안 보일 때 (교차로가 아닌 경우) ======
            elif total_pixels < PIXEL_THRESHOLD:
                # 최초 라인 이탈 시에만 정지하고 메시지 출력
                if line_lost_time is None:
                    line_lost_time = time.time()
                    motor_stop()
                    action = "STOP"
                    pass
                    pass

                # 키보드 입력 확인
                user_input = get_user_input()
                if user_input:
                    if user_input == 'w':
                        motor_forward()
                        action = "FORWARD"
                        pass
                    elif user_input == 'a':
                        pass
                        motor_forward()
                        time.sleep(0.5)  # 직진으로 접근
                        motor_left(1.0)  # 좌회전
                        time.sleep(1.2)  # 회전 시간 (충분히 회전)
                        motor_forward()
                        time.sleep(0.5)  # 라인 복귀 직진
                        action = "LEFT"
                    elif user_input == 'd':
                        pass
                        motor_forward()
                        time.sleep(0.5)  # 직진으로 접근
                        motor_right(1.0)  # 우회전
                        time.sleep(1.2)  # 회전 시간 (충분히 회전)
                        motor_forward()
                        time.sleep(0.5)  # 라인 복귀 직진
                        action = "RIGHT"
                    elif user_input == 's':
                        motor_stop()
                        action = "STOP"
                        pass
                # 입력이 없으면 현재 동작 유지

            # ====== 라인이 충분히 보일 때 조향 제어 (개선된 비례 제어 버전) ======
            elif total_pixels >= PIXEL_THRESHOLD:
                # 라인 복귀 알림
                if line_lost_time is not None:
                    pass
                    line_lost_time = None

                vehicle_stopped = False  # 라인 찾으면 정지 상태 해제

                # 동적 임계값 계산 (속도 기반)
                is_high_speed = SPEED_FORWARD > 0.6
                current_balance_threshold = HIGH_SPEED_BALANCE_THRESHOLD if is_high_speed else BASE_BALANCE_THRESHOLD

                if diff < current_balance_threshold:
                    # 좌우 균형 잡힘 → 전진
                    motor_forward()
                    action = "FORWARD"
                    one_side_missing_time = None
                    one_side_missing_direction = None

                elif left_pixels > right_pixels:
                    # 왼쪽에 청록색이 많음 → 우회전 필요
                    last_seen_side = 'LEFT'  # 라인이 왼쪽에 있음

                    # 편차에 비례한 회전 강도 계산 (최대 편차 50%로 정규화)
                    turn_intensity = min(1.0, diff / 0.5)

                    if right_pixels < 50:
                        # 오른쪽 라인이 거의 없음
                        if one_side_missing_time is None or one_side_missing_direction != 'RIGHT':
                            one_side_missing_time = time.time()
                            one_side_missing_direction = 'RIGHT'

                        elapsed = time.time() - one_side_missing_time
                        if elapsed < STRAIGHT_DURATION:
                            # 직진 유지 (0.5초)
                            motor_forward()
                            action = "FORWARD"
                        else:
                            # 강한 우회전 (intensity * 1.5)
                            motor_right(min(1.0, turn_intensity * 1.5))
                            action = "RIGHT"
                    else:
                        # 일반 우회전 (비례 제어)
                        motor_right(turn_intensity)
                        action = "RIGHT"
                        one_side_missing_time = None
                        one_side_missing_direction = None

                else:
                    # 오른쪽에 청록색이 많음 → 좌회전 필요
                    last_seen_side = 'RIGHT'  # 라인이 오른쪽에 있음

                    # 편차에 비례한 회전 강도 계산 (최대 편차 50%로 정규화)
                    turn_intensity = min(1.0, diff / 0.5)

                    if left_pixels < 50:
                        # 왼쪽 라인이 거의 없음
                        if one_side_missing_time is None or one_side_missing_direction != 'LEFT':
                            one_side_missing_time = time.time()
                            one_side_missing_direction = 'LEFT'

                        elapsed = time.time() - one_side_missing_time
                        if elapsed < STRAIGHT_DURATION:
                            # 직진 유지 (0.5초)
                            motor_forward()
                            action = "FORWARD"
                        else:
                            # 강한 좌회전 (intensity * 1.5)
                            motor_left(min(1.0, turn_intensity * 1.5))
                            action = "LEFT"
                    else:
                        # 일반 좌회전 (비례 제어)
                        motor_left(turn_intensity)
                        action = "LEFT"
                        one_side_missing_time = None
                        one_side_missing_direction = None

                # 주행 중 객체 인식 트리거 처리
                handle_runtime_triggers(frame_count)

            # 통계 업데이트
            action_stats[action] += 1

            # 로그 출력 (60프레임마다, 간결하게) - 정지 상태일 때는 건너뛰기
            if frame_count % 60 == 0 and not vehicle_stopped:
                runtime = int(time.time() - start_time)

                # 상태 아이콘
                icons = {
                    "FORWARD": "↑",
                    "LEFT": "←",
                    "RIGHT": "→",
                    "INTERSECTION": "🛑",
                    "STOP": "■",
                    "BACKWARD": "↓"
                }
                icon = icons.get(action, "?")

                # 회전 강도 표시 (비례 제어 확인용)
                if action in ["LEFT", "RIGHT"] and 'turn_intensity' in locals():
                    intensity_str = f" ({turn_intensity:.2f})"
                else:
                    intensity_str = ""

                # 간결한 로그 출력
                pass

            time.sleep(0.02)  # 더 빠른 반응

    except KeyboardInterrupt:
        pass

    finally:
        runtime = int(time.time() - start_time)
        pass
        pass
        pass
        pass
        pass
        pass
        pass
        pass
        pass
        for action in ["FORWARD", "LEFT", "RIGHT", "INTERSECTION", "STOP", "BACKWARD"]:
            count = action_stats.get(action, 0)
            percentage = (count / max(frame_count, 1)) * 100
            bar = "█" * int(percentage / 2)
            pass
        pass

        # 성능 분석
        forward_ratio = action_stats["FORWARD"] / max(frame_count, 1)
        intersection_ratio = action_stats.get("INTERSECTION", 0) / max(frame_count, 1)
        stop_ratio = action_stats["STOP"] / max(frame_count, 1)

        if intersection_ratio > 0.1:
            pass
            pass
        elif stop_ratio > 0.7:
            pass
            pass
        elif forward_ratio > 0.5:
            pass
        elif forward_ratio > 0.3:
            pass
        else:
            pass

        pass
        pass
        pass
        pass
        pass
        pass
        pass

        # 객체 인식 통계 (활성화된 경우)
        if OBJECT_DETECTION_ENABLED:
            pass
            pass
            try:
                with shared_state.lock:
                    obj_counts = getattr(shared_state, 'detection_counts', {})

                if obj_counts:
                    for obj_type, count in obj_counts.items():
                        pass
                else:
                    pass
                pass
            except:
                pass

        pass

        # 모터 완전 정지
        motor_stop()
        PWMA.value = 0.0
        PWMB.value = 0.0
        camera.release()
        pass

if __name__ == '__main__':
    lane_follow_loop()