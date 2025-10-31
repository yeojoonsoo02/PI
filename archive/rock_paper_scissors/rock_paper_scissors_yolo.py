"""
YOLO 기반 가위바위보 인식 시스템
맥북 웹캠을 사용하여 실시간으로 주먹(Rock), 가위(Scissors), 보(Paper)를 인식합니다.
"""

import cv2
import numpy as np
from ultralytics import YOLO
import time
from collections import Counter


class RockPaperScissorsDetector:
    """YOLO 기반 가위바위보 감지기"""

    def __init__(self, model_path='yolov8n.pt', confidence_threshold=0.5):
        """
        초기화

        Args:
            model_path: YOLO 모델 경로 (기본값: YOLOv8 nano)
            confidence_threshold: 감지 신뢰도 임계값
        """
        print("[INFO] YOLO 모델 로딩 중...")
        self.model = YOLO(model_path)
        self.confidence_threshold = confidence_threshold

        # 가위바위보 클래스 (커스텀 모델 학습 시 사용)
        self.classes = {
            0: 'Rock',      # 주먹
            1: 'Paper',     # 보
            2: 'Scissors'   # 가위
        }

        # 결과 저장용 (안정성 향상)
        self.recent_predictions = []
        self.max_history = 5

        print("[INFO] 모델 로딩 완료!")

    def detect_hand(self, frame):
        """
        손 영역 감지 (YOLOv8 사전 학습 모델 사용)

        Args:
            frame: 입력 프레임

        Returns:
            hands: 감지된 손 영역 리스트
        """
        results = self.model(frame, verbose=False)
        hands = []

        for result in results:
            boxes = result.boxes
            for box in boxes:
                # 사람(person) 클래스 필터링 (클래스 0)
                # 실제로는 손 감지 모델 사용 권장
                if int(box.cls[0]) == 0:  # person class
                    confidence = float(box.conf[0])
                    if confidence > self.confidence_threshold:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        hands.append({
                            'bbox': (x1, y1, x2, y2),
                            'confidence': confidence
                        })

        return hands

    def classify_gesture(self, hand_roi):
        """
        손 영역에서 가위바위보 분류

        이 함수는 간단한 휴리스틱 방법을 사용합니다.
        실제 프로덕션에서는 커스텀 YOLO 모델이나 분류 CNN을 사용해야 합니다.

        Args:
            hand_roi: 손 영역 이미지

        Returns:
            gesture: 감지된 제스처 ('Rock', 'Paper', 'Scissors')
        """
        # 간단한 색상 기반 분류 (예시)
        # 실제로는 학습된 모델 사용 권장
        gray = cv2.cvtColor(hand_roi, cv2.COLOR_BGR2GRAY)

        # 엣지 감지
        edges = cv2.Canny(gray, 50, 150)
        edge_count = np.sum(edges > 0)

        # 간단한 휴리스틱
        h, w = hand_roi.shape[:2]
        edge_density = edge_count / (h * w)

        if edge_density < 0.1:
            return 'Rock'  # 주먹 (엣지 적음)
        elif edge_density > 0.2:
            return 'Scissors'  # 가위 (엣지 많음)
        else:
            return 'Paper'  # 보 (중간)

    def get_stable_prediction(self, current_prediction):
        """
        예측 결과 안정화 (최근 N개 결과의 다수결)

        Args:
            current_prediction: 현재 예측 결과

        Returns:
            stable_prediction: 안정화된 예측 결과
        """
        self.recent_predictions.append(current_prediction)
        if len(self.recent_predictions) > self.max_history:
            self.recent_predictions.pop(0)

        if len(self.recent_predictions) >= 3:
            counter = Counter(self.recent_predictions)
            return counter.most_common(1)[0][0]

        return current_prediction

    def draw_results(self, frame, hands, gesture=None):
        """
        결과 시각화

        Args:
            frame: 원본 프레임
            hands: 감지된 손 리스트
            gesture: 분류된 제스처

        Returns:
            frame: 시각화된 프레임
        """
        for hand in hands:
            x1, y1, x2, y2 = hand['bbox']
            confidence = hand['confidence']

            # 바운딩 박스 그리기
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

            # 신뢰도 표시
            label = f"Hand: {confidence:.2f}"
            cv2.putText(frame, label, (x1, y1 - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # 제스처 결과 표시
        if gesture:
            # 한글 변환
            gesture_kr = {
                'Rock': '주먹 ✊',
                'Paper': '보 ✋',
                'Scissors': '가위 ✌️'
            }

            display_text = gesture_kr.get(gesture, gesture)

            # 큰 글씨로 화면 상단에 표시
            cv2.putText(frame, display_text, (50, 100),
                       cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 255, 255), 4)

        return frame


def main():
    """메인 함수"""
    print("=" * 60)
    print("YOLO 기반 가위바위보 인식 시스템")
    print("=" * 60)
    print("\n[사용법]")
    print("- 웹캠 앞에서 주먹, 가위, 보를 보여주세요")
    print("- 'q' 또는 ESC: 종료")
    print("- 'c': 화면 캡처")
    print("- 's': 통계 초기화")
    print("\n[주의사항]")
    print("- 이 버전은 YOLOv8 사전 학습 모델을 사용합니다")
    print("- 더 정확한 인식을 위해서는 가위바위보 커스텀 데이터셋으로")
    print("  모델을 학습시키는 것을 권장합니다")
    print("=" * 60)

    # 감지기 초기화
    detector = RockPaperScissorsDetector()

    # 웹캠 열기
    print("\n[INFO] 웹캠 열기...")
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("[ERROR] 웹캠을 열 수 없습니다!")
        return

    # 웹캠 설정
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    print("[INFO] 웹캠 준비 완료!")
    print("[INFO] 프로그램 실행 중... (종료: 'q' 또는 ESC)\n")

    # 통계
    stats = Counter()
    frame_count = 0
    fps_start_time = time.time()
    fps = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("[ERROR] 프레임 읽기 실패!")
                break

            # 좌우 반전 (거울 모드)
            frame = cv2.flip(frame, 1)

            # 손 감지
            hands = detector.detect_hand(frame)

            # 제스처 분류
            gesture = None
            if hands:
                # 가장 큰 손 영역 선택
                largest_hand = max(hands, key=lambda h:
                                 (h['bbox'][2] - h['bbox'][0]) *
                                 (h['bbox'][3] - h['bbox'][1]))

                x1, y1, x2, y2 = largest_hand['bbox']
                hand_roi = frame[y1:y2, x1:x2]

                if hand_roi.size > 0:
                    gesture = detector.classify_gesture(hand_roi)
                    gesture = detector.get_stable_prediction(gesture)
                    stats[gesture] += 1

            # 결과 시각화
            frame = detector.draw_results(frame, hands, gesture)

            # FPS 계산
            frame_count += 1
            if frame_count >= 30:
                fps = 30 / (time.time() - fps_start_time)
                fps_start_time = time.time()
                frame_count = 0

            # 정보 표시
            info_text = f"FPS: {fps:.1f}"
            cv2.putText(frame, info_text, (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            # 통계 표시
            y_offset = 60
            for ges, count in stats.most_common(3):
                stat_text = f"{ges}: {count}"
                cv2.putText(frame, stat_text, (10, y_offset),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                y_offset += 25

            # 화면 표시
            cv2.imshow('Rock Paper Scissors - YOLO', frame)

            # 키 입력 처리
            key = cv2.waitKey(1) & 0xFF

            if key in (ord('q'), 27):  # 'q' 또는 ESC
                print("\n[INFO] 프로그램 종료")
                break
            elif key == ord('c'):  # 화면 캡처
                filename = f"capture_{int(time.time())}.jpg"
                cv2.imwrite(filename, frame)
                print(f"[INFO] 화면 캡처: {filename}")
            elif key == ord('s'):  # 통계 초기화
                stats.clear()
                print("[INFO] 통계 초기화됨")

    except KeyboardInterrupt:
        print("\n[INFO] 사용자에 의해 중단됨")

    finally:
        # 정리
        cap.release()
        cv2.destroyAllWindows()

        # 최종 통계 출력
        print("\n" + "=" * 60)
        print("최종 통계")
        print("=" * 60)
        for gesture, count in stats.most_common():
            print(f"{gesture}: {count}회")
        print("=" * 60)


if __name__ == "__main__":
    main()
