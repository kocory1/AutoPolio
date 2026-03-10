# Autofolio 임베딩 전략

**문서 버전:** 1.1  
**기준:** [AUTOFOLIO_파이프라인.md](AUTOFOLIO_파이프라인.md), [AUTOFOLIO_User_Asset_스키마_설계.md](AUTOFOLIO_User_Asset_스키마_설계.md)

---

## 1. 개요

Autofolio는 **폴더 구조 기반 RAPTOR** 방식을 채택하여, GitHub 레포의 자연스러운 디렉터리 구조를 계층적 요약 트리로 활용한다.

### 핵심 아이디어

- RAPTOR의 계층적 트리 구조를 가져오되, **클러스터링 대신 실제 폴더 구조**를 트리의 기준으로 사용.
- code(Leaf): 개별 소스 파일 임베딩 (본인 커밋만)
- folder(Mid): 폴더별 요약 생성 → 임베딩
- project(Root): 레포 루트 요약 → 임베딩

---

## 2. 왜 폴더 구조 기반인가

| 장점 | 설명 |
|------|------|
| **클러스터링 불필요** | 폴더 구조가 이미 논리적 그룹핑 → 복잡한 클러스터링 알고리즘 불필요 |
| **결정적(Deterministic)** | 같은 레포면 항상 같은 트리 → 재현성 보장 |
| **직관적** | 유저가 "auth 모듈" 하면 해당 폴더 요약과 매칭 |
| **비용 절감** | 임베딩 클러스터링 스텝 생략 |
| **개발자 사고방식과 일치** | 폴더로 기능을 나누는 관행과 일치 → 검색 결과 이해 용이 |

---

## 3. 트리 구조 예시

### 레포 폴더 구조

```
project/
├── src/
│   ├── auth/
│   │   ├── login.py
│   │   ├── jwt.py
│   │   └── oauth.py
│   ├── payment/
│   │   ├── pg.py
│   │   └── refund.py
│   └── product/
│       ├── crud.py
│       └── search.py
├── tests/
│   └── ...
└── README.md
```

### RAPTOR 트리 매핑

```
                      [프로젝트 루트 요약]
                      "FastAPI 기반 이커머스 백엔드,
                       인증/결제/상품 관리 구현"
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
         [src 요약]     [README 임베딩]  [tests 요약]
              │
     ┌────────┼────────┐
     ▼        ▼        ▼
 [auth 요약] [payment 요약] [product 요약]
 "JWT 인증,   "PG 연동,      "상품 CRUD,
  소셜로그인"  환불 처리"     검색 기능"
     │            │            │
  ┌──┼──┐     ┌──┼──┐      ┌──┼──┐
  ▼  ▼  ▼     ▼  ▼  ▼      ▼  ▼  ▼
login jwt oauth pg refund  crud search
.py  .py .py   .py .py     .py  .py
```

---

## 4. 구현 흐름

```
1. GitHub API로 트리 구조 수집 (GET /repos/{owner}/{repo}/git/trees/{sha}?recursive=1)

2. Noise Filtering
   - 제외: node_modules/, .git/, __pycache__/, *.lock, 설정 파일 등
   - 포함: 소스 코드 (*.py, *.js, *.ts, *.java 등), README, 문서

3. code 레벨: 각 소스 파일 (본인 커밋만)
   - summary 우선 임베딩, 없으면 content (토큰 제한 시 truncate)
   - metadata: type, source, repo, path (MVP 4개)

4. folder 레벨: Bottom-up 재귀
   - 하위 파일들의 요약/내용을 합침
   - LLM으로 폴더 요약 생성
   - 폴더 요약 → 임베딩

5. project 레벨: 루트까지 반복
   - 상위 폴더는 하위 폴더 요약들을 입력으로 받아 요약 생성
   - 레포 루트 요약 → project type
```

---

## 5. 청크 스키마

[User_Asset_스키마_설계](AUTOFOLIO_User_Asset_스키마_설계.md) §2와 동일. type=code|folder|project|document, source=github|resume|portfolio, metadata MVP 4개(type, source, repo, path).

### code 청크 (Leaf)

```json
{
  "id": "owner/repo/src/auth/login.py",
  "document": "JWT 토큰 기반 로그인 처리, 실패 시 401 반환",
  "metadata": {
    "type": "code",
    "source": "github",
    "repo": "owner/repo",
    "path": "src/auth/login.py"
  },
  "embedding": [...]
}
```

- **document**: summary 우선, 없으면 content (truncate). [User_Asset](AUTOFOLIO_User_Asset_스키마_설계.md) §2.4
- **본인 커밋만** 인덱싱 (`author=본인`)

### folder 청크 (Mid)

```json
{
  "id": "owner/repo/src/auth",
  "document": "JWT 기반 인증 시스템. 로그인, 토큰 검증, 소셜 로그인(Google/Kakao) 지원",
  "metadata": {
    "type": "folder",
    "source": "github",
    "repo": "owner/repo",
    "path": "src/auth"
  },
  "embedding": [...]
}
```

### project 청크 (Root)

```json
{
  "id": "owner/repo/",
  "document": "FastAPI 기반 이커머스 백엔드, 인증/결제/상품 관리 구현",
  "metadata": {
    "type": "project",
    "source": "github",
    "repo": "owner/repo",
    "path": "/"
  },
  "embedding": [...]
}
```

---

## 6. 커밋 통합 전략

- **code 인덱싱:** 본인 커밋에 포함된 파일만. `author=본인` 필터 적용. [User_Asset](AUTOFOLIO_User_Asset_스키마_설계.md) §2.2
- **MVP:** metadata에 `related_commits` 미포함. 추후 확장 시 code 청크에 연결 검토.

---

## 7. 검색 활용 시나리오

| 시나리오 | type | 예시 |
|----------|------|------|
| **JD 키워드 매칭** | folder, project | "인증 시스템 경험" → auth 폴더 요약 매칭 |
| **STAR 에셋 생성** | folder | "결제 모듈에서 한 일" → payment 폴더 요약 |
| **Inspector 증거 찾기** | code | "동시성 처리 코드" → pg.py 파일 매칭 |
| **프로젝트 개요** | project | "이 프로젝트가 뭔지" → 루트 요약 |

---

## 8. 예외 처리

| 케이스 | 대응 |
|--------|------|
| **폴더 구조 없음 (모든 파일이 루트)** | 트리 깊이 1로 처리, code 단위 임베딩만 수행 |
| **폴더 내 파일이 너무 많음** | code 요약 먼저 생성 → 요약끼리 다시 요약 (토큰 제한 대응) |
| **유틸/헬퍼 폴더** | `utils/`, `helpers/`, `common/` 등은 path로 구분, 검색 가중치 낮춤 |
| **테스트 폴더** | `tests/`, `__tests__/` 등은 path로 구분, 필요 시 type_filter로 제외 |

---

## 9. 요약

| 항목 | 내용 |
|------|------|
| **전략** | 폴더 구조 기반 RAPTOR |
| **code** | 소스 파일 임베딩. summary 우선, 없으면 content. 본인 커밋만. |
| **folder** | 폴더별 LLM 요약 → 임베딩, bottom-up 재귀 |
| **project** | 레포 루트 LLM 요약 → 임베딩 |
| **metadata** | type, source, repo, path (MVP 4개). [User_Asset](AUTOFOLIO_User_Asset_스키마_설계.md) §2.3 |
| **장점** | 클러스터링 불필요, 직관적, 개발자 사고방식과 일치 |

---

## 10. 문서 관계

- 파이프라인: [AUTOFOLIO_파이프라인.md](AUTOFOLIO_파이프라인.md)
- User Asset 스키마: [AUTOFOLIO_User_Asset_스키마_설계.md](AUTOFOLIO_User_Asset_스키마_설계.md)

---

## 11. 문서 이력

- 1.0 (2026-02-12): 초안 작성. 폴더 기반 RAPTOR 구조, 청크 스키마, 커밋 통합, 예외 처리 정의.
- 1.1: User_Asset 스키마에 맞춤. type=code|folder|project, metadata MVP 4개, 본인 커밋만, summary 우선 임베딩.
