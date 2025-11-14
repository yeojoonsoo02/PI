"""
main.py
-------
라즈베리파이 자율주행 자동차 메인 스크립트

* lane_tracer.py  : 차선 주행 스레드
* object_detector.py : 객체 탐지 스레드 (YOLOv8)
* shared_state.py : 전역 상태 공유
"""

import threading
import time
import shared_state
from lane_tracer import lane_follow_loop
from object_detector import object_detect_loop
from gpiozero import PWMOutputDevice

# ============================================================
# 메인 실행 함수
# ============================================================

def main():
    print("=" * 70)
    print(" Autonomous Car System: Line + Object Integration")
    print("=" * 70)

    # --- 두 스레드 실행 ---
    lane_thread = threading.Thread(target=lane_follow_loop, daemon=True)
    detect_thread = threading.Thread(target=object_detect_loop, daemon=True)
    lane_thread.start()
    detect_thread.start()

    print("[✓] Threads started (Lane Follower + Object Detector)")
    print("[INFO] Press Ctrl+C to terminate\n")

    last_trigger_displayed = None

    try:
        while True:
            # 공유 상태 확인
            with shared_state.lock:
                obj_name = shared_state.object_detected
                obj_dist = shared_state.object_distance
                trig = shared_state.last_trigger
                obj_state = shared_state.object_state.copy()

            # --- 모니터링 출력 ---
            if obj_name:
                print(f"[MONITOR] Detected: {obj_name:12s} | area={obj_dist}")

            # 활성 상태맵 출력 (디버깅용)
            active_objects = [k for k, v in obj_state.items() if v]
            if active_objects:
                print(f"[ACTIVE] {', '.join(active_objects)}")

            # 새로운 트리거 발생 시 출력
            if trig and trig != last_trigger_displayed:
                print(f"\n Action Triggered: {trig}\n")
                last_trigger_displayed = trig

            time.sleep(1.0)

    except KeyboardInterrupt:
        print("\n[INFO] Program stopped by user.")

    finally:
        # 안전 정지
        try:
            PWMA = PWMOutputDevice(18)
            PWMB = PWMOutputDevice(23)
            PWMA.value = 0.0
            PWMB.value = 0.0
            print("[✓] Motors stopped safely.")
        except Exception:
            pass

        print("[✓] All threads stopped. Cleanup complete.")


if __name__ == "__main__":
    main()
