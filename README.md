# SmartAutoTrade

# 🎯 Automated Trading Project — Team Development Guide

이 문서는 팀원이 **로컬 PC에서 개발을 시작하고(main 브랜치 클론)**,  
**PR을 통해 협업**하며,  
**EC2 서버에 배포되는 전체 흐름**을 정리한 공식 가이드입니다.

---

# 🧩 1. Repository Structure

teamrepo/
 ┣ apps/
 ┃ ┣ base/      # 공통 웹 페이지 (메인/네비게이션)
 ┃ ┣ m1/        # Market Analysis
 ┃ ┣ m2/        # Option Skew Analysis (Jaehyun)
 ┃ ┣ m3/        # Risk Management
 ┃ ┗ api/       # FastAPI (공용 데이터 API)
 ┗ nginx/       # Reverse Proxy 설정

각 폴더는 개별 Docker Compose 서비스로 실행됩니다.

---

# 🍀 2. Clone & Local Development

## 2-1) 프로젝트 클론
git clone https://github.com/won0201/SmartAutoTrade.git teamrepo
cd teamrepo

## 2-2) 자신의 작업용 브랜치 생성
git checkout -b feature/<branch-name>

예시:
- feature/market-dashboard
- feature/option-skew
- feature/risk-monitor

---

# 🐳 3. Running Services in Local (Docker)

## 3-1) 개별 모듈 실행 예시 — m2

cd apps/m2
docker compose up -d --build

## 3-2) 포트 충돌 시 (로컬에서만)

# docker-compose.yml
ports:
  - "7202:7102"   # 로컬 PC에서는 7202로 열기

## 3-3) 로그 보기
docker compose logs -f --tail=100

---

# 🧪 4. 로컬 개발 절차

1. apps/m2에서 코드 수정(각자 해당 폴더)
2. 테스트 (브라우저에서 확인)  
3. 변경사항 커밋  
4. 본인 브랜치에 push  

git add .
git commit -m "feat(m2): add skew chart"
git push origin feature/<branch-name>

---

# 🔀 5. GitHub Pull Request Workflow

1. GitHub에서 feature → main PR 생성  
2. 리뷰 & 승인  
3. main에 merge  
4. merge 후 main은 최신 코드가 됨

⚠️ 팀 규칙: main 브랜치에 직접 push 금지  

---

# 🚀 6. Deployment to EC2 (Server)

EC2에는 다음 디렉토리 구조가 있음:

/srv/teamrepo   # 깃허브 원본
/srv/apps       # 실제 Docker 실행 경로

## 6-1) main 최신화

cd /srv/teamrepo
git pull origin main

## 6-2) teamrepo → apps 동기화

rsync -av --delete \
  --exclude=".git" --exclude=".github" \
  --exclude="**/__pycache__" --exclude="**/.venv" \
  --exclude="**/.env" \
  /srv/teamrepo/apps/ /srv/apps/

## 6-3) 컨테이너 재배포 (예: m2)

cd /srv/apps/m2
docker compose down || true
docker compose up -d --build
docker compose logs -f --tail=100

---

# 📡 7. API Communication

웹 모듈은 FastAPI(api)에서 받은 JSON 데이터를 활용합니다.

fetch("http://<SERVER_IP>:8000/ivskew/latest")
  .then(res => res.json())
  .then(data => console.log(data));

---

# 🗂 8. Commit Message Convention

| 타입 | 설명 |
|------|------|
| feat | 새로운 기능 |
| fix | 버그 수정 |
| chore | 설정/환경 변경 |
| docs | 문서 작업 |
| refactor | 구조 개선 |

예:
git commit -m "feat(m3): add VaR visualization"

---

# 👥 9. Team Roles

Member 1 | Market Analysis | 시장 지표 수집 & 시각화
Jaehyun | Option Skew Analysis | 옵션 스큐 분석 & 웹 모듈(m2) 구성
Member 3 | Risk Management | 리스크 관리 및 자동매매 연결

---

# 🔐 10. Branch Protection (팀장 설정 권장)

GitHub → Settings → Branches → Add Protection Rule

- Require pull request before merging  
- Require 1 approving review  
- Restrict direct pushes  
- Include administrators (optional)

---

# 🎉 11. Summary Workflow

(팀원 로컬)
git clone https://github.com/won0201/SmartAutoTrade.git
git checkout -b feature/<name>
docker compose up
개발
git push

  ↓ PR

(main merge)

  ↓

(EC2 서버)
/srv/teamrepo git pull
rsync teamrepo/apps → apps
docker compose up -d
