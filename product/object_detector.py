"""
object_detector.py (수정 버전)
-------------------------------
YOLOv8 탐지 + 분류 + 거리 기반 근접 이벤트
"""

import time
import cv2
import numpy as np
from ultralytics import YOLO
import shared_state
import os

# ======================================
# 모델 및 파라미터 설정
# ======================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 모델 파일 경로 - 여러 위치 확인
def find_model_file():
    """best.pt 모델 파일을 여러 위치에서 찾기"""
    possible_paths = [
        # Raspberry Pi 경로들
        "/home/keonha/AI_CAR/product/best.pt",
        "/home/keonha/AI_CAR/best.pt",
        "/home/keonha/best.pt",
        os.path.join(BASE_DIR, "best.pt"),  # 현재 디렉토리
        os.path.join(BASE_DIR, "..", "best.pt"),  # 상위 디렉토리
        os.path.join(BASE_DIR, "models", "best.pt"),
        "/home/pi/best.pt",  # 기본 pi 사용자 경로
        "/home/pi/AI_CAR/best.pt",
    ]

    print("  [INFO] YOLO 모델 파일 검색 중...")
    for path in possible_paths:
        if os.path.exists(path):
            print(f"  [✓] 모델 파일 발견: {path}")
            return path

    # 현재 디렉토리 내용 확인 (디버깅용)
    print(f"  [DEBUG] 현재 디렉토리: {BASE_DIR}")
    print(f"  [DEBUG] 상위 디렉토리: {os.path.dirname(BASE_DIR)}")

    # 상위 디렉토리에서 .pt 파일 찾기
    parent_dir = os.path.dirname(BASE_DIR)
    if os.path.exists(parent_dir):
        pt_files = [f for f in os.listdir(parent_dir) if f.endswith('.pt')]
        if pt_files:
            print(f"  [DEBUG] 상위 디렉토리의 .pt 파일들: {pt_files}")
            for pt_file in pt_files:
                full_path = os.path.join(parent_dir, pt_file)
                print(f"  [✓] 대체 모델 파일 발견: {full_path}")
                return full_path

    print(f"  [⚠️] best.pt 모델 파일을 찾을 수 없음")
    return None

# 단일 모델만 사용 (best.pt)
DETECTOR_PATH = find_model_file()
CLASSIFIER_PATH = None  # Classifier는 사용하지 않음

MIN_AREA = 5000        # 너무 작은 객체 제외
NEAR_AREA = 20000      # 근접 판단 기준
CONF_THRESHOLD = 0.7   # 신뢰도 임계값
COOLDOWN = 3.0         # 근접 이벤트 쿨다운


def object_detect_loop():
    print("=" * 70)
    print(" YOLOv8 Object Detector (BGR→RGB 변환 적용)")
    print("=" * 70)

    # 모델 파일 확인
    if not DETECTOR_PATH:
        print("  [❌] YOLO 모델 파일 (best.pt)이 없습니다!")
        print("  [INFO] best.pt 파일을 다음 위치 중 하나에 배치하세요:")
        print("        - /home/keonha/AI_CAR/product/best.pt")
        print("        - /home/keonha/AI_CAR/best.pt")
        print("        - /home/pi/AI_CAR/best.pt")
        print("  [INFO] 객체 인식 비활성화 - 라인 트레이싱만 동작")

        # shared_state에 detector 비활성 상태 표시
        with shared_state.lock:
            shared_state.detector_active = False
            # 모든 객체 상태를 False로 유지
            for obj_name in shared_state.KNOWN_OBJECTS:
                shared_state.object_state[obj_name] = False

        print("  [INFO] Object detector 스레드 종료")
        return

    # 모델 로드 (단일 모델만 사용)
    print(f"  [INFO] 모델 로드 중: {DETECTOR_PATH}")
    detector = YOLO(DETECTOR_PATH)
    print(f"  [✓] YOLO 모델 로드 완료")

    # 모델 클래스 정보 출력
    if hasattr(detector, 'names'):
        print(f"  [INFO] 감지 가능한 객체 클래스:")
        for idx, name in detector.names.items():
            print(f"        - {idx}: {name}")

    # detector 활성 상태 표시
    with shared_state.lock:
        shared_state.detector_active = True

    last_action_time = 0

    try:
        while True:
            # ===============================
            # 1️최신 프레임 획득 (BGR)
            # ===============================
            with shared_state.lock:
                frame_bgr = getattr(shared_state, "latest_frame", None)

            if frame_bgr is None:
                time.sleep(0.05)
                continue

            # YOLO 입력용 RGB로 변환
            frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

            # ROI: 오른쪽 절반 (640x480 기준 320~640)
            _, width = frame_rgb.shape[:2]
            roi_rgb = frame_rgb[:, width // 2:]
            roi_bgr = frame_bgr[:, width // 2:]  # 디버깅용 시각화

            results = detector(roi_rgb, verbose=False)
            now = time.time()

            detected_label = None
            nearest_area = 0
            traffic_detected = False
            traffic_area = 0

            # ===============================
            #  탐지 결과 처리
            # ===============================
            if results and len(results) > 0 and hasattr(results[0], 'boxes') and results[0].boxes is not None:
                for box in results[0].boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    area = (x2 - x1) * (y2 - y1)
                    conf = float(box.conf[0])
                    cls_id = int(box.cls[0])
                    cls_name = results[0].names[cls_id]

                    if area < MIN_AREA or conf < CONF_THRESHOLD:
                        continue

                    # 검출된 클래스명 사용
                    detected_name = cls_name

                    # 클래스명 매핑 (모델의 클래스명을 shared_state의 KNOWN_OBJECTS에 맞게 변환)
                    # 예: "left" -> "turn_left", "right" -> "turn_right", "straight" -> "go_straight"
                    name_mapping = {
                        "left": "turn_left",
                        "right": "turn_right",
                        "straight": "go_straight",
                        "stop": "stop",
                        "slow": "slow",
                        "horn": "horn",
                        "traffic": "traffic",
                        "turn_left": "turn_left",
                        "turn_right": "turn_right",
                        "go_straight": "go_straight"
                    }

                    sub_name = name_mapping.get(detected_name.lower(), detected_name)
                    sub_conf = conf

                    # 신호등 처리
                    if sub_name.startswith("traffic"):
                        traffic_detected = True
                        traffic_area = area
                        continue

                    # 가장 큰 면적 객체 선택
                    if area > nearest_area:
                        nearest_area = area
                        detected_label = sub_name

                    # 디버깅용 표시
                    cv2.rectangle(roi_bgr, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(roi_bgr, f"{sub_name} ({conf:.2f})", (x1, y1 - 5),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

            # ===============================
            # shared_state 갱신 및 로깅
            # ===============================
            with shared_state.lock:
                # 기존 상태 백업 (변경 감지용)
                prev_detected = shared_state.object_detected
                prev_state = shared_state.object_state.copy()

                # 모든 object_state를 False로 초기화
                for obj_name in shared_state.KNOWN_OBJECTS:
                    shared_state.object_state[obj_name] = False

                # 감지된 객체의 object_state를 True로 설정
                if detected_label:
                    if detected_label in shared_state.KNOWN_OBJECTS:
                        shared_state.object_state[detected_label] = True
                        shared_state.object_area[detected_label] = nearest_area
                        shared_state.object_last_seen[detected_label] = now

                # traffic 신호등도 상태 업데이트
                if traffic_detected:
                    shared_state.object_state["traffic"] = True
                    shared_state.object_area["traffic"] = traffic_area
                    shared_state.object_last_seen["traffic"] = now

                # 새로운 상태 업데이트
                shared_state.object_detected = detected_label
                shared_state.object_distance = nearest_area

                # 새로운 객체 감지 시 로그
                if detected_label and detected_label != prev_detected:
                    timestamp = time.strftime("%H:%M:%S")
                    print(f"\n{'='*50}")
                    print(f"🎯 [객체 감지] {timestamp}")
                    print(f"  📌 객체: {detected_label}")
                    print(f"  📏 크기: {nearest_area}")
                    print(f"  🎭 신뢰도: {sub_conf:.2%}")  # sub_conf 사용

                    # 표지판 종류별 메시지
                    if detected_label in ["go_straight", "turn_left", "turn_right"]:
                        print(f"  💾 방향 표지판 → 큐에 저장 예정")
                        print(f"  📝 lane_tracer가 교차로에서 실행할 예정")
                    elif detected_label == "stop":
                        print(f"  🛑 정지 표지판 → 큐에 저장 예정")
                        print(f"  📝 lane_tracer가 교차로에서 처리할 예정")
                    elif detected_label == "slow":
                        print(f"  ⚠️ 서행 표지판 → 속도 감소 신호")
                    print(f"{'='*50}\n")

                if traffic_detected:
                    shared_state.traffic_light_area = traffic_area
                    shared_state.traffic_light_last_ts = now
                    shared_state.right_turn_done = False

                    # 신호등 감지 로그
                    if not prev_state.get("traffic", False):  # 새로 감지된 경우만
                        timestamp = time.strftime("%H:%M:%S")
                        print(f"🚦 [신호등 감지] {timestamp} | 크기: {traffic_area}")

            # ===============================
            #  이벤트 트리거 처리
            # ===============================
            if (
                detected_label
                and nearest_area > NEAR_AREA
                and (now - last_action_time > COOLDOWN)
            ):
                print(f"[DETECTED] {detected_label} (area={nearest_area})")
                with shared_state.lock:
                    shared_state.last_trigger = detected_label
                last_action_time = now

            # ===============================
            #  디버그 출력 (프레임별)
            # ===============================
            if detected_label:
                print(f" → {detected_label:12s} | area={nearest_area:6.0f}")

            # VNC 환경에서 미리보기 가능
            # cv2.imshow("YOLO Detection ROI (BGR view)", roi_bgr)
            # if cv2.waitKey(1) & 0xFF in (27, ord('q')):
            #     print("[INFO] Exit requested by user.")
            #     break

            time.sleep(0.2)

    except KeyboardInterrupt:
        print("\n[INFO] Object detector stopped by user.")
    finally:
        cv2.destroyAllWindows()
        print(" Detector cleanup complete")
