"""
Keyboard Control - 키보드로 로봇 제어 (고속 버전)
W/A/S/D 키로 로봇을 움직입니다 (SSH 환경용)
+ 실시간 속도 조절 기능 추가
"""
import time
import sys
import tty
import termios
from gpiozero import DigitalOutputDevice, PWMOutputDevice

# 모터 핀 설정 (gpiozero)
PWMA = PWMOutputDevice(18)
AIN1 = DigitalOutputDevice(22)
AIN2 = DigitalOutputDevice(27)

PWMB = PWMOutputDevice(23)
BIN1 = DigitalOutputDevice(25)
BIN2 = DigitalOutputDevice(24)

# 속도 설정 (향상된 기본값)
SPEED = 0.75  # 기본 속도: 0.75 (이전 0.5에서 50% 증가)
MIN_SPEED = 0.3
MAX_SPEED = 1.0
SPEED_STEP = 0.1

def motor_forward(speed):
    """전진 - 빠른 반응"""
    AIN1.value = 0
    AIN2.value = 1
    PWMA.value = speed
    BIN1.value = 0
    BIN2.value = 1
    PWMB.value = speed

def motor_backward(speed):
    """후진 - 빠른 반응"""
    AIN1.value = 1
    AIN2.value = 0
    PWMA.value = speed
    BIN1.value = 1
    BIN2.value = 0
    PWMB.value = speed

def motor_left(speed):
    """좌회전 - 빠른 반응"""
    AIN1.value = 1
    AIN2.value = 0
    PWMA.value = 0.0
    BIN1.value = 0
    BIN2.value = 1
    PWMB.value = speed

def motor_right(speed):
    """우회전 - 빠른 반응"""
    AIN1.value = 0
    AIN2.value = 1
    PWMA.value = speed
    BIN1.value = 1
    BIN2.value = 0
    PWMB.value = 0.0

def motor_stop():
    """즉시 정지"""
    AIN1.value = 0
    AIN2.value = 0
    PWMA.value = 0.0
    BIN1.value = 0
    BIN2.value = 0.0
    PWMB.value = 0.0

def get_key():
    """터미널에서 키 입력 받기 (SSH 환경용)"""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)

        # 화살표 키 처리 (ESC 시퀀스)
        if ch == '\x1b':  # ESC
            ch2 = sys.stdin.read(1)
            if ch2 == '[':
                ch3 = sys.stdin.read(1)
                if ch3 == 'A':
                    return 'UP'
                elif ch3 == 'B':
                    return 'DOWN'
                elif ch3 == 'C':
                    return 'RIGHT'
                elif ch3 == 'D':
                    return 'LEFT'

        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

def print_status(current_speed, action=""):
    """현재 상태 출력 (한 줄로 깔끔하게)"""
    speed_bar = "█" * int(current_speed * 10)
    print(f"\r🚗 Speed: {current_speed:.1f} [{speed_bar:10s}] | {action:15s}", end='', flush=True)

def main():
    """메인 루프 - 고속 반응 모드"""
    global SPEED
    current_speed = SPEED

    print("=" * 70)
    print(" 🏎️  FAST Keyboard Control - 고속 반응 모드")
    print("=" * 70)
    print()
    print("Controls:")
    print("  W / ↑     : Forward      |  +  : Speed UP   (+0.1)")
    print("  S / ↓     : Backward     |  -  : Speed DOWN (-0.1)")
    print("  A / ←     : Left         |  T  : TURBO (Max Speed)")
    print("  D / →     : Right        |  R  : Reset Speed (0.75)")
    print("  X / Space : Stop         |  Q  : Quit")
    print("=" * 70)
    print()
    print_status(current_speed, "Ready")
    print()

    last_action = "Ready"

    try:
        while True:
            key = get_key()

            # 종료
            if key in ['q', 'Q']:
                print("\n\n[INFO] Quitting...")
                break

            # 속도 조절
            elif key == '+' or key == '=':
                current_speed = min(current_speed + SPEED_STEP, MAX_SPEED)
                last_action = f"⬆️  Speed UP: {current_speed:.1f}"

            elif key == '-' or key == '_':
                current_speed = max(current_speed - SPEED_STEP, MIN_SPEED)
                last_action = f"⬇️  Speed DOWN: {current_speed:.1f}"

            elif key in ['t', 'T']:
                current_speed = MAX_SPEED
                last_action = "🚀 TURBO MODE!"

            elif key in ['r', 'R']:
                current_speed = 0.75
                last_action = "🔄 Reset: 0.75"

            # 전진
            elif key in ['w', 'W', 'UP']:
                motor_forward(current_speed)
                last_action = "⬆️  Forward"

            # 후진
            elif key in ['s', 'S', 'DOWN']:
                motor_backward(current_speed)
                last_action = "⬇️  Backward"

            # 좌회전
            elif key in ['a', 'A', 'LEFT']:
                motor_left(current_speed)
                last_action = "⬅️  Left Turn"

            # 우회전
            elif key in ['d', 'D', 'RIGHT']:
                motor_right(current_speed)
                last_action = "➡️  Right Turn"

            # 정지
            elif key in ['x', 'X', ' ']:
                motor_stop()
                last_action = "🛑 STOP"

            # 상태 표시 업데이트
            print_status(current_speed, last_action)

    except KeyboardInterrupt:
        print("\n\n[INFO] Stopped by user")

    finally:
        motor_stop()
        PWMA.value = 0.0
        PWMB.value = 0.0
        print("\n[✓] Motors stopped, cleanup complete")

if __name__ == '__main__':
    main()
