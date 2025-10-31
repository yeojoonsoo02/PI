# 🚀 빠른 시작 가이드

## 1분 만에 시작하기

### 1단계: 라이브러리 설치 확인

```bash
# 이미 설치되었습니다!
pip list | grep -E "ultralytics|mediapipe|opencv-python"
```

### 2단계: 프로그램 실행

**추천: MediaPipe 버전 (가장 정확)**

```bash
python rock_paper_scissors_advanced.py
```

**대안: YOLO 기본 버전**

```bash
python rock_paper_scissors_yolo.py
```

### 3단계: 사용하기

1. 웹캠 창이 열리면 손을 보여주세요
2. 제스처를 만들어보세요:
   - ✊ **주먹**: 손가락을 모두 접기
   - ✋ **보**: 손가락을 모두 펴기
   - ✌️ **가위**: 검지와 중지만 펴기

3. 화면에 실시간으로 인식 결과가 표시됩니다!

### 단축키

| 키 | 기능 |
|----|------|
| `q` | 종료 |
| `c` | 화면 캡처 |
| `s` | 통계 초기화 |

## 🎯 어떤 버전을 선택해야 할까요?

| 버전 | 추천 대상 | 장점 |
|------|----------|------|
| **rock_paper_scissors_advanced.py** | 일반 사용자 | 높은 정확도, 안정적 |
| **rock_paper_scissors_yolo.py** | YOLO 학습자 | 커스터마이징 가능 |

## 📹 데모 영상

프로그램 실행 후 다음과 같은 화면이 나타납니다:

```
┌──────────────────────────────────────┐
│  FPS: 30.5        Hands: 1           │
│                                      │
│  Statistics:                         │
│  ✊ Rock: 45                         │
│  ✋ Paper: 32                        │
│  ✌️ Scissors: 23                     │
│                                      │
│         가위 ✌️                      │
│                                      │
│   [손 랜드마크가 화면에 표시됨]      │
│                                      │
└──────────────────────────────────────┘
```

## 🔧 문제 해결

### 웹캠이 열리지 않아요!

```python
# rock_paper_scissors_advanced.py 수정
cap = cv2.VideoCapture(1)  # 0 대신 1, 2 등으로 변경
```

### FPS가 너무 낮아요!

```python
# 해상도 조정
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
```

### 인식이 잘 안 돼요!

1. 조명을 밝게 하세요
2. 손을 카메라 중앙에 위치시키세요
3. 손을 천천히 움직이세요
4. 배경이 복잡하지 않게 하세요

## 🎓 다음 단계

### YOLO 커스텀 모델 학습하기

더 정확한 인식을 원하신다면:

```bash
# 1. 데이터셋 다운로드
# https://universe.roboflow.com/roboflow-58fyf/rock-paper-scissors-sxsw

# 2. data.yaml 생성
python train_yolo_rps.py --create-yaml

# 3. 모델 학습
python train_yolo_rps.py --data dataset/data.yaml --epochs 100
```

### 게임 만들기

인식 시스템을 활용하여 가위바위보 게임을 만들어보세요!

```python
# game.py 예시
from rock_paper_scissors_advanced import HandGestureRecognizer
import random

# 컴퓨터의 선택
computer_choice = random.choice(['Rock', 'Paper', 'Scissors'])

# 사용자 제스처 인식
# ... (인식 코드)

# 승부 판정
# ... (게임 로직)
```

## 📚 추가 리소스

- [README_RPS.md](README_RPS.md) - 전체 문서
- [train_yolo_rps.py](train_yolo_rps.py) - 모델 학습 스크립트
- [YOLOv8 공식 문서](https://docs.ultralytics.com/)
- [MediaPipe Hands](https://google.github.io/mediapipe/solutions/hands.html)

## 💡 팁

1. **조명**: 밝은 곳에서 사용하세요
2. **배경**: 단순한 배경이 좋습니다
3. **거리**: 카메라에서 30-50cm 거리 유지
4. **안정성**: 손을 천천히 움직이세요

---

**즐거운 코딩 되세요! 🎉**
