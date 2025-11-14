#!/usr/bin/env python3
"""
키보드 입력 테스트 스크립트
line_tracer_integrated.py의 단순화된 키보드 제어 테스트용
"""

import sys
import select
import termios
import tty

def get_user_input():
    """키보드 입력 받기 (non-blocking)"""
    if select.select([sys.stdin], [], [], 0.01)[0]:
        user_input = sys.stdin.read(1).lower()
        return user_input if user_input in ['w', 'a', 's', 'd', 'q'] else None
    return None

def test_keyboard():
    print("=" * 50)
    print(" 키보드 제어 테스트 (improved.py 스타일)")
    print("=" * 50)
    print()
    print("조작 방법:")
    print("  [w] 직진 | [a] 좌회전 | [d] 우회전")
    print("  [s] 정지 | [q] 종료")
    print()
    print("입력을 기다리는 중...")

    # 터미널 설정
    old_settings = termios.tcgetattr(sys.stdin)
    try:
        tty.setcbreak(sys.stdin.fileno())

        while True:
            user_input = get_user_input()
            if user_input:
                print(f"\n입력 받음: '{user_input}'")

                if user_input == 'w':
                    print("  → 직진 실행 (motor_forward)")
                    print("  → action = 'FORWARD'")
                elif user_input == 'a':
                    print("  → 좌회전 실행 (motor_left)")
                    print("  → action = 'LEFT'")
                elif user_input == 'd':
                    print("  → 우회전 실행 (motor_right)")
                    print("  → action = 'RIGHT'")
                elif user_input == 's':
                    print("  → 정지 유지 (motor_stop)")
                    print("  → action = 'STOP'")
                elif user_input == 'q':
                    print("\n프로그램 종료...")
                    break

    finally:
        # 터미널 설정 복원
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        print("\n테스트 완료!")

if __name__ == "__main__":
    test_keyboard()