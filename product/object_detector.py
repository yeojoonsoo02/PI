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
from datetime import datetime
from PIL import Image

# ======================================
# 모델 및 파라미터 설정
# ======================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(BASE_DIR)  # AI_CAR 디렉토리

# 실제 모델 파일 경로 (AI_CAR/models/ 기준)
DETECTOR_PATH = os.path.join(PARENT_DIR, "models", "sign_traffic_detector.pt")  # 탐지 모델
CLASSIFIER_PATH = os.path.join(PARENT_DIR, "models", "sign_traffic_classifier.pt")  # 분류 모델

MIN_AREA = 5000        # 너무 작은 객체 제외 (다시 5000으로 상향)
NEAR_AREA = 20000      # 근접 판단 기준
CONF_THRESHOLD = 0.8   # 탐지 모델 신뢰도 임계값 (80%로 상향)
CLASSIFIER_CONF_THRESHOLD = 0.8  # 분류 모델 신뢰도 임계값 (80%)
COOLDOWN = 3.0         # 근접 이벤트 쿨다운

# 이미지 캡처 설정
CAPTURE_FOLDER = "/home/keonha/AI_CAR/captured_images"
MAX_CAPTURES_PER_OBJECT = 1  # 각 객체당 최대 캡처 횟수 (처음 인식 시 1장만)


def object_detect_loop():
    print("=" * 70)
    print(" YOLOv8 Object Detector (RGB 네이티브 처리)")
    print(" 🎯 2단계 인식 시스템: 탐지(Detector) → 분류(Classifier)")
    print("=" * 70)

    # 모델 파일 확인 (상세 디버깅)
    print(f"  [DEBUG] BASE_DIR: {BASE_DIR}")
    print(f"  [DEBUG] PARENT_DIR: {PARENT_DIR}")
    print(f"  [DEBUG] DETECTOR_PATH: {DETECTOR_PATH}")
    print(f"  [DEBUG] 모델 파일 존재 여부: {os.path.exists(DETECTOR_PATH)}")

    if not os.path.exists(DETECTOR_PATH):
        print(f"  [❌] 탐지 모델 파일이 없습니다: {DETECTOR_PATH}")
        print("  [INFO] 객체 인식 비활성화 - 라인 트레이싱만 동작")

        # shared_state에 detector 비활성 상태 표시
        with shared_state.lock:
            shared_state.detector_active = False
            # 모든 객체 상태를 False로 유지
            for obj_name in shared_state.KNOWN_OBJECTS:
                shared_state.object_state[obj_name] = False

        print("  [INFO] Object detector 스레드 종료")
        return

    # 모델 로드 (탐지 + 분류)
    print(f"  [INFO] 탐지 모델 로드 중: {DETECTOR_PATH}")
    detector = YOLO(DETECTOR_PATH)
    print(f"  [✓] 탐지 모델 로드 완료")

    # 분류 모델 로드 (있는 경우)
    classifier = None
    if os.path.exists(CLASSIFIER_PATH):
        print(f"  [INFO] 분류 모델 로드 중: {CLASSIFIER_PATH}")
        classifier = YOLO(CLASSIFIER_PATH)
        print(f"  [✓] 분류 모델 로드 완료 - 2단계 인식 활성화")
    else:
        print(f"  [⚠️] 분류 모델 없음 ({CLASSIFIER_PATH}) - 탐지 모델만 사용")

    # 모델 클래스 정보 출력
    if hasattr(detector, 'names'):
        print(f"  [INFO] 탐지 가능한 객체 클래스:")
        for idx, name in detector.names.items():
            print(f"        - {idx}: {name}")

    if classifier and hasattr(classifier, 'names'):
        print(f"  [INFO] 분류 가능한 세부 클래스:")
        for idx, name in classifier.names.items():
            # 클래스명에 따른 아이콘 추가
            icon = ""
            if "left" in name.lower() or "turn_left" in name:
                icon = "⬅️"
            elif "right" in name.lower() or "turn_right" in name:
                icon = "➡️"
            elif "straight" in name.lower() or "go_straight" in name:
                icon = "⬆️"
            elif "stop" in name.lower():
                icon = "🛑"
            elif "traffic" in name.lower():
                icon = "🚦"
            elif "horn" in name.lower():
                icon = "📢"
            elif "slow" in name.lower():
                icon = "⚠️"
            print(f"        - {idx}: {icon} {name}")

    # detector 활성 상태 표시
    with shared_state.lock:
        shared_state.detector_active = True

    # last_action_time은 아래에서 dict로 정의됨

    # 디버그용 카운터 및 타이머
    frame_count = 0
    detection_count = 0
    last_status_time = time.time()
    last_frame_time = 0
    no_frame_count = 0

    # 중복 실행 방지를 위한 딕셔너리
    last_action_time = {}  # 각 객체별 마지막 동작 시간
    # ACTION_COOLDOWN은 shared_state에서 가져옴 (5초)

    # 이미지 캡처용 카운터 및 폴더 생성
    capture_count = {}  # 각 객체별 캡처 횟수
    if not os.path.exists(CAPTURE_FOLDER):
        os.makedirs(CAPTURE_FOLDER)
        print(f"  [✓] 캡처 폴더 생성: {CAPTURE_FOLDER}")
    else:
        print(f"  [INFO] 캡처 폴더 존재: {CAPTURE_FOLDER}")

    print("\n" + "="*50)
    print("📸 [객체 인식 시작]")
    print(f"  • 신뢰도 기준: {int(CONF_THRESHOLD*100)}%")
    print(f"  • 최소 크기: {MIN_AREA}")
    print(f"  • 이미지 캡처: 활성화 (처음 인식 시 1장만)")
    print("="*50 + "\n")

    try:
        while True:
            # ===============================
            # 1️최신 프레임 획득 (RGB)
            # ===============================
            with shared_state.lock:
                frame_rgb = getattr(shared_state, "latest_frame", None)

            if frame_rgb is None:
                no_frame_count += 1
                if no_frame_count % 20 == 0:  # 1초마다 (0.05 * 20)
                    print(f"⚠️  [프레임 없음] {no_frame_count}번째 시도 중... (카메라 연결 확인)")
                time.sleep(0.05)
                continue

            # 프레임을 받았으면
            frame_count += 1
            no_frame_count = 0  # 리셋

            # ✅ BGR → RGB 변환 (모델 학습 색공간과 일치시키기)
            frame_rgb = cv2.cvtColor(frame_rgb, cv2.COLOR_BGR2RGB)

            # ROI: 오른쪽 절반 (640x480 기준 320~640)
            _, width = frame_rgb.shape[:2]
            roi_rgb = frame_rgb[:, width // 2:]

            # YOLO 탐지 시도
            detection_count += 1

            results = detector(roi_rgb, verbose=False)
            now = time.time()

            detected_label = None
            nearest_area = 0
            detected_conf = 0.0  # 신뢰도 변수 추가
            traffic_detected = False
            traffic_area = 0
            traffic_conf = 0.0  # 신호등 신뢰도 변수 추가
            objects_found = 0

            # ===============================
            #  탐지 결과 처리
            # ===============================
            if results and len(results) > 0 and hasattr(results[0], 'boxes') and results[0].boxes is not None:
                total_boxes = len(results[0].boxes) if results[0].boxes is not None else 0
                valid_objects = 0  # 조건을 통과한 객체 수

                for box in results[0].boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    area = (x2 - x1) * (y2 - y1)
                    conf = float(box.conf[0])
                    cls_id = int(box.cls[0])
                    cls_name = results[0].names[cls_id]

                    # ✅ test 버전 방식: 모든 객체를 분류 모델로 재확인
                    if classifier:
                        # ROI 추출하여 분류 모델 실행
                        crop = roi_rgb[y1:y2, x1:x2]
                        if crop.size > 0:
                            # test 버전과 동일한 방식: predict() 사용
                            cls_res = classifier.predict(crop, imgsz=224, verbose=False)
                            if cls_res and len(cls_res) > 0:
                                sub_id = int(cls_res[0].probs.top1)
                                sub_name = cls_res[0].names[sub_id]
                                sub_conf = float(cls_res[0].probs.top1conf)

                                # 분류 모델 신뢰도 체크 (80% 이상만)
                                if sub_conf >= CLASSIFIER_CONF_THRESHOLD:
                                    # 방향 표지판 아이콘
                                    direction_icon = ""
                                    if "left" in sub_name.lower() or "turn_left" in sub_name:
                                        direction_icon = "⬅️"
                                    elif "right" in sub_name.lower() or "turn_right" in sub_name:
                                        direction_icon = "➡️"
                                    elif "straight" in sub_name.lower() or "go_straight" in sub_name:
                                        direction_icon = "⬆️"

                                    # 분류 성공 로그
                                    if direction_icon:
                                        print(f"   🔄 [2단계 분류] {cls_name} → {sub_name} (신뢰도: {sub_conf:.1%})")
                                        print(f"      ✨ {direction_icon} **방향 표지판 확정!** {direction_icon}")

                                    cls_name = sub_name  # 분류된 이름으로 변경
                                    conf = (conf + sub_conf) / 2  # 평균 신뢰도

                    # 조건을 통과한 객체만 표시 (80% 이상, 5000 이상)
                    if conf >= CONF_THRESHOLD and area >= MIN_AREA:
                        valid_objects += 1

                        # 방향 표지판 아이콘 추가
                        icon = ""
                        if "left" in cls_name.lower() or "turn_left" in cls_name:
                            icon = "⬅️"
                        elif "right" in cls_name.lower() or "turn_right" in cls_name:
                            icon = "➡️"
                        elif "straight" in cls_name.lower() or "go_straight" in cls_name:
                            icon = "⬆️"
                        elif "stop" in cls_name.lower():
                            icon = "🛑"
                        elif "traffic" in cls_name.lower():
                            icon = "🚦"

                        objects_found += 1

                    if area < MIN_AREA or conf < CONF_THRESHOLD:
                        continue

                    # 검출된 클래스명 사용
                    detected_name = cls_name

                    # 🔍 디버그: 모델이 감지한 원본 클래스명 출력
                    print(f"\n🔍 [모델 감지] '{detected_name}' - 신뢰도: {conf:.0%} | 크기: {area:,}")

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
                        "go_straight": "go_straight",
                        # "sign" 클래스는 매핑하지 않음 (분류 모델이 필요)
                    }

                    sub_name = name_mapping.get(detected_name.lower(), None)

                    # KNOWN_OBJECTS에 없는 객체는 무시 (예: "sign", "direction", "arrow" 등)
                    if sub_name is None or sub_name not in shared_state.KNOWN_OBJECTS:
                        print(f"   ⚠️ [필터링됨] '{detected_name}' → name_mapping에 없음 (분류 모델 필요)")
                        continue
                    sub_conf = conf

                    # ✅ KNOWN_OBJECTS에 매핑된 객체만 로그 표시
                    print(f"\n🎯 [{sub_name}] 감지 - 신뢰도: {conf:.0%} | 크기: {area:,}")

                    # 신호등 처리
                    if sub_name.startswith("traffic"):
                        traffic_detected = True
                        traffic_area = area
                        traffic_conf = sub_conf  # 신호등 신뢰도 저장
                        continue

                    # 가장 큰 면적 객체 선택
                    if area > nearest_area:
                        nearest_area = area
                        detected_label = sub_name
                        detected_conf = sub_conf  # 신뢰도 저장

                    # 디버깅용 표시 (RGB 프레임 사용)
                    cv2.rectangle(roi_rgb, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(roi_rgb, f"{sub_name} ({conf:.2f})", (x1, y1 - 5),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

            # ===============================
            # shared_state 갱신 및 로깅
            # ===============================
            with shared_state.lock:
                # 기존 상태 백업 (변경 감지용)
                prev_detected = shared_state.object_detected
                prev_state = shared_state.object_state.copy()

                # 감지된 객체 목록 생성
                detected_objects = []
                if detected_label and detected_label in shared_state.KNOWN_OBJECTS:
                    detected_objects.append(detected_label)
                if traffic_detected:
                    detected_objects.append("traffic")

                # 모든 객체에 대해 연속 감지 프레임 업데이트
                for obj_name in shared_state.KNOWN_OBJECTS:
                    if obj_name in detected_objects:
                        # 감지된 객체: 프레임 카운터 증가
                        shared_state.detection_frames[obj_name] += 1
                        shared_state.object_state[obj_name] = True
                    else:
                        # 미감지된 객체: 프레임 카운터 리셋
                        shared_state.detection_frames[obj_name] = 0
                        shared_state.object_state[obj_name] = False

                # 감지된 객체의 상세 정보 업데이트
                if detected_label and detected_label in shared_state.KNOWN_OBJECTS:
                    shared_state.object_area[detected_label] = nearest_area
                    shared_state.object_last_seen[detected_label] = now
                    shared_state.confidence[detected_label] = detected_conf

                # traffic 신호등 상세 정보 업데이트
                if traffic_detected:
                    shared_state.object_area["traffic"] = traffic_area
                    shared_state.object_last_seen["traffic"] = now
                    shared_state.confidence["traffic"] = traffic_conf

                # 새로운 상태 업데이트
                shared_state.object_detected = detected_label
                shared_state.object_distance = nearest_area

                # 새로운 객체 감지 시 로그 (더 강조된 버전)
                if detected_label and detected_label != prev_detected:
                    timestamp = time.strftime("%H:%M:%S")

                    # 중복 실행 체크
                    can_execute = True
                    if detected_label in shared_state.action_last_time:
                        time_since_last = now - shared_state.action_last_time[detected_label]
                        if time_since_last < shared_state.ACTION_COOLDOWN:
                            can_execute = False

                    print(f"\n{'🔥'*25}")
                    print(f"🎯🎯🎯 [{detected_label}] 감지! 🎯🎯🎯")
                    print(f"{'🔥'*25}")
                    print(f"  ⏰ 시간: {timestamp}")
                    print(f"  📌 객체 타입: {detected_label}")
                    print(f"  📏 크기: {nearest_area:,}")
                    print(f"  🎭 신뢰도: {sub_conf:.2%}")

                    # 동작 가능 여부 표시
                    if can_execute:
                        print(f"  ✅ 동작 실행 가능!")
                    else:
                        remaining = shared_state.ACTION_COOLDOWN - (now - shared_state.action_last_time[detected_label])
                        print(f"  ⏳ 쿨다운 중... ({remaining:.1f}초 남음)")

                    # 객체별 구체적 설명 (방향 표지판 강조)
                    actions = {
                        "stop": "🛑 2초 정지",
                        "traffic": "🚦 3초 대기 → 우회전",
                        "horn": "📢 경적 1초",
                        "slow": "⚠️ 속도 25%로 감소",
                        "go_straight": "⬆️⬆️⬆️ 직진 표지판 → 교차로에서 직진",
                        "straight": "⬆️⬆️⬆️ 직진 표지판 → 교차로에서 직진",
                        "turn_left": "⬅️⬅️⬅️ 좌회전 표지판 → 교차로에서 좌회전",
                        "left": "⬅️⬅️⬅️ 좌회전 표지판 → 교차로에서 좌회전",
                        "turn_right": "➡️➡️➡️ 우회전 표지판 → 교차로에서 우회전",
                        "right": "➡️➡️➡️ 우회전 표지판 → 교차로에서 우회전"
                    }

                    # 방향 표지판이면 특별 강조
                    if detected_label in ["go_straight", "straight", "turn_left", "left", "turn_right", "right"]:
                        # 방향 표지판 아이콘 결정
                        dir_icon = ""
                        if detected_label in ["turn_left", "left"]:
                            dir_icon = "⬅️⬅️⬅️"
                            direction = "좌회전"
                        elif detected_label in ["turn_right", "right"]:
                            dir_icon = "➡️➡️➡️"
                            direction = "우회전"
                        else:  # go_straight, straight
                            dir_icon = "⬆️⬆️⬆️"
                            direction = "직진"

                        print(f"\n  🚗💨 [방향 표지판 감지!]")
                        print(f"  🎯 {dir_icon} {direction.upper()} 표지판 {dir_icon} 🎯")
                        print(f"  🎬 동작: {actions.get(detected_label, '알 수 없음')}")
                        print(f"  💾 교차로에서 자동 실행 예정")
                        print(f"  🔄 분류 모델로 확정된 방향입니다!\n")
                    elif detected_label in actions:
                        print(f"  🎬 동작: {actions[detected_label]}")

                    print(f"{'='*50}\n")

                    # 이미지 캡처 (새로운 객체 감지 시)
                    if detected_label not in capture_count:
                        capture_count[detected_label] = 0

                    if capture_count[detected_label] < MAX_CAPTURES_PER_OBJECT:
                        try:
                            # 캡처할 이미지 준비 (ROI 영역, RGB)
                            capture_img = roi_rgb.copy()

                            # 타임스탬프 생성
                            capture_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            capture_num = capture_count[detected_label] + 1

                            # 파일명 생성
                            filename = f"{detected_label}_{capture_timestamp}_{capture_num}.jpg"
                            filepath = os.path.join(CAPTURE_FOLDER, filename)

                            # 이미지 저장 (PIL 사용 - RGB 네이티브 저장)
                            pil_img = Image.fromarray(capture_img)
                            pil_img.save(filepath, quality=95)
                            capture_count[detected_label] += 1

                            print(f"  📷 [이미지 캡처] {filename}")
                            print(f"      └─ 저장 위치: {filepath}")
                            print(f"      └─ 처음 인식 시 자동 저장 완료")
                        except Exception as e:
                            print(f"  ❌ 이미지 캡처 실패: {e}")

                if traffic_detected:
                    shared_state.traffic_light_area = traffic_area
                    shared_state.traffic_light_last_ts = now
                    shared_state.right_turn_done = False

                    # 신호등 감지 로그
                    if not prev_state.get("traffic", False):  # 새로 감지된 경우만
                        timestamp = time.strftime("%H:%M:%S")
                        print(f"🚦 [신호등 감지] {timestamp} | 크기: {traffic_area}")

            # ===============================
            #  이벤트 트리거 처리 (근접 이벤트용)
            # ===============================
            # 이미 위에서 중복 실행 방지 처리됨
            # 근접 이벤트만 체크
            if detected_label and nearest_area > NEAR_AREA:
                with shared_state.lock:
                    # 이미 실행 중이 아닌 경우에만 트리거
                    if detected_label not in shared_state.action_last_time:
                        shared_state.last_trigger = detected_label
                        print(f"[TRIGGER] {detected_label} 근접 이벤트 (area={nearest_area})")

            # 디버그 출력 제거 (너무 많은 로그 방지)

            # ===============================
            # 📊 주기적 상태 리포트 (30초마다)
            # ===============================
            if now - last_status_time >= 30.0:
                print("\n" + "="*60)
                print(f"📊 [상태 리포트] {time.strftime('%H:%M:%S')}")
                print(f"  • 총 프레임 수신: {frame_count}개")
                print(f"  • 총 탐지 시도: {detection_count}회")
                print(f"  • 프레임 처리율: {frame_count/detection_count:.1%}" if detection_count > 0 else "N/A")
                print(f"  • 현재 프레임 크기: {frame_rgb.shape if frame_rgb is not None else 'N/A'}")
                print(f"  • ROI 크기: {roi_rgb.shape}")
                print(f"  • 마지막 탐지 객체: {detected_label if detected_label else '없음'}")

                # 활성 객체 상태
                with shared_state.lock:
                    active_objects = [k for k, v in shared_state.object_state.items() if v]
                    if active_objects:
                        print(f"  • 활성 객체: {', '.join(active_objects)}")
                    else:
                        print(f"  • 활성 객체: 없음")

                # 캡처 상태
                if capture_count:
                    total_captures = sum(capture_count.values())
                    capture_summary = [f"{k}:{v}" for k, v in capture_count.items() if v > 0]
                    print(f"  • 📷 캡처된 이미지: 총 {total_captures}장")
                    if capture_summary:
                        print(f"      └─ {', '.join(capture_summary)}")
                else:
                    print(f"  • 📷 캡처된 이미지: 없음")

                print(f"  • YOLO 모델 상태: {'정상' if detector else '오류'}")
                print("="*60 + "\n")
                last_status_time = now

            # 탐지 실패 로그 제거 (너무 많은 로그 방지)

            time.sleep(0.2)

    except KeyboardInterrupt:
        print("\n[INFO] Object detector stopped by user.")
    finally:
        cv2.destroyAllWindows()
        print(" Detector cleanup complete")
