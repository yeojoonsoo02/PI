"""
노란색 라인 색상 범위 캘리브레이션 도구
실시간으로 HSV 범위를 조정하여 최적의 값을 찾을 수 있습니다.
"""
import cv2
import numpy as np

def nothing(x):
    pass

def main():
    # 카메라 열기
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("카메라를 열 수 없습니다.")
        return

    # 트랙바 윈도우 생성
    cv2.namedWindow('Trackbars')

    # HSV 범위 트랙바 생성
    cv2.createTrackbar('H_min', 'Trackbars', 20, 179, nothing)
    cv2.createTrackbar('H_max', 'Trackbars', 30, 179, nothing)
    cv2.createTrackbar('S_min', 'Trackbars', 100, 255, nothing)
    cv2.createTrackbar('S_max', 'Trackbars', 255, 255, nothing)
    cv2.createTrackbar('V_min', 'Trackbars', 100, 255, nothing)
    cv2.createTrackbar('V_max', 'Trackbars', 255, 255, nothing)

    print("=" * 60)
    print("노란색 라인 색상 캘리브레이션 도구")
    print("=" * 60)
    print("트랙바를 조정하여 노란색 선만 흰색으로 보이도록 설정하세요.")
    print("q 키를 눌러 종료하면 최종 값이 출력됩니다.")
    print("=" * 60)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # 하단 절반만 사용 (라인 트레이싱과 동일)
        height, width, _ = frame.shape
        crop_img = frame[height // 2:, :]

        # BGR을 HSV로 변환
        hsv = cv2.cvtColor(crop_img, cv2.COLOR_BGR2HSV)

        # 트랙바 값 읽기
        h_min = cv2.getTrackbarPos('H_min', 'Trackbars')
        h_max = cv2.getTrackbarPos('H_max', 'Trackbars')
        s_min = cv2.getTrackbarPos('S_min', 'Trackbars')
        s_max = cv2.getTrackbarPos('S_max', 'Trackbars')
        v_min = cv2.getTrackbarPos('V_min', 'Trackbars')
        v_max = cv2.getTrackbarPos('V_max', 'Trackbars')

        # 색상 범위 설정
        lower = np.array([h_min, s_min, v_min])
        upper = np.array([h_max, s_max, v_max])

        # 마스크 생성
        mask = cv2.inRange(hsv, lower, upper)

        # 결과 이미지
        result = cv2.bitwise_and(crop_img, crop_img, mask=mask)

        # 현재 값을 화면에 표시
        info_text = f"H:{h_min}-{h_max} S:{s_min}-{s_max} V:{v_min}-{v_max}"
        cv2.putText(frame, info_text, (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # 화면 출력
        cv2.imshow('Original', frame)
        cv2.imshow('Cropped', crop_img)
        cv2.imshow('HSV', hsv)
        cv2.imshow('Mask', mask)
        cv2.imshow('Result', result)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            print("\n최종 HSV 값:")
            print(f"lower_yellow = np.array([{h_min}, {s_min}, {v_min}])")
            print(f"upper_yellow = np.array([{h_max}, {s_max}, {v_max}])")
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
