# 카메라 테스트 완료 요약 📹

## 생성된 파일들

### 1. 테스트 스크립트
- **`test_camera_roi.py`** - 카메라 및 ROI 색상 구분 테스트
- **`run_test.sh`** - 테스트 실행 스크립트 (Linux/Mac)

### 2. 메인 코드
- **`dual_roi_line_tracer.py`** - Dual ROI 라인 트레이싱 코드

### 3. 문서
- **`TEST_GUIDE.md`** - 상세 테스트 가이드
- **`README_LINE_TRACER.md`** - 라인 트레이싱 사용 설명서

## 빠른 시작

### Step 1: 카메라 테스트
```bash
# 방법 1: 스크립트로 실행
./run_test.sh

# 방법 2: 직접 실행
python test_camera_roi.py
```

### Step 2: 확인 사항

#### ✅ 카메라 방향 확인
6개의 창이 열립니다:
- Camera Test - Main (메인 화면)
- Left ROI (Original) (좌측 원본)
- Right ROI (Original) (우측 원본)
- Left ROI (Binary) (좌측 이진화)
- Right ROI (Binary) (우측 이진화)

**키 조작:**
- `f`: 상하 반전
- `h`: 좌우 반전
- `r`: 180도 회전
- `n`: 원본 복원

**확인:** 화면이 정상적으로 보이는 flip 모드를 찾으세요!

#### ✅ 색상 구분 확인

메인 화면에 표시되는 정보:
```
Left Pixels: XXXX      ← 좌측 라인 픽셀 수
Right Pixels: XXXX     ← 우측 라인 픽셀 수
Left Brightness: XX.X  ← 좌측 평균 밝기
Right Brightness: XX.X ← 우측 평균 밝기
```

**테스트 방법:**
1. 라인 위에 카메라를 두세요
2. Binary 창에서 라인이 흰색으로 보이는지 확인
3. Pixels 값이 충분히 큰지 확인 (500 이상 권장)

**임계값 조정:**
- `1`: 임계값 낮춤 (더 어두운 선도 감지)
- `2`: 임계값 높임 (밝은 선만 감지)

### Step 3: ROI 위치 확인

메인 화면에서:
- **파란색 박스** = 좌측 ROI (LEFT ROI)
- **초록색 박스** = 우측 ROI (RIGHT ROI)
- **노란색 선** = 화면 중앙선

**확인:** 두 ROI가 트랙의 양쪽 라인을 포함하는지 확인하세요!

## 테스트 결과 해석

### 정상 동작 예시

#### 🟢 라인 위 (양쪽 라인 모두 있음)
```
Left Pixels: 850
Right Pixels: 920
Command: FORWARD
```
→ **직진**

#### 🔵 좌측 라인 이탈
```
Left Pixels: 50
Right Pixels: 900
Command: LEFT
```
→ **좌회전 (라인 복귀)**

#### 🟢 우측 라인 이탈
```
Left Pixels: 880
Right Pixels: 45
Command: RIGHT
```
→ **우회전 (라인 복귀)**

#### 🔴 완전 이탈
```
Left Pixels: 30
Right Pixels: 25
Command: STOP
```
→ **정지**

## 다음 단계

### 카메라 방향이 거꾸로인 경우

`dual_roi_line_tracer.py` 파일의 243번째 줄 근처에서:

```python
ret, frame = cap.read()
if not ret:
    break

# ⬇️ 여기에 추가 ⬇️
frame = cv2.flip(frame, -1)  # 180도 회전
# 또는
# frame = cv2.flip(frame, 0)  # 상하 반전
# frame = cv2.flip(frame, 1)  # 좌우 반전
```

### 임계값 설정

테스트에서 찾은 최적 임계값을 메인 코드에 적용:

```python
# dual_roi_line_tracer.py의 237번째 줄
thresh = 150  # 테스트에서 찾은 값으로 변경
```

### ROI 크기 조정

트랙에 맞게 ROI 크기 조정:

```python
# dual_roi_line_tracer.py의 235-236번째 줄
roi_height_ratio = 0.3  # 트랙에 맞게 조정
roi_width_ratio = 0.3   # 트랙에 맞게 조정
```

## 메인 라인 트레이싱 실행

테스트가 완료되면 메인 코드를 실행:

```bash
python dual_roi_line_tracer.py
```

**실시간 조정 키:**
- `1/2`: 임계값 조정
- `3/4`: ROI 높이 조정
- `5/6`: ROI 너비 조정
- `7/8`: 최소 픽셀 수 조정
- `q/ESC`: 종료

## 트러블슈팅

### 문제: 카메라가 열리지 않음
```
[ERROR] 카메라를 열 수 없습니다.
```
**해결:**
- 카메라가 연결되어 있는지 확인
- 다른 프로그램에서 카메라를 사용중인지 확인
- 권한 문제 확인 (Mac: 시스템 환경설정 > 보안 및 개인정보 보호)

### 문제: 라인이 감지되지 않음
```
Left Pixels: 5
Right Pixels: 8
```
**해결:**
1. `1` 키를 여러 번 눌러 임계값 낮춤
2. Binary 창에서 라인이 흰색으로 나타날 때까지 조정
3. 조명 환경 개선 (더 밝게 또는 어둡게)

### 문제: 너무 많이 감지됨
```
Left Pixels: 15000
Right Pixels: 14500
```
**해결:**
1. `2` 키를 여러 번 눌러 임계값 높임
2. Binary 창에서 라인만 흰색으로 나타날 때까지 조정

## 성공 체크리스트

테스트 완료 전 확인:

- [ ] 카메라가 정상적으로 열림
- [ ] 화면 방향이 올바름 (필요시 flip 적용)
- [ ] 좌측 ROI가 좌측 라인을 감지함
- [ ] 우측 ROI가 우측 라인을 감지함
- [ ] Binary 이미지에서 라인만 흰색으로 보임
- [ ] 임계값이 적절히 조정됨
- [ ] Pixels 값이 라인 있을 때 500 이상
- [ ] Pixels 값이 라인 없을 때 100 이하

모두 체크되면 메인 라인 트레이싱을 실행할 준비 완료! 🎉

## 추가 정보

자세한 내용은 다음 문서를 참조하세요:
- **TEST_GUIDE.md** - 상세 테스트 가이드
- **README_LINE_TRACER.md** - 라인 트레이싱 전체 설명서
