"""
고급 가위바위보 인식 시스템
MediaPipe Hands + 커스텀 분류 로직을 사용한 정확한 제스처 인식
"""

import cv2
import numpy as np
import mediapipe as mp
import time
from collections import Counter


class HandGestureRecognizer:
    """MediaPipe 기반 손 제스처 인식기"""

    def __init__(self, min_detection_confidence=0.7, min_tracking_confidence=0.7):
        """
        초기화

        Args:
            min_detection_confidence: 손 감지 최소 신뢰도
            min_tracking_confidence: 손 추적 최소 신뢰도
        """
        print("[INFO] MediaPipe Hands 초기화 중...")

        # MediaPipe Hands 초기화
        self.mp_hands = mp.solutions.hands
        self.mp_draw = mp.solutions.drawing_utils
        self.mp_draw_styles = mp.solutions.drawing_styles

        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )

        # 손가락 끝 인덱스 (MediaPipe 랜드마크)
        self.finger_tips = [4, 8, 12, 16, 20]  # 엄지, 검지, 중지, 약지, 소지
        self.finger_pips = [2, 6, 10, 14, 18]  # 각 손가락의 두 번째 관절

        # 예측 안정화
        self.recent_gestures = []
        self.max_history = 7

        print("[INFO] 초기화 완료!")

    def count_fingers(self, hand_landmarks, handedness):
        """
        펼쳐진 손가락 개수 세기

        Args:
            hand_landmarks: 손 랜드마크
            handedness: 손잡이 정보 (Left/Right)

        Returns:
            finger_count: 펼쳐진 손가락 개수
            finger_status: 각 손가락 상태 리스트
        """
        finger_status = []

        # 엄지 판단 (좌우 손에 따라 다름)
        is_right_hand = handedness.classification[0].label == 'Right'

        # 엄지
        thumb_tip = hand_landmarks.landmark[self.finger_tips[0]]
        thumb_pip = hand_landmarks.landmark[self.finger_pips[0]]

        if is_right_hand:
            thumb_up = thumb_tip.x < thumb_pip.x
        else:
            thumb_up = thumb_tip.x > thumb_pip.x

        finger_status.append(1 if thumb_up else 0)

        # 나머지 손가락 (검지, 중지, 약지, 소지)
        for i in range(1, 5):
            tip = hand_landmarks.landmark[self.finger_tips[i]]
            pip = hand_landmarks.landmark[self.finger_pips[i]]

            # 손가락 끝이 관절보다 위에 있으면 펼쳐진 것
            finger_up = tip.y < pip.y
            finger_status.append(1 if finger_up else 0)

        finger_count = sum(finger_status)

        return finger_count, finger_status

    def classify_gesture(self, hand_landmarks, handedness):
        """
        손 제스처 분류

        Args:
            hand_landmarks: 손 랜드마크
            handedness: 손잡이 정보

        Returns:
            gesture: 인식된 제스처 ('Rock', 'Paper', 'Scissors')
        """
        finger_count, finger_status = self.count_fingers(hand_landmarks, handedness)

        # 주먹 (Rock): 손가락 0~1개
        if finger_count <= 1:
            return 'Rock'

        # 보 (Paper): 손가락 5개 모두 펼침
        elif finger_count == 5:
            return 'Paper'

        # 가위 (Scissors): 손가락 2개 (검지, 중지)
        elif finger_count == 2:
            # 검지와 중지만 펼쳐져 있는지 확인
            if finger_status[1] == 1 and finger_status[2] == 1:
                return 'Scissors'

        # 가위의 변형 (검지, 중지, 약지 등)
        elif finger_count == 3:
            if finger_status[1] == 1 and finger_status[2] == 1:
                return 'Scissors'

        # 애매한 경우 이전 제스처 유지
        return None

    def get_stable_gesture(self, current_gesture):
        """
        제스처 안정화 (최근 결과의 다수결)

        Args:
            current_gesture: 현재 제스처

        Returns:
            stable_gesture: 안정화된 제스처
        """
        if current_gesture is None:
            return None

        self.recent_gestures.append(current_gesture)
        if len(self.recent_gestures) > self.max_history:
            self.recent_gestures.pop(0)

        if len(self.recent_gestures) >= 4:
            counter = Counter(self.recent_gestures)
            most_common = counter.most_common(1)[0]

            # 과반수 이상이면 안정화된 것으로 판단
            if most_common[1] >= len(self.recent_gestures) * 0.5:
                return most_common[0]

        return current_gesture

    def draw_hand_landmarks(self, image, hand_landmarks):
        """
        손 랜드마크 그리기

        Args:
            image: 입력 이미지
            hand_landmarks: 손 랜드마크

        Returns:
            image: 랜드마크가 그려진 이미지
        """
        self.mp_draw.draw_landmarks(
            image,
            hand_landmarks,
            self.mp_hands.HAND_CONNECTIONS,
            self.mp_draw_styles.get_default_hand_landmarks_style(),
            self.mp_draw_styles.get_default_hand_connections_style()
        )
        return image

    def process_frame(self, frame):
        """
        프레임 처리 및 제스처 인식

        Args:
            frame: 입력 프레임

        Returns:
            frame: 처리된 프레임
            gesture: 인식된 제스처
            hand_count: 감지된 손 개수
        """
        # RGB 변환
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # 손 감지
        results = self.hands.process(frame_rgb)

        gesture = None
        hand_count = 0

        if results.multi_hand_landmarks:
            hand_count = len(results.multi_hand_landmarks)

            for hand_landmarks, handedness in zip(
                results.multi_hand_landmarks,
                results.multi_handedness
            ):
                # 랜드마크 그리기
                frame = self.draw_hand_landmarks(frame, hand_landmarks)

                # 제스처 분류
                current_gesture = self.classify_gesture(hand_landmarks, handedness)
                if current_gesture:
                    gesture = current_gesture

            # 제스처 안정화
            gesture = self.get_stable_gesture(gesture)

        return frame, gesture, hand_count

    def release(self):
        """리소스 해제"""
        self.hands.close()


def draw_info_panel(frame, gesture, stats, fps, hand_count):
    """
    정보 패널 그리기

    Args:
        frame: 입력 프레임
        gesture: 현재 제스처
        stats: 통계
        fps: FPS
        hand_count: 손 개수

    Returns:
        frame: 정보가 표시된 프레임
    """
    h, w = frame.shape[:2]

    # 반투명 패널
    overlay = frame.copy()
    cv2.rectangle(overlay, (10, 10), (300, 200), (0, 0, 0), -1)
    frame = cv2.addWeighted(overlay, 0.5, frame, 0.5, 0)

    # FPS 표시
    cv2.putText(frame, f"FPS: {fps:.1f}", (20, 40),
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    # 손 개수 표시
    cv2.putText(frame, f"Hands: {hand_count}", (20, 70),
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    # 통계 표시
    y_offset = 100
    cv2.putText(frame, "Statistics:", (20, y_offset),
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    y_offset += 25

    for ges, count in stats.most_common(3):
        emoji = {'Rock': '✊', 'Paper': '✋', 'Scissors': '✌️'}.get(ges, '')
        stat_text = f"{emoji} {ges}: {count}"
        cv2.putText(frame, stat_text, (20, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        y_offset += 25

    # 현재 제스처 크게 표시
    if gesture:
        gesture_map = {
            'Rock': ('주먹 ✊', (0, 0, 255)),
            'Paper': ('보 ✋', (0, 255, 0)),
            'Scissors': ('가위 ✌️', (255, 0, 0))
        }

        text, color = gesture_map.get(gesture, (gesture, (255, 255, 255)))

        # 텍스트 크기 계산
        font_scale = 2.0
        thickness = 4
        text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX,
                                    font_scale, thickness)[0]

        # 중앙 상단에 표시
        text_x = (w - text_size[0]) // 2
        text_y = 80

        # 배경 박스
        cv2.rectangle(frame,
                     (text_x - 10, text_y - text_size[1] - 10),
                     (text_x + text_size[0] + 10, text_y + 10),
                     color, -1)

        cv2.putText(frame, text, (text_x, text_y),
                   cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), thickness)

    return frame


def main():
    """메인 함수"""
    print("=" * 70)
    print("고급 가위바위보 인식 시스템 (MediaPipe Hands)")
    print("=" * 70)
    print("\n[사용법]")
    print("- 웹캠 앞에서 손을 보여주세요")
    print("- 주먹(✊): 손가락을 모두 접기")
    print("- 보(✋): 손가락을 모두 펴기")
    print("- 가위(✌️): 검지와 중지만 펴기")
    print("\n[단축키]")
    print("- 'q' 또는 ESC: 종료")
    print("- 'c': 화면 캡처")
    print("- 's': 통계 초기화")
    print("- 'r': 제스처 히스토리 초기화")
    print("=" * 70)

    # 인식기 초기화
    recognizer = HandGestureRecognizer()

    # 웹캠 열기
    print("\n[INFO] 웹캠 열기...")
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("[ERROR] 웹캠을 열 수 없습니다!")
        return

    # 웹캠 설정
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    print("[INFO] 웹캠 준비 완료!")
    print("[INFO] 프로그램 실행 중...\n")

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

            # 프레임 처리
            frame, gesture, hand_count = recognizer.process_frame(frame)

            # 통계 업데이트
            if gesture:
                stats[gesture] += 1

            # FPS 계산
            frame_count += 1
            if frame_count >= 30:
                fps = 30 / (time.time() - fps_start_time)
                fps_start_time = time.time()
                frame_count = 0

            # 정보 패널 그리기
            frame = draw_info_panel(frame, gesture, stats, fps, hand_count)

            # 사용 안내 표시
            cv2.putText(frame, "Press 'q' to quit, 'c' to capture, 's' to reset stats",
                       (10, frame.shape[0] - 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

            # 화면 표시
            cv2.imshow('Rock Paper Scissors - Advanced', frame)

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
            elif key == ord('r'):  # 제스처 히스토리 초기화
                recognizer.recent_gestures.clear()
                print("[INFO] 제스처 히스토리 초기화됨")

    except KeyboardInterrupt:
        print("\n[INFO] 사용자에 의해 중단됨")

    finally:
        # 정리
        recognizer.release()
        cap.release()
        cv2.destroyAllWindows()

        # 최종 통계 출력
        print("\n" + "=" * 70)
        print("최종 통계")
        print("=" * 70)
        if stats:
            total = sum(stats.values())
            for gesture, count in stats.most_common():
                percentage = (count / total) * 100
                emoji = {'Rock': '✊', 'Paper': '✋', 'Scissors': '✌️'}.get(gesture, '')
                print(f"{emoji} {gesture}: {count}회 ({percentage:.1f}%)")
        else:
            print("통계 없음")
        print("=" * 70)


if __name__ == "__main__":
    main()
