# 🤖 Line Tracer Project

노란색 라인을 따라가는 스마트 라인 트레이서 with 갈림길 감지

## 📁 프로젝트 구조

```
PI/
├── line_tracer_optimized.py            # 최적화 버전 (권장) 🌟
├── dual_roi_line_tracer_improved.py    # GUI 버전 (모니터 연결 필요)
├── dual_roi_line_tracer_headless.py    # 헤드리스 버전 (SSH용)
├── camera_diagnostic.py                 # 카메라 진단 도구
├── run_optimized.sh                     # 최적화 버전 실행 🌟
├── run_headless.sh                      # 헤드리스 모드 실행
├── run_line_tracer.sh                   # GUI 모드 실행
├── README.md                            # 이 파일
├── README_LINE_TRACER.md               # 상세 사용 설명서
│
├── archive/                             # 아카이브 폴더
│   ├── rock_paper_scissors/            # 가위바위보 프로젝트
│   ├── old_line_tracers/               # 이전 버전 라인 트레이서
│   ├── camera_tests/                   # 카메라 테스트 도구
│   └── docs/                           # 문서 아카이브
│
└── AI_CAR/                             # AI 자동차 관련 파일
```

## 🚀 빠른 시작

### 최적화 버전 (가장 권장) 🌟

```bash
# 1. 카메라 진단 (처음 한 번만)
python3 camera_diagnostic.py

# 2. 최적화 버전 실행
./run_optimized.sh

# 또는 직접 실행
python3 line_tracer_optimized.py
```

**최적화 버전의 장점:**
- ✅ 깔끔한 객체지향 설계
- ✅ 안정적인 종료 처리
- ✅ 실시간 통계 (FPS, 주행시간, 갈림길 횟수)
- ✅ 세션 요약 정보
- ✅ 더 부드러운 주행

### SSH로 접속했을 때 (기본 버전)

```bash
# 헤드리스 모드 실행
./run_headless.sh

# 또는 직접 실행
python3 dual_roi_line_tracer_headless.py
```

### 모니터/VNC 연결했을 때 (GUI 버전)

```bash
# GUI 버전 실행
./run_line_tracer.sh

# 또는 직접 실행
python3 dual_roi_line_tracer_improved.py
```

## ✨ 주요 기능

### 🔍 1. 스마트 라인 트레이싱
- 노란색 라인 전용 HSV 감지
- 3개 ROI (좌/중앙/우) 동시 감지
- 적응형 자동 조향

### 🔀 2. 갈림길 자동 감지
- 4가지 갈림길 타입 자동 인식
- 갈림길에서 자동 정지
- **헤드리스 모드**: 자동으로 직진 선택
- **GUI 모드**: 키보드로 방향 선택 가능

### 🔄 3. 라인 검색 모드
- 라인 손실 시 5단계 검색 알고리즘
- 마지막 본 방향 기반 지능형 회전

### ⏪ 4. 라인 이탈 후진
- 1초 이상 라인 못 찾으면 자동 후진
- 2초 후진 후 라인 검색 재개

## 🔧 설정

### GPU 메모리 설정 (필수)

```bash
sudo nano /boot/firmware/config.txt

# 파일 끝에 추가
gpu_mem=128

# 저장 후 재부팅
sudo reboot
```

### GPIO 권한 설정

```bash
sudo usermod -a -G gpio $USER
# 로그아웃 후 다시 로그인
```

## 📊 버전 비교

| 기능 | 최적화 버전 🌟 | 헤드리스 버전 | GUI 버전 |
|------|---------------|--------------|----------|
| 실행 환경 | SSH ✅ | SSH ✅ | 모니터/VNC |
| 화면 표시 | 콘솔 (통계) | 콘솔 (기본) | OpenCV 창 |
| 갈림길 제어 | 자동 (우선순위) | 자동 (직진) | 키보드 입력 |
| 코드 구조 | 객체지향 ✅ | 절차적 | 절차적 |
| 통계 출력 | FPS/시간/갈림길 ✅ | 5초마다 | - |
| 종료 처리 | 안정적 ✅ | 안정적 ✅ | 기본 |
| 세션 요약 | ✅ | - | - |
| 추천 용도 | **일반 주행** | 디버깅 | 파라미터 조정 |

## 🐛 문제 해결

### Qt 디스플레이 오류
```
qt.qpa.xcb: could not connect to display
```

**해결**: 헤드리스 모드 사용
```bash
python3 dual_roi_line_tracer_headless.py
```

### 카메라 메모리 오류
```
Failed to allocate required memory
```

**해결**: GPU 메모리 증가 (위 "GPU 메모리 설정" 참고)

### GPIO 권한 오류
```
RuntimeError: No access to /dev/gpiomem
```

**해결**: GPIO 그룹에 사용자 추가 (위 "GPIO 권한 설정" 참고)

## 📖 상세 문서

- [README_LINE_TRACER.md](README_LINE_TRACER.md) - 전체 기능 설명 및 사용법
- `camera_diagnostic.py` - 카메라 문제 진단

## 🎯 실행 예시

### 헤드리스 모드 출력

```
==========================================================
 Line Tracer - Headless Mode (SSH Compatible)
==========================================================
[INFO] Press Ctrl+C to stop

[INFO] Trying Picamera2...
[INFO] Picamera2 initialized successfully!
[INFO] GPIO initialized successfully

[MOTOR] FORWARD speed=65
[STATUS] L: 245 C: 892 R: 156 | forward
[MOTOR] LEFT speed=50
[STATUS] L: 678 C: 123 R:  45 | left
[JUNCTION] Detected! Available: ['left', 'forward', 'right']
[JUNCTION] Auto-selecting: forward
[MOTOR] FORWARD speed=65
```

## 🤝 기여

버그 리포트 및 개선 제안은 GitHub Issues로 부탁드립니다.

## 📝 라이선스

MIT License

---

**Made with ❤️ by Claude Code**
