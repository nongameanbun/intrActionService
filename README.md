# nongameanbun - intrAction

## 프로젝트 구조
```text
.
├── main.py # 인터럽트 관리 API 라우터 및 메인 로직
├── gateway.py # 타 마이크로서비스 API 연동을 위한 게이트웨이
├── env.example # 환경 변수 예시 파일
├── interruptions.py # 인터럽트 종류 등록 및 매핑
└── interruption # 각종 인터럽트 핸들러 모듈 
    ├── base.py # 인터럽트 기본 클래스
    ├── booster.py # 거탐(booster) 인터럽트
    ├── dead.py # 비석(dead) 인터럽트
    ├── liecheck.py # 진실의 방(liecheck) 인터럽트
    ├── myster.py # 의문의 모루(myster) 인터럽트
    ├── shape.py # 도형(shape) 인터럽트
    └── viol.py # 폭력(viol) 인터럽트
```

## 사전 요구 사항

### 환경 변수 세팅 (`.env`)
환경에 맞게 각 포트 번호를 지정하여 프로젝트 루트에 `.env` 파일을 생성합니다.

```powershell
Copy-Item env.example .env
```

`env.example` 포맷 예시:
```ini
RUNE_SOLVER_PORT=8020
inputHandler_API_PORT=8001
statusChecker_API_PORT=8002
alarmHandler_API_PORT=8003
intrAction_API_PORT=8004
mainAction_API_PORT=8005
subaction_API_PORT=8006
streaning_API_PORT=8007
objectDetector_API_PORT=8008
agentServer_API_PORT=8009
```

## 실행 방법

```bash
pip install -r requirements.txt
python main.py
```

`localhost:8004/docs` 로 swagger 명세를 확인 가능
1