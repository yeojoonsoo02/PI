# 객체 인식 문제 해결 요약
## 📅 2024-11-13

## 🔧 수정된 주요 문제들

### 1. **YOLO 모델 파일 문제 해결**

#### 문제점
- 코드가 두 개의 모델 파일을 찾고 있었음:
  - `sign_traffic_detector.pt`
  - `sign_traffic_classifier.pt`
- 실제로는 `best.pt` 파일 하나만 존재

#### 해결책
```python
# object_detector.py 수정
# 변경 전: 두 개의 모델 파일 검색
DETECTOR_PATH = find_model_file("sign_traffic_detector.pt")
CLASSIFIER_PATH = find_model_file("sign_traffic_classifier.pt")

# 변경 후: 단일 best.pt 파일만 사용
DETECTOR_PATH = find_model_file()  # best.pt 검색
CLASSIFIER_PATH = None  # Classifier 사용 안 함
```

### 2. **모델 파일 검색 경로 개선**

#### 추가된 검색 경로
```python
possible_paths = [
    "/home/keonha/AI_CAR/product/best.pt",  # product 디렉토리 추가
    "/home/keonha/AI_CAR/best.pt",
    "/home/keonha/best.pt",
    "/home/pi/best.pt",  # 기본 pi 사용자 경로 추가
    "/home/pi/AI_CAR/best.pt",
    # 상위 디렉토리 자동 검색 기능 추가
]
```

### 3. **클래스명 매핑 추가**

#### 문제점
- YOLO 모델의 클래스명과 shared_state의 KNOWN_OBJECTS가 일치하지 않을 수 있음

#### 해결책
```python
# 클래스명 자동 매핑 추가
name_mapping = {
    "left": "turn_left",
    "right": "turn_right",
    "straight": "go_straight",
    "stop": "stop",
    "slow": "slow",
    # ... 기타 매핑
}
sub_name = name_mapping.get(detected_name.lower(), detected_name)
```

### 4. **디버그 로그 개선**

#### 추가된 로그
- 모델 검색 과정 상세 표시
- 감지 가능한 클래스 목록 출력
- 표지판 감지 시 큐 저장 여부 명확히 표시
- 신뢰도 표시 수정 (sub_conf 사용)

### 5. **에러 처리 개선**

#### 수정사항
- 모델 파일이 없을 때 무한 대기 제거
- 스레드가 깔끔하게 종료되도록 수정
- 빈 results 처리 안전성 향상

## 📊 시스템 동작 흐름

### 정상 동작 시나리오
```
1. main.py 실행
   ↓
2. lane_tracer.py 스레드 시작 (라인 트레이싱)
   ↓
3. object_detector.py 스레드 시작 (객체 감지)
   ↓
4. best.pt 모델 자동 검색 및 로드
   ↓
5. 프레임 공유 시작 (3프레임마다)
   ↓
6. YOLO 모델이 표지판 감지
   ↓
7. 감지된 표지판을 큐에 저장
   ↓
8. 교차로 도달 시 저장된 표지판 실행
```

### 모델 파일 없을 때 동작
```
1. best.pt 파일 검색 실패
   ↓
2. 디버그 정보 출력 (현재 디렉토리, 검색 경로)
   ↓
3. detector_active = False 설정
   ↓
4. 객체 감지 스레드 종료
   ↓
5. 라인 트레이싱만 동작
```

## ✅ 검증 체크리스트

### 코드 수정 확인
- [x] object_detector.py: 단일 모델 파일 사용하도록 수정
- [x] 모델 검색 경로 확장 및 자동 검색 기능 추가
- [x] 클래스명 매핑 로직 추가
- [x] 디버그 로그 개선
- [x] 에러 처리 개선

### 배포 준비
- [x] DEPLOYMENT_GUIDE.md 작성
- [x] 카메라 오류 해결 방법 문서화
- [x] 모델 파일 전송 명령어 제공
- [x] 시스템 상태 모니터링 가이드 제공

## 🚀 다음 단계

### 라즈베리파이에서 실행
1. best.pt 파일 전송:
   ```bash
   scp /Users/yeojoonsoo02/Desktop/Python_Project/PI/best.pt keonha@[IP]:/home/keonha/AI_CAR/
   ```

2. 카메라 프로세스 정리:
   ```bash
   sudo fuser -k /dev/video0
   ```

3. 프로그램 실행:
   ```bash
   cd /home/keonha/AI_CAR/product
   sudo python3 main.py
   ```

### 모니터링할 로그
- "모델 파일 발견: /home/keonha/AI_CAR/best.pt" ✅
- "YOLO 모델 로드 완료" ✅
- "감지 가능한 객체 클래스: ..." ✅
- "🎯 [객체 감지]" 메시지 ✅

## 💡 추가 개선 사항 (선택적)

1. **프레임 동기화 최적화**
   - lane_tracer와 object_detector의 프레임 처리 간격 동기화

2. **ROI 확장**
   - 현재 오른쪽 절반만 스캔 → 전체 프레임으로 확장 가능

3. **신뢰도 임계값 조정**
   - CONF_THRESHOLD 값을 환경에 맞게 조정

4. **메모리 최적화**
   - 오래된 감지 데이터 자동 정리 기능 추가