"""
카메라 및 ROI 색상 구분 테스트 스크립트
카메라 회전 상태와 우측 하단 색상 감지 확인
"""
import cv2


def open_camera():
    """카메라 열기"""
    cap = cv2.VideoCapture(0)
    if cap.isOpened():
        print("[INFO] OpenCV 카메라 연결 성공")
        return cap, "opencv"

    try:
        from picamera2 import Picamera2
        picam2 = Picamera2()
        picam2.configure(picam2.create_preview_configuration(main={"format": "RGB888"}))
        picam2.start()
        print("[INFO] PiCamera2 연결 성공")

        class PicamWrap:
            def read(self):
                frame = picam2.capture_array()
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                return True, frame

            def release(self):
                picam2.stop()

        return PicamWrap(), "picamera2"
    except Exception as e:
        print(f"[ERROR] 카메라 연결 실패: {e}")
        return None, None


def main():
    """메인 테스트 루프"""
    print("=" * 60)
    print("카메라 및 ROI 색상 구분 테스트")
    print("=" * 60)
    print("[INFO] 키 조작:")
    print("  f: 카메라 상하 반전 (flip vertical)")
    print("  h: 카메라 좌우 반전 (flip horizontal)")
    print("  r: 180도 회전 (flip both)")
    print("  n: 원본으로 복원 (no flip)")
    print("  1/2: 이진화 임계값 조정")
    print("  q/ESC: 종료")
    print("=" * 60)

    cap, cam_type = open_camera()
    if cap is None:
        print("[ERROR] 카메라를 열 수 없습니다.")
        return

    print(f"[INFO] 카메라 타입: {cam_type}")

    # ROI 설정
    roi_height_ratio = 0.3
    roi_width_ratio = 0.3
    thresh = 150
    flip_mode = None  # None, 0(상하), 1(좌우), -1(180도)

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("[ERROR] 프레임을 읽을 수 없습니다.")
                break

            # 카메라 회전 적용
            if flip_mode is not None:
                frame = cv2.flip(frame, flip_mode)

            h, w = frame.shape[:2]

            # ROI 영역 계산
            roi_h = int(h * roi_height_ratio)
            roi_w = int(w * roi_width_ratio)
            roi_y = h - roi_h

            # 좌측 하단 ROI
            left_roi = frame[roi_y:h, 0:roi_w]
            # 우측 하단 ROI
            right_roi = frame[roi_y:h, w-roi_w:w]

            # 좌측 ROI 처리
            left_gray = cv2.cvtColor(left_roi, cv2.COLOR_BGR2GRAY)
            left_blur = cv2.GaussianBlur(left_gray, (5, 5), 0)
            _, left_binary = cv2.threshold(left_blur, thresh, 255, cv2.THRESH_BINARY_INV)
            left_pixels = cv2.countNonZero(left_binary)

            # 우측 ROI 처리
            right_gray = cv2.cvtColor(right_roi, cv2.COLOR_BGR2GRAY)
            right_blur = cv2.GaussianBlur(right_gray, (5, 5), 0)
            _, right_binary = cv2.threshold(right_blur, thresh, 255, cv2.THRESH_BINARY_INV)
            right_pixels = cv2.countNonZero(right_binary)

            # 디버그 오버레이
            # 감지된 라인을 노란색으로 표시
            # 좌측 라인
            left_colored = cv2.cvtColor(left_binary, cv2.COLOR_GRAY2BGR)
            yellow_mask_left = cv2.inRange(left_colored, (200, 200, 200), (255, 255, 255))
            frame[roi_y:h, 0:roi_w][yellow_mask_left > 0] = [0, 255, 255]  # 노란색 (BGR)

            # 우측 라인
            right_colored = cv2.cvtColor(right_binary, cv2.COLOR_GRAY2BGR)
            yellow_mask_right = cv2.inRange(right_colored, (200, 200, 200), (255, 255, 255))
            frame[roi_y:h, w-roi_w:w][yellow_mask_right > 0] = [0, 255, 255]  # 노란색 (BGR)

            # 좌측 ROI 박스 (파란색)
            cv2.rectangle(frame, (0, roi_y), (roi_w, h), (255, 0, 0), 2)
            cv2.putText(frame, "LEFT ROI", (5, roi_y - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)

            # 우측 ROI 박스 (초록색)
            cv2.rectangle(frame, (w-roi_w, roi_y), (w, h), (0, 255, 0), 2)
            cv2.putText(frame, "RIGHT ROI", (w-roi_w+5, roi_y - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            # 중앙선 표시
            cv2.line(frame, (w//2, 0), (w//2, h), (0, 255, 255), 1)

            # 텍스트 정보
            y_pos = 30
            flip_text = "None" if flip_mode is None else f"Flip {flip_mode}"
            cv2.putText(frame, f"Flip Mode: {flip_text}", (10, y_pos),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

            y_pos += 30
            cv2.putText(frame, f"Threshold: {thresh}", (10, y_pos),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

            y_pos += 30
            cv2.putText(frame, f"Left Pixels: {left_pixels}", (10, y_pos),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)

            y_pos += 30
            cv2.putText(frame, f"Right Pixels: {right_pixels}", (10, y_pos),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            # 평균 밝기 계산 및 표시
            left_avg = left_gray.mean()
            right_avg = right_gray.mean()

            y_pos += 30
            cv2.putText(frame, f"Left Brightness: {left_avg:.1f}", (10, y_pos),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)

            y_pos += 30
            cv2.putText(frame, f"Right Brightness: {right_avg:.1f}", (10, y_pos),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            # 화면 출력
            cv2.imshow("Camera Test - Main", frame)

            # ROI 확대 표시
            left_roi_large = cv2.resize(left_roi, (300, 200))
            right_roi_large = cv2.resize(right_roi, (300, 200))

            cv2.imshow("Left ROI (Original)", left_roi_large)
            cv2.imshow("Right ROI (Original)", right_roi_large)

            # 이진화 이미지 표시
            left_binary_large = cv2.resize(left_binary, (300, 200))
            right_binary_large = cv2.resize(right_binary, (300, 200))

            cv2.imshow("Left ROI (Binary)", left_binary_large)
            cv2.imshow("Right ROI (Binary)", right_binary_large)

            # 키 입력 처리
            key = cv2.waitKey(1) & 0xFF
            if key in (27, ord('q')):
                print("[INFO] 종료")
                break
            elif key == ord('f'):
                flip_mode = 0 if flip_mode != 0 else None
                print(f"[INFO] 상하 반전: {'ON' if flip_mode == 0 else 'OFF'}")
            elif key == ord('h'):
                flip_mode = 1 if flip_mode != 1 else None
                print(f"[INFO] 좌우 반전: {'ON' if flip_mode == 1 else 'OFF'}")
            elif key == ord('r'):
                flip_mode = -1 if flip_mode != -1 else None
                print(f"[INFO] 180도 회전: {'ON' if flip_mode == -1 else 'OFF'}")
            elif key == ord('n'):
                flip_mode = None
                print("[INFO] 원본으로 복원")
            elif key == ord('1'):
                thresh = max(60, thresh - 5)
                print(f"[INFO] 임계값: {thresh}")
            elif key == ord('2'):
                thresh = min(220, thresh + 5)
                print(f"[INFO] 임계값: {thresh}")

    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("[INFO] 카메라 종료")


if __name__ == "__main__":
    main()
