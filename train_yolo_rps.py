"""
YOLO 가위바위보 커스텀 모델 학습 스크립트

사용법:
    python train_yolo_rps.py --data dataset/data.yaml --epochs 100
"""

import argparse
from ultralytics import YOLO
from pathlib import Path


def create_data_yaml(output_path='data.yaml'):
    """
    YOLO 학습용 data.yaml 파일 생성 예시

    Args:
        output_path: 출력 파일 경로
    """
    yaml_content = """# Rock Paper Scissors Dataset Configuration

# 경로 설정
path: ../dataset  # dataset root dir
train: train/images  # train images (relative to 'path')
val: valid/images  # val images (relative to 'path')
test: test/images  # test images (optional)

# 클래스 정의
names:
  0: Rock      # 주먹
  1: Paper     # 보
  2: Scissors  # 가위

# 클래스 개수
nc: 3
"""

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(yaml_content)

    print(f"[INFO] data.yaml 템플릿 생성: {output_path}")
    print("[INFO] 실제 데이터셋 경로에 맞게 수정하세요!")


def train_yolo_model(
    data_yaml='data.yaml',
    model='yolov8n.pt',
    epochs=100,
    imgsz=640,
    batch=16,
    device='mps'  # macOS GPU 가속
):
    """
    YOLO 모델 학습

    Args:
        data_yaml: 데이터셋 설정 파일
        model: 사전 학습 모델 (yolov8n.pt, yolov8s.pt, yolov8m.pt 등)
        epochs: 학습 에포크 수
        imgsz: 입력 이미지 크기
        batch: 배치 크기
        device: 학습 디바이스 ('mps', 'cpu', 'cuda')
    """
    print("=" * 70)
    print("YOLO 가위바위보 모델 학습 시작")
    print("=" * 70)

    # 데이터 파일 존재 확인
    if not Path(data_yaml).exists():
        print(f"[WARNING] {data_yaml} 파일이 없습니다.")
        print("[INFO] 템플릿 생성 중...")
        create_data_yaml(data_yaml)
        print("[ERROR] data.yaml 파일을 수정한 후 다시 실행하세요!")
        return

    # 모델 로드
    print(f"\n[INFO] 모델 로드: {model}")
    yolo_model = YOLO(model)

    # 학습 파라미터 출력
    print(f"\n[학습 설정]")
    print(f"  - 데이터: {data_yaml}")
    print(f"  - 에포크: {epochs}")
    print(f"  - 이미지 크기: {imgsz}")
    print(f"  - 배치 크기: {batch}")
    print(f"  - 디바이스: {device}")
    print()

    try:
        # 학습 시작
        results = yolo_model.train(
            data=data_yaml,
            epochs=epochs,
            imgsz=imgsz,
            batch=batch,
            device=device,
            project='runs/detect',
            name='rps_train',
            exist_ok=True,
            pretrained=True,
            optimizer='Adam',
            verbose=True,
            patience=20,  # Early stopping
            save=True,
            plots=True,
            # 데이터 증강
            hsv_h=0.015,  # 색상 변화
            hsv_s=0.7,    # 채도 변화
            hsv_v=0.4,    # 명도 변화
            degrees=10,   # 회전
            translate=0.1,  # 이동
            scale=0.5,    # 스케일
            flipud=0.0,   # 상하 반전 (손은 보통 안 함)
            fliplr=0.5,   # 좌우 반전
            mosaic=1.0    # 모자이크 증강
        )

        print("\n" + "=" * 70)
        print("학습 완료!")
        print("=" * 70)
        print(f"\n[결과 저장 위치]")
        print(f"  - 모델: runs/detect/rps_train/weights/best.pt")
        print(f"  - 로그: runs/detect/rps_train/")
        print()

        # 모델 검증
        print("[INFO] 모델 검증 중...")
        metrics = yolo_model.val()

        print(f"\n[성능 지표]")
        print(f"  - mAP50: {metrics.box.map50:.3f}")
        print(f"  - mAP50-95: {metrics.box.map:.3f}")
        print()

        print("[INFO] 학습된 모델 사용법:")
        print(f"  detector = RockPaperScissorsDetector(")
        print(f"      model_path='runs/detect/rps_train/weights/best.pt'")
        print(f"  )")

    except Exception as e:
        print(f"\n[ERROR] 학습 중 오류 발생: {e}")
        print("\n[해결 방법]")
        print("1. 데이터셋 경로가 올바른지 확인")
        print("2. 이미지와 라벨 파일이 모두 존재하는지 확인")
        print("3. data.yaml 파일 내용이 올바른지 확인")
        print("4. 디바이스 설정 확인 (macOS: 'mps', NVIDIA: 'cuda', CPU: 'cpu')")


def export_model(model_path='runs/detect/rps_train/weights/best.pt'):
    """
    학습된 모델을 다양한 형식으로 내보내기

    Args:
        model_path: 학습된 모델 경로
    """
    print(f"\n[INFO] 모델 내보내기: {model_path}")

    model = YOLO(model_path)

    # ONNX 형식으로 내보내기 (배포용)
    print("[INFO] ONNX 형식으로 변환 중...")
    model.export(format='onnx')

    # TensorFlow Lite 형식 (모바일용)
    print("[INFO] TFLite 형식으로 변환 중...")
    try:
        model.export(format='tflite')
    except Exception as e:
        print(f"[WARNING] TFLite 변환 실패: {e}")

    print("[INFO] 모델 내보내기 완료!")


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description='YOLO 가위바위보 모델 학습 스크립트'
    )

    parser.add_argument(
        '--data',
        type=str,
        default='data.yaml',
        help='데이터셋 설정 파일 경로 (default: data.yaml)'
    )

    parser.add_argument(
        '--model',
        type=str,
        default='yolov8n.pt',
        help='사전 학습 모델 (yolov8n/s/m/l/x.pt) (default: yolov8n.pt)'
    )

    parser.add_argument(
        '--epochs',
        type=int,
        default=100,
        help='학습 에포크 수 (default: 100)'
    )

    parser.add_argument(
        '--imgsz',
        type=int,
        default=640,
        help='입력 이미지 크기 (default: 640)'
    )

    parser.add_argument(
        '--batch',
        type=int,
        default=16,
        help='배치 크기 (default: 16)'
    )

    parser.add_argument(
        '--device',
        type=str,
        default='mps',
        help='학습 디바이스 (mps/cpu/cuda) (default: mps for macOS)'
    )

    parser.add_argument(
        '--create-yaml',
        action='store_true',
        help='data.yaml 템플릿만 생성'
    )

    parser.add_argument(
        '--export',
        type=str,
        help='학습된 모델 내보내기 (모델 경로 지정)'
    )

    args = parser.parse_args()

    # data.yaml 템플릿만 생성
    if args.create_yaml:
        create_data_yaml(args.data)
        return

    # 모델 내보내기
    if args.export:
        export_model(args.export)
        return

    # 모델 학습
    train_yolo_model(
        data_yaml=args.data,
        model=args.model,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device
    )


if __name__ == "__main__":
    main()
