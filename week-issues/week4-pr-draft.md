# Week 4 PR 초안 (복사용)

## PR 열기 (브랜치 이미 푸시됨)

**Compare & PR 생성 URL:**  
https://github.com/kocory1/AutoPolio/compare/main...week4/auth-tdd-wip?expand=1

Base: `main` ← Head: `week4/auth-tdd-wip`

---

## 제목

```
Week 4: GitHub OAuth + Git Trees 파일 트리 + selected assets + 대시보드
```

---

## 본문

```markdown
## Summary
- GitHub OAuth·세션 기반 인증 및 `/api/me`.
- **파일 트리** `GET /api/github/repos/{repo_id}/files`: Git **Trees API** (`recursive=1`) 사용, `traverse_cap`/`capped` 없이 필터 결과 전체 반환. GitHub `truncated=true` 시 502.
- 대시보드: 트리 선택·`selected_repo_assets` 저장/복원·저장된 파일 기준 contents 재선택. HTML은 `src/web/dashboard.py`.
- OpenAPI·`docs/API_GitHub_Spec.md` 동기화.

## 구현된 API 목록

### Auth (`src/api/auth.py`)
| Method | Path |
|--------|------|
| GET | `/api/auth/github/login` |
| GET | `/api/auth/github/callback` |
| GET | `/api/auth/logout` |
| GET | `/api/me` |

### GitHub + 선택 레포 (`src/api/github.py`)
| Method | Path |
|--------|------|
| GET | `/api/github/repos` |
| GET | `/api/user/selected-repos` |
| PUT | `/api/user/selected-repos` |
| GET | `/api/github/repos/{repo_id}/files` |
| GET | `/api/github/repos/{repo_id}/contents` |
| GET | `/api/github/repos/{repo_id}/commits` |

### User — 선택 assets (`src/api/user_assets.py`)
| Method | Path |
|--------|------|
| GET | `/api/user/selected-repo-assets?selected_repo_id=...` |
| PUT | `/api/user/selected-repo-assets` |

### Portfolio (`src/api/portfolio.py`)
| Method | Path |
|--------|------|
| POST | `/api/portfolio/generate` (header `X-User-Id`) |
| GET | `/api/portfolio` (header `X-User-Id`, optional `portfolio_id`) |

### 기타
| Method | Path |
|--------|------|
| GET | `/` |
| GET | `/dashboard` |

## How to test
```bash
poetry run pytest -q
poetry run uvicorn src.app.main:app --reload --host 127.0.0.1 --port 8000
# 브라우저: http://127.0.0.1:8000/dashboard
```

## Notes
- 이전 PR을 닫은 뒤 **Git Trees 전환 + traverse_cap 제거** 등 후속 수정까지 이 브랜치에 포함.
- 상세 이슈: `week-issues/week4-github.md`
```
