# Autofolio

**From Code to Career** – 증거 기반 개발자 이력서

## 개발 환경 (Poetry)

프로젝트 공통 가상환경은 Poetry로 관리합니다.

```bash
# 의존성 설치 및 가상환경 생성
poetry install

# 스크립트 실행 (가상환경 활성화 후)
poetry run python scripts/jobkorea_collect_urls.py

# 또는 셸에서 가상환경 활성화 후
poetry shell
python scripts/jobkorea_collect_urls.py
```

## 문서

- [기획서](docs/AUTOFOLIO_기획서.md)
- [파이프라인](docs/AUTOFOLIO_파이프라인.md)
- [자기소개서 크롤링 전략](docs/AUTOFOLIO_자기소개서크롤링전략.md)
- [저장 전략 (크롤링)](scripts/README_저장전략.md)
