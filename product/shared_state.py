"""
shared_state.py
---------------
lane_tracer와 object_detector 간의 공유 상태
Lock을 이용해 thread-safe하게 접근 가능
"""

from threading import Lock

lock = Lock()

# ============================================================
# 객체 관련 상태 
# ============================================================

# 인식 가능한 객체 목록
KNOWN_OBJECTS = [
    "go_straight", "turn_left", "turn_right",
    "stop", "slow", "horn",
    "traffic"
]

# 각 객체별 감지 상태 및 정보
object_state = {name: False for name in KNOWN_OBJECTS}   # 현재 감지 여부
object_area = {name: 0 for name in KNOWN_OBJECTS}        # 최근 감지 면적
object_last_seen = {name: 0.0 for name in KNOWN_OBJECTS} # 마지막 감지 시각
confidence = {name: 0.0 for name in KNOWN_OBJECTS}       # 신뢰도 (0.0 ~ 1.0)
detection_frames = {name: 0 for name in KNOWN_OBJECTS}   # 연속 감지 프레임 수

# 근접 이벤트용 (lane_tracer / detector 간 1회성 트리거)
last_trigger = None

# 간단 로그용 (main.py 모니터 출력용)
object_detected = None        # 가장 최근 감지된 객체 이름
object_distance = 0           # 해당 객체의 감지 면적 (근사 거리)

# ============================================================
# 신호등 관련 (traffic 객체와 병행 사용)
# ============================================================

traffic_light_area = 0        # 신호등 감지 면적
traffic_light_last_ts = 0.0   # 마지막 감지 시각
right_turn_done = False       # 우회전 완료 여부

# ============================================================
# 동작 중복 실행 방지용
# ============================================================

action_executed = {}          # 각 객체별 동작 실행 여부
action_last_time = {}         # 각 객체별 마지막 동작 시간
ACTION_COOLDOWN = 5.0         # 같은 객체에 대해 5초간 재실행 금지

# ============================================================
# 프레임 공유용 (object_detector ↔ lane_tracer)
# ============================================================

latest_frame = None

# ============================================================
# 통계 데이터 (세션 통계용)
# ============================================================

detection_counts = {name: 0 for name in KNOWN_OBJECTS}  # 각 객체별 총 감지 횟수
detector_active = False  # object_detector 스레드 활성 상태
