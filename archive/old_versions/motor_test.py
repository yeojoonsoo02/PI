"""
Motor Test - 모터 동작 테스트
각 방향으로 1초씩 동작하여 모터가 정상인지 확인
"""
import time

try:
    import RPi.GPIO as GPIO

    # GPIO 설정
    IN1, IN2, IN3, IN4, ENA, ENB = 17, 18, 22, 23, 24, 25
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    # 모든 핀을 출력 모드로 설정
    for pin in (IN1, IN2, IN3, IN4, ENA, ENB):
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, False)  # 초기화

    # PWM 설정
    pwmA = GPIO.PWM(ENA, 1000)
    pwmB = GPIO.PWM(ENB, 1000)
    pwmA.start(0)
    pwmB.start(0)

    print("=" * 60)
    print(" Motor Test Program")
    print("=" * 60)
    print()

    def test_forward():
        """전진 테스트"""
        print("[1/4] Testing FORWARD...")
        GPIO.output(IN1, True)
        GPIO.output(IN2, False)
        GPIO.output(IN3, True)
        GPIO.output(IN4, False)
        pwmA.ChangeDutyCycle(70)
        pwmB.ChangeDutyCycle(70)
        time.sleep(2)

    def test_backward():
        """후진 테스트"""
        print("[2/4] Testing BACKWARD...")
        GPIO.output(IN1, False)
        GPIO.output(IN2, True)
        GPIO.output(IN3, False)
        GPIO.output(IN4, True)
        pwmA.ChangeDutyCycle(70)
        pwmB.ChangeDutyCycle(70)
        time.sleep(2)

    def test_left():
        """좌회전 테스트"""
        print("[3/4] Testing LEFT...")
        GPIO.output(IN1, True)
        GPIO.output(IN2, False)
        GPIO.output(IN3, False)
        GPIO.output(IN4, True)
        pwmA.ChangeDutyCycle(70)
        pwmB.ChangeDutyCycle(70)
        time.sleep(2)

    def test_right():
        """우회전 테스트"""
        print("[4/4] Testing RIGHT...")
        GPIO.output(IN1, False)
        GPIO.output(IN2, True)
        GPIO.output(IN3, True)
        GPIO.output(IN4, False)
        pwmA.ChangeDutyCycle(70)
        pwmB.ChangeDutyCycle(70)
        time.sleep(2)

    def stop():
        """정지"""
        GPIO.output(IN1, False)
        GPIO.output(IN2, False)
        GPIO.output(IN3, False)
        GPIO.output(IN4, False)
        pwmA.ChangeDutyCycle(0)
        pwmB.ChangeDutyCycle(0)

    # 테스트 시작
    print("Starting motor test in 3 seconds...")
    print("Press Ctrl+C to stop")
    print()
    time.sleep(3)

    try:
        test_forward()
        stop()
        time.sleep(1)

        test_backward()
        stop()
        time.sleep(1)

        test_left()
        stop()
        time.sleep(1)

        test_right()
        stop()

        print()
        print("=" * 60)
        print(" Test Complete!")
        print("=" * 60)
        print()
        print("Results:")
        print("  ✓ If robot moved forward   → Motor OK")
        print("  ✓ If robot moved backward  → Motor OK")
        print("  ✓ If robot turned left     → Motor OK")
        print("  ✓ If robot turned right    → Motor OK")
        print()
        print("If no movement:")
        print("  ✗ Check motor driver connections")
        print("  ✗ Check power supply to motors")
        print("  ✗ Check GPIO pin assignments")

    except KeyboardInterrupt:
        print("\n[INFO] Test stopped by user")

    finally:
        stop()
        pwmA.stop()
        pwmB.stop()
        GPIO.cleanup()
        print("[✓] Cleanup complete")

except ImportError:
    print("[ERROR] RPi.GPIO not available")
    print("This test must run on Raspberry Pi")

except Exception as e:
    print(f"[ERROR] {e}")
    try:
        GPIO.cleanup()
    except:
        pass
