# 합격 자소서 크롤링 저장 전략

의존성은 프로젝트 루트 `pyproject.toml` (Poetry)에 포함되어 있습니다. `poetry install` 후 실행하세요.

## 2단계 저장

| 단계 | 목적 | 출력 |
|------|------|------|
| **1단계** | 리스트 페이지에서 상세 URL만 수집 | `data/jobkorea_urls.json` |
| **2단계** | 수집한 URL 순회하며 상세 페이지 크롤링 | `data/jobkorea/{id}.json` (문서당 1개) |

---

## 1단계: URL 목록 (JSON)

**파일**: `data/jobkorea_urls.json`

**형식**: 처음부터 JSON 배열로 저장. 나중에 2단계에서 "어디까지 수집했는지" 체크·재개할 수 있음.

```json
[
  {
    "id": "199325",
    "url": "https://www.jobkorea.co.kr/starter/PassAssay/View/199325?Page=10&OrderBy=0&FavorCo_Stat=0&schPart=10031&Pass_An_Stat=0"
  },
  {
    "id": "199326",
    "url": "https://..."
  }
]
```

**이렇게 하는 이유:**
- `id`만 있으면 2단계에서 `data/jobkorea/{id}.json` 존재 여부로 스킵 가능 (재실행 시 이어하기)
- 리스트에서 미리 보이는 회사명/직무를 넣고 싶으면 `company_preview`, `position_preview` 같은 필드 추가 가능 (선택)
- 한 파일에 모아두면 URL 목록 관리·개수 확인이 쉬움

---

## 2단계: 상세 문서 (문서당 JSON)

**디렉터리**: `data/jobkorea/`  
**파일명**: `{id}.json` (예: `199325.json`)

**형식**: 크롤링 전략의 통합 스키마.

```json
{
  "id": "199325",
  "source": "잡코리아",
  "url": "https://...",
  "crawled_at": "2025-02-20T12:00:00Z",
  "company": "(주)케이티디에스",
  "position": "신입 앱개발자",
  "year": "2018년 하반기",
  "questions": [
    { "question": "...", "answer": "..." },
    ...
  ],
  "expert_feedback": { "summary": "...", "good_points": [], "weak_points": [] }
}
```

**이렇게 하는 이유:**
- 문서 단위로 저장하면 중간에 실패해도 이미 수집한 건 유지
- `jobkorea_urls.json`의 `id`와 파일명 일치시켜 "이 URL은 이미 수집됨" 체크 가능
- 나중에 ChromaDB 등으로 옮길 때 `data/jobkorea/*.json`만 순회하면 됨

---

## 요약

| 저장 대상 | 형식 | 경로 |
|-----------|------|------|
| URL 목록 | JSON 배열 `[{id, url}, ...]` | `data/jobkorea_urls.json` |
| 상세 문서 | JSON 1건 = 파일 1개 | `data/jobkorea/{id}.json` |

URL은 처음부터 JSON으로 넣어두고, 상세 수집 결과는 `id` 단위로 파일 나누는 방식이 재실행·이관 모두 다루기 좋음.
