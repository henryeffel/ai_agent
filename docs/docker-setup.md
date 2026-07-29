# IEUM Docker 설치 및 검증 준비

기준일: 2026-07-28

## 목적과 범위

Docker는 IEUM의 배포 구성을 확장하기 위한 작업이 아니라 다음 구현을 실제 환경에서 검증하기 위한 최소 수단으로 사용한다.

- FastAPI Backend 실행
- PostgreSQL + pgvector 실행
- `CREATE EXTENSION IF NOT EXISTS vector` 검증
- NVIDIA Embedding과 동일한 2,048차원 Vector 저장·검색
- PostgreSQL 조건부 상태 변경과 unique constraint 검증
- 동시 요청 시 동일 Action의 외부 호출 1회 검증

P0에서는 Frontend를 컨테이너화하지 않는다. Frontend는 로컬에서 `npm run dev`로 실행한다.

## 사용자가 해야 할 작업

### 1. Windows와 WSL 상태 확인

일반 PowerShell에서 실행한다.

```powershell
winver
wsl --status
wsl --version
wsl -l -v
```

WSL이 설치되지 않았다면 관리자 PowerShell에서 다음을 실행하고 Windows를 재시작한다.

```powershell
wsl --install
```

설치된 Linux 배포판의 `VERSION`이 1이라면 WSL 2로 변경한다.

```powershell
wsl --set-version Ubuntu 2
wsl --set-default-version 2
```

배포판 이름이 Ubuntu가 아니라면 `wsl -l -v`에 표시된 정확한 이름을 사용한다.

### 2. Docker Desktop 설치

WinGet으로 설치할 수 있다.

```powershell
winget install --exact --id Docker.DockerDesktop --accept-package-agreements --accept-source-agreements
```

패키지를 먼저 확인하려면 다음을 실행한다.

```powershell
winget search --exact --id Docker.DockerDesktop
```

WinGet이 없거나 설치가 실패하면 Docker 공식 Windows 설치 페이지에서 Docker Desktop을 내려받아 설치한다. 설치 설정에서는 WSL 2 backend를 사용한다.

### 3. Docker Desktop 최초 실행

설치 후 Docker Desktop을 직접 한 번 실행한다.

- 이용 약관을 확인하고 동의한다.
- Settings에서 WSL 2 기반 엔진 사용 여부를 확인한다.
- Docker Engine이 시작될 때까지 기다린다.
- 설치 과정에서 요청하면 Windows를 재시작한다.

### 4. 설치 결과 확인

새 PowerShell 창에서 실행한다.

```powershell
docker --version
docker compose version
docker info
docker run --rm hello-world
```

`docker info`와 `hello-world`가 성공하면 IEUM 컨테이너 구현 및 실제 통합 검증을 진행할 수 있다.

## 설치 후 전달할 결과

다음 명령의 출력 또는 오류 내용을 Codex에 전달한다.

```powershell
wsl --version
wsl -l -v
docker --version
docker compose version
docker info
```

API 키나 `.env` 내용은 전달하지 않는다.

## 현재 설치 체크포인트

기준 시각: 2026-07-28

확인된 설치 버전:

```text
Docker Engine CLI: 29.6.2
Docker Compose:     v5.3.1
WSL:                2.7.11.0
WSL Kernel:         6.18.33.2-2
Windows:            10.0.19045.6466
```

Docker Desktop 설치 경로:

```text
C:\Program Files\Docker\Docker
```

Docker CLI 경로:

```text
C:\Program Files\Docker\Docker\resources\bin
```

설치 직후 열려 있던 PowerShell에서는 PATH가 갱신되지 않아 다음 명령으로 현재 세션 PATH를 임시 갱신했다.

```powershell
$env:Path += ";C:\Program Files\Docker\Docker\resources\bin"
```

Windows 재부팅 후 새 PowerShell에서는 시스템 PATH가 적용되므로 위 임시 명령 없이 `docker`가 실행돼야 한다.

### 확인된 중단 원인

Docker Desktop 애플리케이션 프로세스는 실행됐지만 Engine 상태는 `stopped`였다.

WSL 확인 결과:

```text
Wsl/WSL_E_WSL_OPTIONAL_COMPONENT_REQUIRED
```

Docker Desktop 오류 로그:

```text
starting grpcfuse fileserver:listening on vsock:4099:
listening on vsock:4099: A socket operation encountered a dead network.
```

판단:

- 최신 WSL 패키지는 설치됐다.
- Linux용 Windows 하위 시스템 선택적 구성 요소 적용에는 Windows 재부팅이 필요하다.
- 선택적 구성 요소가 적용되지 않아 Docker의 WSL 가상 네트워크와 Engine이 시작되지 않았다.
- 아직 Docker 데이터 초기화나 Factory Reset은 수행하지 않았다.

### 재부팅 후 검증 순서

새 PowerShell에서 다음 순서로 실행한다.

```powershell
wsl --version
wsl -l -v
docker --version
docker compose version
docker desktop start
docker desktop status
docker info
docker run --rm hello-world
```

정상 완료 조건:

```text
docker desktop status → running
docker info           → Client와 Server 정보 표시
hello-world           → "Hello from Docker!" 출력
```

Engine이 계속 중지되면 다음 로그를 수집한다.

```powershell
docker desktop logs --priority 2 | Select-Object -Last 50
```

### 정상화 후 바로 진행할 개발 작업

1. Backend Dockerfile
2. `.dockerignore`
3. PostgreSQL/pgvector Compose
4. DB health check 이후 Backend 시작
5. vector extension 및 2,048차원 저장·검색 검증
6. PostgreSQL 동시 요청과 동일 Action 외부 호출 1회 검증
7. 전체 Meeting-to-Action 통합 테스트

## P0에서 제외하는 작업

- Frontend Dockerfile
- Nginx
- Kubernetes
- Docker Swarm
- NVIDIA NIM 자체 컨테이너 호스팅
- Azure Container Apps 배포
- 복잡한 multi-stage 이미지 최적화
- Production 수준의 보안 및 고가용성 Compose
