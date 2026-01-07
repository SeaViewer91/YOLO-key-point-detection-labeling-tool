# YOLO Keypoint Labeling Tool

Python 및 Tkinter 기반의 YOLO Keypoint Detection 라벨링 도구. Ultralytics YOLO 형식의 데이터셋 생성 지원.

## 1. 설치 및 실행

### 요구 사항
- Python 3.x
- `Pillow` 라이브러리

### 실행 순서
터미널(CMD 또는 PowerShell)에서 다음 명령어 실행.

```bash
# 1. 프로젝트 폴더 이동
cd e:\key-point-labeling

# 2. 의존성 설치
pip install -r requirements.txt

# 3. 프로그램 실행
python labeling_tool.py
```

---

## 2. 기능 및 사용법

### 시작
- 상단 **[Open Dir]** 버튼 클릭 후 이미지 폴더 선택.

### 이미지 탐색
- **이동**: UI 상단 `<< Prev`, `Next >>` 버튼 또는 키보드 `방향키 ←`, `→` 사용.
- **저장**: 이미지 이동 시 자동 저장됨. `Ctrl + S` 또는 `Save` 버튼으로 수동 저장 가능.

### 뷰 컨트롤 (Zoom & Pan)
- **확대/축소 (Zoom)**: 마우스 휠 스크롤 (커서 중심).
- **이동 (Pan)**: 마우스 **휠 버튼(Middle Click)** 누른 상태로 드래그.

### 라벨링 (Labeling)
1. **박스 생성**: 빈 공간에서 `마우스 왼쪽 버튼` 드래그하여 Bounding Box 생성.
2. **객체 선택**: 생성된 박스 클릭 시 **청록색(Cyan)**으로 활성화.
3. **키포인트 추가**: 객체 선택 상태에서 키포인트 위치에 `마우스 오른쪽 버튼` 클릭 (순차적 번호 부여).
4. **키포인트 삭제**: `Backspace` 입력 시 마지막 키포인트 삭제.
5. **객체 삭제**: 객체 선택 후 `Delete` 입력 시 박스 및 포함된 키포인트 일괄 삭제.

### 클래스 설정
- 상단 툴바 **Class ID** 입력창에서 클래스 인덱스 변경 가능 (기본값: 0).

---

## 3. 결과물 저장 형식

이미지 경로와 동일한 위치에 같은 파일명의 `.txt` 파일 생성. **Ultralytics YOLO Pose** 형식 준수.

**데이터 포맷:**
```text
<class-index> <x> <y> <width> <height> <px1> <py1> <vis1> <px2> <py2> <vis2> ...
```

- **좌표**: 이미지 크기 대비 0~1 사이로 정규화(Normalized)된 값.
- **Visibility**:
  - `2`: Visible (보임)
  - 생성된 모든 키포인트는 기본값 `2`로 저장됨.
