# Autofolio 임베딩 전략

**문서 버전:** 1.0  
**최종 정리일:** 2025-02-12

---

## 1. 개요

Autofolio는 **폴더 구조 기반 RAPTOR** 방식을 채택하여, GitHub 레포의 자연스러운 디렉터리 구조를 계층적 요약 트리로 활용한다.

### 핵심 아이디어

- RAPTOR의 계층적 트리 구조를 가져오되, **클러스터링 대신 실제 폴더 구조**를 트리의 기준으로 사용.
- Leaf(최하위): 개별 소스 파일 임베딩
- 상위 레벨: 폴더별 요약 생성 → 임베딩
- 루트까지 재귀적으로 요약

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

3. Leaf 레벨: 각 소스 파일
   - 파일 내용 → (선택) LLM 요약 → 임베딩
   - 메타데이터: path, language, lines, related_commits

4. 폴더 레벨: Bottom-up 재귀
   - 하위 파일들의 요약/내용을 합침
   - LLM으로 폴더 요약 생성
   - 폴더 요약 → 임베딩

5. 루트까지 반복
   - 상위 폴더는 하위 폴더 요약들을 입력으로 받아 요약 생성
```

---

## 5. 청크 스키마

### 파일 청크 (Leaf)

```json
{
  "id": "repo_abc/src/auth/login.py",
  "type": "file",
  "repo": "user/repo_abc",
  "path": "src/auth/login.py",
  "language": "python",
  "content": "...",
  "summary": "JWT 토큰 기반 로그인 처리, 실패 시 401 반환",
  "embedding": [...],
  "metadata": {
    "lines": 120,
    "related_commits": ["abc123", "def456"]
  }
}
```

### 폴더 청크 (Non-leaf)

```json
{
  "id": "repo_abc/src/auth",
  "type": "folder",
  "repo": "user/repo_abc",
  "path": "src/auth",
  "children": ["src/auth/login.py", "src/auth/jwt.py", "src/auth/oauth.py"],
  "summary": "JWT 기반 인증 시스템. 로그인, 토큰 검증, 소셜 로그인(Google/Kakao) 지원",
  "embedding": [...],
  "metadata": {
    "file_count": 3,
    "total_lines": 450
  }
}
```

---

## 6. 커밋 통합 전략

폴더 구조는 **코드(공간)** 기준, 커밋은 **시간** 기준이라 별도 처리 필요.

### 옵션 A: 파일에 커밋 메타 연결 (권장)

- 각 파일 청크에 `related_commits` 필드로 해당 파일을 수정한 커밋 ID 목록 저장.
- 파일 검색 후, 관련 커밋도 함께 조회 가능.

### 옵션 B: 커밋 별도 인덱스

- 코드 트리: 폴더 기반 RAPTOR (위 구조)
- 커밋 인덱스: 커밋 메시지 + 변경 파일 목록 (flat 구조)
- 검색 목적에 따라 인덱스 선택.

### 권장 조합

- **1차:** 파일 청크에 `related_commits` 메타 연결
- **2차:** 커밋 메시지 기반 검색이 필요하면 별도 인덱스 추가

---

## 7. 검색 활용 시나리오

| 시나리오 | 검색 레벨 | 예시 |
|----------|-----------|------|
| **JD 키워드 매칭** | Top/Mid 레벨 (폴더 요약) | "인증 시스템 경험" → auth 폴더 요약 매칭 |
| **STAR 에셋 생성** | Mid 레벨 (폴더 요약) | "결제 모듈에서 한 일" → payment 폴더 요약 |
| **Inspector 증거 찾기** | Leaf 레벨 (파일) | "동시성 처리 코드" → pg.py 파일 매칭 |
| **프로젝트 개요** | Root 레벨 | "이 프로젝트가 뭔지" → 루트 요약 |

---

## 8. 예외 처리

| 케이스 | 대응 |
|--------|------|
| **폴더 구조 없음 (모든 파일이 루트)** | 트리 깊이 1로 처리, 파일 단위 임베딩만 수행 |
| **폴더 내 파일이 너무 많음** | 파일 요약 먼저 생성 → 요약끼리 다시 요약 (토큰 제한 대응) |
| **유틸/헬퍼 폴더** | `utils/`, `helpers/`, `common/` 등은 메타에 표시, 검색 가중치 낮춤 |
| **테스트 폴더** | `tests/`, `__tests__/` 등은 별도 타입으로 분류, 필요 시 제외 옵션 |

---

## 9. 요약

| 항목 | 내용 |
|------|------|
| **전략** | 폴더 구조 기반 RAPTOR |
| **Leaf** | 소스 파일 임베딩 (+ 선택적 요약) |
| **Non-leaf** | 폴더별 LLM 요약 → 임베딩, bottom-up 재귀 |
| **커밋** | 파일 메타에 `related_commits` 연결 (1차), 별도 인덱스 (2차) |
| **장점** | 클러스터링 불필요, 직관적, 개발자 사고방식과 일치 |

---

## 10. 문서 이력

- 1.0 (2025-02-12): 초안 작성. 폴더 기반 RAPTOR 구조, 청크 스키마, 커밋 통합, 예외 처리 정의.
