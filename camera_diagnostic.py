#!/usr/bin/env python3
"""
라즈베리파이 카메라 진단 및 테스트 도구
"""
import cv2
import sys
import subprocess

def check_camera_devices():
    """카메라 디바이스 확인"""
    print("=" * 60)
    print(" 1. Camera Device Check")
    print("=" * 60)

    try:
        result = subprocess.run(
            ['ls', '-l', '/dev/video*'],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("[✓] Found camera devices:")
            print(result.stdout)
        else:
            print("[✗] No camera devices found!")
            return False
    except Exception as e:
        print(f"[✗] Error checking devices: {e}")
        return False

    return True


def check_picamera2():
    """Picamera2 모듈 확인"""
    print("\n" + "=" * 60)
    print(" 2. Picamera2 Module Check")
    print("=" * 60)

    try:
        from picamera2 import Picamera2
        print("[✓] Picamera2 module installed")

        # 카메라 정보 확인
        picam2 = Picamera2()
        camera_info = picam2.camera_properties
        print(f"[✓] Camera Model: {camera_info.get('Model', 'Unknown')}")
        print(f"[✓] Camera Location: {camera_info.get('Location', 'Unknown')}")
        picam2.close()
        return True

    except ImportError:
        print("[✗] Picamera2 module not installed")
        print("    Install with: sudo apt install -y python3-picamera2")
        return False
    except Exception as e:
        print(f"[✗] Picamera2 error: {e}")
        return False


def test_picamera2():
    """Picamera2로 카메라 테스트"""
    print("\n" + "=" * 60)
    print(" 3. Picamera2 Test (5 frames)")
    print("=" * 60)

    try:
        from picamera2 import Picamera2

        picam2 = Picamera2()
        config = picam2.create_preview_configuration(
            main={"format": "RGB888", "size": (640, 480)}
        )
        picam2.configure(config)
        picam2.start()

        print("[✓] Camera started successfully")

        for i in range(5):
            frame = picam2.capture_array()
            print(f"[✓] Frame {i+1}: {frame.shape}")

        picam2.stop()
        print("[✓] Picamera2 test PASSED")
        return True

    except Exception as e:
        print(f"[✗] Picamera2 test FAILED: {e}")
        return False


def test_opencv_v4l2():
    """OpenCV V4L2로 카메라 테스트"""
    print("\n" + "=" * 60)
    print(" 4. OpenCV V4L2 Test (5 frames)")
    print("=" * 60)

    try:
        cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        if not cap.isOpened():
            print("[✗] Failed to open camera")
            return False

        print("[✓] Camera opened successfully")

        for i in range(5):
            ret, frame = cap.read()
            if ret:
                print(f"[✓] Frame {i+1}: {frame.shape}")
            else:
                print(f"[✗] Failed to read frame {i+1}")
                break

        cap.release()
        print("[✓] OpenCV V4L2 test PASSED")
        return True

    except Exception as e:
        print(f"[✗] OpenCV V4L2 test FAILED: {e}")
        return False


def check_memory():
    """메모리 확인"""
    print("\n" + "=" * 60)
    print(" 5. Memory Check")
    print("=" * 60)

    try:
        result = subprocess.run(
            ['free', '-h'],
            capture_output=True,
            text=True
        )
        print(result.stdout)

        # GPU 메모리 확인 (라즈베리파이)
        try:
            result = subprocess.run(
                ['vcgencmd', 'get_mem', 'gpu'],
                capture_output=True,
                text=True
            )
            print(f"GPU Memory: {result.stdout.strip()}")
        except:
            pass

    except Exception as e:
        print(f"[✗] Memory check error: {e}")


def print_recommendations():
    """권장 사항 출력"""
    print("\n" + "=" * 60)
    print(" Recommendations")
    print("=" * 60)
    print("""
1. If Picamera2 failed:
   sudo apt update
   sudo apt install -y python3-picamera2

2. If memory allocation error:
   # Increase GPU memory in /boot/config.txt
   gpu_mem=128

3. If permission error:
   sudo usermod -a -G video $USER
   # Then logout and login again

4. Check camera is enabled:
   sudo raspi-config
   # Interface Options → Camera → Enable

5. Reboot if needed:
   sudo reboot
""")


def main():
    """메인 진단 루틴"""
    print("\n╔════════════════════════════════════════════════════════════╗")
    print("║      Raspberry Pi Camera Diagnostic Tool                  ║")
    print("╚════════════════════════════════════════════════════════════╝\n")

    results = {
        "device_check": check_camera_devices(),
        "picamera2_check": check_picamera2(),
        "picamera2_test": False,
        "opencv_test": False
    }

    # Picamera2가 사용 가능하면 테스트
    if results["picamera2_check"]:
        results["picamera2_test"] = test_picamera2()

    # OpenCV 테스트
    results["opencv_test"] = test_opencv_v4l2()

    # 메모리 확인
    check_memory()

    # 결과 요약
    print("\n" + "=" * 60)
    print(" Test Summary")
    print("=" * 60)

    for test, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{test:20s}: {status}")

    # 권장 사항
    if not all(results.values()):
        print_recommendations()

    # 최종 권장 방법
    print("\n" + "=" * 60)
    print(" Recommended Camera Method")
    print("=" * 60)

    if results["picamera2_test"]:
        print("[✓] Use Picamera2 (Recommended for Raspberry Pi Camera)")
    elif results["opencv_test"]:
        print("[✓] Use OpenCV V4L2 (USB Camera compatible)")
    else:
        print("[✗] No working camera method found!")
        print("    Please check camera connection and try again.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
