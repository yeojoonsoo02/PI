"""
HSV Calibration Tool (Headless Version)
노란색 라인을 찾기 위한 HSV 값 테스트 - SSH 환경용
여러 HSV 범위를 테스트하고 결과를 이미지로 저장
"""
import cv2
import numpy as np
import time
import os

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
        time.sleep(2)  # 카메라 준비 대기

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

def test_hsv_range(frame, h_min, h_max, s_min, s_max, v_min, v_max):
    """주어진 HSV 범위로 마스크 생성 및 테스트"""
    # ROI: 화면 하단 절반
    height = frame.shape[0]
    roi = frame[height // 2:, :]

    # BGR을 HSV로 변환
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

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

    return mask, pixels, roi

def main():
    """메인 루프"""
    print("=" * 60)
    print(" HSV Calibration Tool (Headless Version)")
    print("=" * 60)
    print()
    print("이 도구는 여러 HSV 범위를 자동으로 테스트합니다")
    print("결과 이미지가 'hsv_test_results/' 폴더에 저장됩니다")
    print()

    # 결과 폴더 생성
    output_dir = "hsv_test_results"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"[INFO] Created output directory: {output_dir}/")

    camera = init_camera()
    if not camera:
        return

    # 프레임 캡처
    print("[INFO] Capturing frame...")
    ret, frame = camera.read()
    if not ret:
        print("[ERROR] Failed to capture frame")
        camera.release()
        return

    # 원본 이미지 뒤집기
    frame = cv2.flip(frame, -1)

    # 원본 저장
    cv2.imwrite(f"{output_dir}/00_original.jpg", frame)
    print(f"[✓] Saved: {output_dir}/00_original.jpg")

    # 테스트할 HSV 범위들
    hsv_ranges = [
        # (name, h_min, h_max, s_min, s_max, v_min, v_max)
        ("default_yellow", 20, 30, 100, 255, 100, 255),
        ("bright_yellow", 20, 35, 80, 255, 150, 255),
        ("dark_yellow", 15, 30, 120, 255, 80, 200),
        ("wide_yellow", 15, 40, 60, 255, 80, 255),
        ("narrow_yellow", 22, 28, 120, 255, 120, 255),
        ("very_bright", 20, 30, 60, 255, 180, 255),
        ("medium_sat", 20, 30, 100, 200, 100, 255),
    ]

    print()
    print(f"[INFO] Testing {len(hsv_ranges)} HSV ranges...")
    print()

    results = []

    for idx, (name, h_min, h_max, s_min, s_max, v_min, v_max) in enumerate(hsv_ranges, 1):
        mask, pixels, roi = test_hsv_range(frame, h_min, h_max, s_min, s_max, v_min, v_max)

        # 결과 이미지 생성 (ROI + Mask 나란히)
        result_img = np.hstack([roi, cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)])

        # 텍스트 추가
        text_lines = [
            f"Test {idx}: {name}",
            f"H:[{h_min},{h_max}] S:[{s_min},{s_max}] V:[{v_min},{v_max}]",
            f"Yellow pixels: {pixels}"
        ]

        y_offset = 30
        for line in text_lines:
            cv2.putText(result_img, line, (10, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            y_offset += 25

        # 저장
        filename = f"{output_dir}/{idx:02d}_{name}.jpg"
        cv2.imwrite(filename, result_img)

        # 결과 출력
        quality = "✓ GOOD" if pixels > 500 else ("⚠ LOW" if pixels > 100 else "✗ TOO LOW")
        print(f"[{idx:2d}] {name:20s} | Pixels: {pixels:5d} | {quality}")

        results.append((name, h_min, h_max, s_min, s_max, v_min, v_max, pixels))

    # 최적 범위 찾기
    print()
    print("=" * 60)
    print(" Analysis Results")
    print("=" * 60)

    # 픽셀 수로 정렬
    results.sort(key=lambda x: x[7], reverse=True)

    print()
    print("Top 3 HSV ranges by pixel count:")
    print()
    for i, (name, h_min, h_max, s_min, s_max, v_min, v_max, pixels) in enumerate(results[:3], 1):
        print(f"{i}. {name} ({pixels} pixels)")
        print(f"   lower_yellow = np.array([{h_min}, {s_min}, {v_min}])")
        print(f"   upper_yellow = np.array([{h_max}, {s_max}, {v_max}])")
        print()

    # 요약 파일 생성
    summary_file = f"{output_dir}/RESULTS.txt"
    with open(summary_file, 'w') as f:
        f.write("HSV Calibration Test Results\n")
        f.write("=" * 60 + "\n\n")

        f.write("Top 3 HSV ranges:\n\n")
        for i, (name, h_min, h_max, s_min, s_max, v_min, v_max, pixels) in enumerate(results[:3], 1):
            f.write(f"{i}. {name} ({pixels} pixels)\n")
            f.write(f"   lower_yellow = np.array([{h_min}, {s_min}, {v_min}])\n")
            f.write(f"   upper_yellow = np.array([{h_max}, {s_max}, {v_max}])\n\n")

        f.write("\nAll results (sorted by pixel count):\n\n")
        for name, h_min, h_max, s_min, s_max, v_min, v_max, pixels in results:
            f.write(f"{name:20s} | H:[{h_min:2d},{h_max:2d}] S:[{s_min:3d},{s_max:3d}] V:[{v_min:3d},{v_max:3d}] | {pixels:5d} pixels\n")

    print(f"[✓] Summary saved to: {summary_file}")
    print()
    print(f"[INFO] Check images in '{output_dir}/' folder")
    print(f"[INFO] Use 'scp' to download images for review:")
    print(f"       scp -r easo6@raspberrypi:~/Desktop/yeojoonsoo02/{output_dir} .")
    print()

    camera.release()
    print("[✓] Done!")

if __name__ == '__main__':
    main()
