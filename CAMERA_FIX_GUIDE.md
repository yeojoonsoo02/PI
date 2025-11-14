# 🎥 카메라 오류 해결 가이드

## ❌ 오류: "Pipeline handler in use by another process"

이 오류는 다른 프로세스가 카메라를 사용 중일 때 발생합니다.

---

## 🚀 빠른 해결 방법 (추천)

### 방법 1: 간단한 실행 스크립트 사용
```bash
# 실행 권한 부여 (처음 한 번만)
chmod +x run_line_tracer.sh

# 실행
sudo bash run_line_tracer.sh
```

### 방법 2: 수동 정리 후 실행
```bash
# 1단계: 프로세스 정리
sudo pkill -9 python
sudo pkill -9 -f libcamera

# 2단계: 2초 대기
sleep 2

# 3단계: 프로그램 실행
python /home/keonha/AI_CAR/new.py
```

---

## 🔧 강력한 해결 방법

위 방법이 안 되면 강제 정리 스크립트 사용:

```bash
# 실행 권한 부여 (처음 한 번만)
chmod +x force_camera_cleanup.sh

# 실행
sudo bash force_camera_cleanup.sh

# 프로그램 실행
python /home/keonha/AI_CAR/new.py
```

---

## 🔄 최후의 방법: 재부팅

모든 방법이 실패하면:

```bash
sudo reboot
```

재부팅 후:
```bash
python /home/keonha/AI_CAR/new.py
```

---

## 📋 프로세스 확인 명령

### 카메라 사용 프로세스 확인
```bash
# Python 프로세스 확인
ps aux | grep python

# 카메라 프로세스 확인
ps aux | grep -E "libcamera|picamera"

# 카메라 디바이스 사용 확인
sudo lsof /dev/video*
```

### 특정 프로세스 종료
```bash
# PID로 특정 프로세스 종료 (PID는 ps aux로 확인)
sudo kill -9 <PID>

# 예시:
sudo kill -9 1234
```

---

## ⚙️ 카메라 초기화 개선 사항

코드가 자동으로:
1. 3번 재시도
2. 각 시도마다 프로세스 정리
3. 실패 시 명확한 해결 방법 제시

---

## 🎯 예방 방법

1. **프로그램 종료 시**: `Ctrl+C`로 정상 종료
2. **다른 카메라 프로그램 실행 금지**: 라인 트레이서 실행 중 다른 카메라 프로그램 사용 X
3. **정기적 재부팅**: 장시간 사용 후 재부팅 권장

---

## 📁 스크립트 파일 위치

- `run_line_tracer.sh` - 간편 실행 스크립트
- `force_camera_cleanup.sh` - 강제 정리 스크립트
- `cleanup_camera.sh` - 일반 정리 스크립트

---

## ✅ 체크리스트

문제 발생 시 순서대로 시도:

- [ ] 방법 1: run_line_tracer.sh 실행
- [ ] 방법 2: 수동으로 프로세스 정리
- [ ] 방법 3: force_camera_cleanup.sh 실행
- [ ] 방법 4: 재부팅

---

작성일: 2024년 12월
Camera Fix Guide by Claude Code Assistant