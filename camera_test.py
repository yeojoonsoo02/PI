#!/usr/bin/env python3
"""
카메라 테스트 스크립트
카메라 연결 상태 확인 및 기본 기능 테스트
"""

import time
import sys

def test_camera():
    print("=" * 60)
    print(" 라즈베리파이 카메라 테스트")
    print("=" * 60)
    print()

    # 1. libcamera 테스트
    print("1. libcamera 상태 확인...")
    import subprocess
    try:
        result = subprocess.run(['libcamera-hello', '--list-cameras'],
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✓ libcamera 정상")
            print(result.stdout)
        else:
            print("✗ libcamera 오류:")
            print(result.stderr)
    except Exception as e:
        print(f"✗ libcamera 실행 실패: {e}")

    print()

    # 2. Picamera2 import 테스트
    print("2. Picamera2 모듈 확인...")
    try:
        from picamera2 import Picamera2
        print("✓ Picamera2 모듈 정상")
    except ImportError as e:
        print(f"✗ Picamera2 import 실패: {e}")
        print("설치 명령: sudo apt install python3-picamera2")
        return False

    print()

    # 3. 카메라 초기화 테스트
    print("3. 카메라 초기화 시도...")
    try:
        picam2 = Picamera2()
        print("✓ Picamera2 객체 생성 성공")

        # 카메라 정보 출력
        camera_info = picam2.camera_properties
        print(f"  - 모델: {camera_info.get('Model', 'Unknown')}")
        print(f"  - 픽셀 배열 크기: {camera_info.get('PixelArraySize', 'Unknown')}")

        # 설정 생성
        config = picam2.create_preview_configuration(
            main={"format": "RGB888", "size": (640, 480)}
        )
        picam2.configure(config)
        print("✓ 카메라 설정 완료 (640x480)")

        # 카메라 시작
        picam2.start()
        print("✓ 카메라 시작 성공")

        # 프레임 캡처 테스트
        time.sleep(1)
        frame = picam2.capture_array()
        print(f"✓ 프레임 캡처 성공: {frame.shape}")

        # 정리
        picam2.stop()
        print("✓ 카메라 정상 종료")

        return True

    except Exception as e:
        print(f"✗ 카메라 초기화 실패: {e}")

        # 자주 발생하는 오류별 해결책 제시
        error_msg = str(e)
        if "Pipeline handler in use" in error_msg:
            print("\n⚠ 다른 프로세스가 카메라를 사용 중입니다!")
            print("해결 방법:")
            print("1. 실행 중인 카메라 프로그램 종료:")
            print("   pkill -f python")
            print("2. 카메라 관련 프로세스 확인:")
            print("   ps aux | grep camera")

        elif "Camera not found" in error_msg:
            print("\n⚠ 카메라가 연결되지 않았습니다!")
            print("해결 방법:")
            print("1. 카메라 케이블 연결 확인")
            print("2. 카메라 활성화 확인:")
            print("   sudo raspi-config → Interface Options → Camera")

        return False

    print()

def check_processes():
    """카메라 관련 프로세스 확인"""
    print("4. 실행 중인 관련 프로세스 확인...")
    import subprocess

    try:
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        processes = result.stdout.split('\n')

        camera_processes = []
        for proc in processes:
            if any(keyword in proc.lower() for keyword in ['camera', 'libcamera', 'picamera']):
                if 'grep' not in proc:
                    camera_processes.append(proc)

        if camera_processes:
            print("⚠ 카메라 관련 프로세스 발견:")
            for proc in camera_processes:
                # 프로세스 정보 간단히 표시
                parts = proc.split()
                if len(parts) > 10:
                    pid = parts[1]
                    cmd = ' '.join(parts[10:])[:50]  # 명령어 일부만
                    print(f"  PID {pid}: {cmd}...")
        else:
            print("✓ 카메라 관련 프로세스 없음")

    except Exception as e:
        print(f"프로세스 확인 실패: {e}")

if __name__ == "__main__":
    print("카메라 테스트를 시작합니다...\n")

    # 프로세스 확인
    check_processes()
    print()

    # 카메라 테스트
    success = test_camera()

    print()
    print("=" * 60)
    if success:
        print(" ✓ 카메라 테스트 성공!")
        print(" 이제 line_tracer_integrated.py를 실행할 수 있습니다.")
    else:
        print(" ✗ 카메라 테스트 실패")
        print(" 위의 오류 메시지를 확인하고 해결하세요.")
    print("=" * 60)