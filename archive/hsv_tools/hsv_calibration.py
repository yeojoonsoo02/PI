"""
HSV Calibration Tool - HSV 색상 범위 조정 도구
노란색 라인을 찾기 위한 최적의 HSV 값 찾기
"""
import cv2
import numpy as np

def init_camera():
    """카메라 초기화"""
    try:
        from picamera2 import Picamera2
        print("[INFO] Initializing Picamera2...")

        picam2 = Picamera2()
        config = picam2.create_preview_configuration(
            main={"format": "RGB888", "size": (640, 480)}
        )
        picam2.configure(config)
        picam2.start()

        print("[✓] Camera ready")

        class CameraWrapper:
            def read(self):
                frame = picam2.capture_array()
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                return True, frame

            def release(self):
                picam2.stop()

        return CameraWrapper()

    except Exception as e:
        print(f"[✗] Camera initialization failed: {e}")
        return None

def nothing(x):
    """트랙바 콜백 (필요함)"""
    pass

def main():
    """메인 루프"""
    print("=" * 60)
    print(" HSV Calibration Tool")
    print("=" * 60)
    print()
    print("Instructions:")
    print("  1. Adjust HSV sliders to isolate yellow line")
    print("  2. White pixels in 'Mask' window = detected")
    print("  3. Press 'q' to quit and show final values")
    print()

    camera = init_camera()
    if not camera:
        return

    # 윈도우 생성
    cv2.namedWindow("Original")
    cv2.namedWindow("Mask")
    cv2.namedWindow("Controls")

    # HSV 트랙바 생성
    cv2.createTrackbar("H Min", "Controls", 20, 179, nothing)
    cv2.createTrackbar("H Max", "Controls", 30, 179, nothing)
    cv2.createTrackbar("S Min", "Controls", 100, 255, nothing)
    cv2.createTrackbar("S Max", "Controls", 255, 255, nothing)
    cv2.createTrackbar("V Min", "Controls", 100, 255, nothing)
    cv2.createTrackbar("V Max", "Controls", 255, 255, nothing)

    print("[INFO] Adjust sliders to calibrate...")

    try:
        while True:
            # 프레임 읽기
            ret, frame = camera.read()
            if not ret:
                break

            # 이미지 뒤집기
            frame = cv2.flip(frame, -1)

            # ROI: 화면 하단 절반
            height = frame.shape[0]
            roi = frame[height // 2:, :]

            # BGR을 HSV로 변환
            hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

            # 트랙바 값 읽기
            h_min = cv2.getTrackbarPos("H Min", "Controls")
            h_max = cv2.getTrackbarPos("H Max", "Controls")
            s_min = cv2.getTrackbarPos("S Min", "Controls")
            s_max = cv2.getTrackbarPos("S Max", "Controls")
            v_min = cv2.getTrackbarPos("V Min", "Controls")
            v_max = cv2.getTrackbarPos("V Max", "Controls")

            # HSV 범위
            lower = np.array([h_min, s_min, v_min])
            upper = np.array([h_max, s_max, v_max])

            # 마스크 생성
            mask = cv2.inRange(hsv, lower, upper)

            # 노이즈 제거
            kernel = np.ones((3, 3), np.uint8)
            mask = cv2.erode(mask, kernel, iterations=2)
            mask = cv2.dilate(mask, kernel, iterations=2)

            # 픽셀 수 계산
            pixels = cv2.countNonZero(mask)

            # 결과 표시
            cv2.putText(frame, f"Pixels: {pixels}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(mask, f"Pixels: {pixels}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, 255, 2)

            cv2.imshow("Original", frame)
            cv2.imshow("Mask", mask)

            # 'q' 키로 종료
            if cv2.waitKey(1) == ord('q'):
                print("\n" + "=" * 60)
                print(" Calibrated HSV Values")
                print("=" * 60)
                print(f"lower_yellow = np.array([{h_min}, {s_min}, {v_min}])")
                print(f"upper_yellow = np.array([{h_max}, {s_max}, {v_max}])")
                print("=" * 60)
                print()
                print("Copy these values to yellow_line_follower.py!")
                break

    except KeyboardInterrupt:
        print("\n[INFO] Stopped by user")

    finally:
        camera.release()
        cv2.destroyAllWindows()
        print("[✓] Cleanup complete")

if __name__ == '__main__':
    main()
