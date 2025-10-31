"""
빠른 카메라 확인 스크립트
카메라가 작동하는지만 빠르게 확인
"""
import cv2
import sys

print("카메라 연결 확인 중...")

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("❌ 카메라를 열 수 없습니다.")
    print("해결 방법:")
    print("1. 카메라가 연결되어 있는지 확인")
    print("2. 다른 프로그램에서 카메라를 사용중인지 확인")
    print("3. Mac: 시스템 환경설정 > 보안 및 개인정보 보호에서 카메라 권한 확인")
    sys.exit(1)

print("✅ 카메라 연결 성공!")

# 프레임 읽기 테스트
ret, frame = cap.read()
if not ret:
    print("❌ 프레임을 읽을 수 없습니다.")
    cap.release()
    sys.exit(1)

print(f"✅ 프레임 읽기 성공! 해상도: {frame.shape[1]}x{frame.shape[0]}")

# 5프레임 테스트
print("\n5프레임 테스트 중...")
for i in range(5):
    ret, frame = cap.read()
    if ret:
        print(f"  프레임 {i+1}/5 ✅")
    else:
        print(f"  프레임 {i+1}/5 ❌")
        break

cap.release()

print("\n" + "="*50)
print("카메라 확인 완료! 이제 전체 테스트를 실행하세요:")
print("  python test_camera_roi.py")
print("또는")
print("  ./run_test.sh")
print("="*50)
