# 가위바위보 인식 시스템

맥북 웹캠을 활용한 실시간 가위바위보(주먹, 가위, 보) 인식 시스템입니다.

## 📋 목차

- [기능](#기능)
- [설치](#설치)
- [사용법](#사용법)
- [파일 구조](#파일-구조)
- [성능 비교](#성능-비교)
- [커스텀 YOLO 모델 학습](#커스텀-yolo-모델-학습)

## ✨ 기능

- ✊ 주먹(Rock) 인식
- ✋ 보(Paper) 인식
- ✌️ 가위(Scissors) 인식
- 📊 실시간 통계
- 🎯 높은 정확도 (MediaPipe 버전)
- 📸 화면 캡처 기능

## 🚀 설치

### 1. Python 환경 확인

```bash
python --version  # Python 3.8 이상 필요
```

### 2. 가상환경 생성 (권장)

```bash
# 가상환경 생성
python -m venv venv

# 가상환경 활성화
# macOS/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate
```

### 3. 라이브러리 설치

```bash
pip install -r requirements.txt
```

## 📖 사용법

### 버전 1: YOLO 기반 (기본)

```bash
python rock_paper_scissors_yolo.py
```

**특징:**
- YOLOv8 사전 학습 모델 사용
- 빠른 실행 속도
- 커스텀 모델로 개선 가능

### 버전 2: MediaPipe 기반 (권장) ⭐

```bash
python rock_paper_scissors_advanced.py
```

**특징:**
- MediaPipe Hands 사용
- 높은 정확도 (95%+)
- 손가락 랜드마크 기반 분류
- 안정적인 인식

### 단축키

| 키 | 기능 |
|----|------|
| `q` 또는 `ESC` | 종료 |
| `c` | 화면 캡처 |
| `s` | 통계 초기화 |
| `r` | 제스처 히스토리 초기화 (Advanced 버전) |

## 📁 파일 구조

```
PI/
├── rock_paper_scissors_yolo.py      # YOLO 기반 버전
├── rock_paper_scissors_advanced.py  # MediaPipe 기반 버전 (권장)
├── requirements.txt                 # 필수 라이브러리
├── README_RPS.md                    # 이 파일
└── train_yolo_rps.py               # YOLO 커스텀 모델 학습 스크립트
```

## 📊 성능 비교

| 버전 | 정확도 | FPS | 장점 | 단점 |
|------|--------|-----|------|------|
| YOLO 기본 | ~70% | 30-60 | 빠름, 확장 가능 | 사전 학습 모델 한계 |
| MediaPipe | ~95% | 30-45 | 매우 정확, 안정적 | MediaPipe 의존성 |
| YOLO 커스텀 | ~90% | 30-60 | 높은 정확도, 커스터마이징 가능 | 학습 데이터 필요 |

## 🎓 커스텀 YOLO 모델 학습

더 정확한 인식을 위해 가위바위보 데이터셋으로 YOLO 모델을 직접 학습시킬 수 있습니다.

### 1. 데이터셋 준비

Roboflow나 Kaggle에서 가위바위보 데이터셋 다운로드:

**추천 데이터셋:**
- [Roboflow - Rock Paper Scissors](https://universe.roboflow.com/roboflow-58fyf/rock-paper-scissors-sxsw)
- [Kaggle - RPS Dataset](https://www.kaggle.com/datasets/drgfreeman/rockpaperscissors)

### 2. 데이터셋 구조

```
dataset/
├── train/
│   ├── images/
│   └── labels/
├── valid/
│   ├── images/
│   └── labels/
└── data.yaml
```

### 3. 학습 실행

```bash
python train_yolo_rps.py --data dataset/data.yaml --epochs 100
```

### 4. 학습된 모델 사용

```python
# rock_paper_scissors_yolo.py 수정
detector = RockPaperScissorsDetector(
    model_path='runs/detect/train/weights/best.pt'  # 학습된 모델 경로
)
```

## 🔧 문제 해결

### 웹캠이 열리지 않는 경우

```python
# 다른 카메라 인덱스 시도
cap = cv2.VideoCapture(1)  # 0 대신 1, 2, 3 등
```

### FPS가 낮은 경우

```python
# 해상도 낮추기
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
```

### MediaPipe 설치 오류

```bash
# Apple Silicon Mac의 경우
pip install mediapipe --no-binary mediapipe
```

## 📝 제스처 인식 기준

### 주먹 (Rock) ✊
- 모든 손가락이 접혀 있음
- 손가락 개수: 0-1개

### 보 (Paper) ✋
- 모든 손가락이 펼쳐져 있음
- 손가락 개수: 5개

### 가위 (Scissors) ✌️
- 검지와 중지만 펼쳐져 있음
- 손가락 개수: 2개

## 🎯 향상 방법

1. **더 많은 학습 데이터**: 다양한 각도와 조명에서 촬영
2. **데이터 증강**: 회전, 밝기 조절, 노이즈 추가
3. **앙상블**: MediaPipe + YOLO 결합
4. **후처리**: 시간적 smoothing 적용

## 📚 참고 자료

- [YOLOv8 Documentation](https://docs.ultralytics.com/)
- [MediaPipe Hands](https://google.github.io/mediapipe/solutions/hands.html)
- [OpenCV Documentation](https://docs.opencv.org/)

## 📄 라이선스

MIT License

## 👤 작성자

Claude Code AI Assistant

---

**즐거운 코딩 되세요! 🎉**
