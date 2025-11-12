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
def find_model_file(filename):
    """모델 파일을 여러 위치에서 찾기"""
    possible_paths = [
        os.path.join(BASE_DIR, "models", filename),
        os.path.join(BASE_DIR, "..", filename),  # 상위 디렉토리
        os.path.join(BASE_DIR, filename),  # 현재 디렉토리
        os.path.join("/home/keonha/AI_CAR", filename),  # 절대 경로
        os.path.join("/home/keonha/AI_CAR/test", filename),
    ]

    for path in possible_paths:
        if os.path.exists(path):
            print(f"  [✓] 모델 파일 발견: {path}")
            return path

    # best.pt 파일도 시도
    if "detector" in filename:
        for path in possible_paths:
            best_path = path.replace(filename, "best.pt")
            if os.path.exists(best_path):
                print(f"  [✓] 대체 모델 파일 발견: {best_path}")
                return best_path

    print(f"  [⚠️] 모델 파일을 찾을 수 없음: {filename}")
    return None

DETECTOR_PATH = find_model_file("sign_traffic_detector.pt")
CLASSIFIER_PATH = find_model_file("sign_traffic_classifier.pt")

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
        print("  [❌] Detector 모델 파일이 없습니다!")
        print("  [INFO] best.pt 파일을 다음 위치 중 하나에 배치하세요:")
        print("        - /home/keonha/AI_CAR/best.pt")
        print("        - /home/keonha/AI_CAR/test/best.pt")
        print("  [INFO] 객체 인식 비활성화 - 라인 트레이싱만 동작")
        while True:
            time.sleep(1)  # 스레드 유지 (크래시 방지)
        return

    # Classifier는 옵션
    use_classifier = CLASSIFIER_PATH is not None

    # 모델 로드
    detector = YOLO(DETECTOR_PATH)
    classifier = YOLO(CLASSIFIER_PATH) if use_classifier else None

    print(f"  [✓] Detector 모델 로드 완료")
    if use_classifier:
        print(f"  [✓] Classifier 모델 로드 완료")
    else:
        print(f"  [⚠️] Classifier 모델 없음 - 기본 분류만 사용")

    last_action_time = 0
    last_label = None

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
            height, width = frame_rgb.shape[:2]
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
            for box in results[0].boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                area = (x2 - x1) * (y2 - y1)
                conf = float(box.conf[0])
                cls_id = int(box.cls[0])
                cls_name = results[0].names[cls_id]

                if area < MIN_AREA or conf < CONF_THRESHOLD:
                    continue

                # Classifier 사용 여부에 따라 분류
                if use_classifier and classifier:
                    # crop 영역 분류 (RGB 기준)
                    crop_rgb = roi_rgb[y1:y2, x1:x2]
                    cls_res = classifier.predict(crop_rgb, imgsz=224, verbose=False)
                    sub_id = int(cls_res[0].probs.top1)
                    sub_name = cls_res[0].names[sub_id]
                    sub_conf = float(cls_res[0].probs.top1conf)

                    if sub_conf < 0.8:
                        continue
                else:
                    # Classifier 없이 기본 라벨 사용
                    sub_name = cls_name if 'cls_name' in locals() else "object"
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
                    print(f"  🎭 신뢰도: {conf:.2%}")

                    # 표지판 종류별 메시지
                    if detected_label in ["go_straight", "turn_left", "turn_right"]:
                        print(f"  💾 방향 표지판 → 큐에 저장됨")
                    elif detected_label == "stop":
                        print(f"  🛑 정지 표지판 → 즉시 정지 예정")
                    elif detected_label == "slow":
                        print(f"  ⚠️ 서행 표지판 → 속도 감소 예정")
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
                last_label = detected_label
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
