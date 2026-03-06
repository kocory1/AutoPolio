# Autofolio 16주 팀 계획표 (2인 분담)

**팀 구성:** 2명 (P1 + P2)  
**기간:** 16주  
**기준:** AUTOFOLIO_파이프라인.md Phase 1~3, **LangGraph** 기반 오케스트레이션, API·Graph 설계 → 구현 순서  
**참고:** 8주차는 시험기간.

---

## 1. 분담 구조 개요

### 1.1 역할 정의

| 역할 | 담당 축 | 담당 영역 요약 |
|------|---------|----------------|
| **P1** | **데이터·파이프라인** | 이력서/합격 자소서 DB, Vector DB, RAPTOR, 임베딩, Asset 생성, 배치, Retrieval |
| **P2** | **서비스·연동·LangGraph** | GitHub OAuth, 채용 공고 파싱, Job Fit, Writer/Inspector LangGraph 설계·구현, Human-in-the-loop |

### 1.2 설계 공통 → 구현 분담

- **1~2주 (공통):** API 설계와 LangGraph 설계를 함께 진행.
  - API: Phase 1~3 엔드포인트·스키마·Provider(P1)–Consumer(P2) 정리.
  - LangGraph: Portfolio/Writer/Inspector 노드·엣지·State, 호출 API·모듈 스펙 정리.
- **3주~ (분담):** P1은 데이터/검색 모듈·저장소 구현, P2는 OAuth·Job Fit·그래프 구현.
- **연동:** 설계 단계에서 P1 제공 API·모듈 ↔ 그래프 노드 인터페이스를 맞춰 재작업 최소화.

### 1.3 의존성 방향

```
P1 (데이터) ── 제공 ──►  P2 (서비스 · LangGraph)
  · 합격 자소서 검색 모듈     · Writer 그래프: retrieve_samples·load_assets 노드에서 검색·에셋 조회 (API 아님)
  · User 프로필/임베딩       · Job Fit API가 프로필·공고 파싱 결과 비교
  · RAPTOR/에셋 저장        · Writer/Inspector 그래프가 에셋 조회
```

---

## 2. LangGraph·Graph 설계 (공통 설계)

오케스트레이션을 LangGraph로 두고, Portfolio/Writer/Inspector 흐름을 그래프로 설계·구현한다.  
`AUTOFOLIO_LangGraph_설계.md`와 `AUTOFOLIO_API_스펙.md`에 반영한다.

### 2.1 그래프 목록 및 담당

| 그래프 | 용도 | State 핵심 필드 | 담당 | 비고 |
|--------|------|------------------|------|------|
| **포트폴리오 그래프** | User 프로필·에셋 → STAR → 포트폴리오 생성 | `profile`, `assets`, `star`, `portfolio` | P2 | Phase 1 |
| **Writer 그래프** | 문항 + 합격 샘플 → 유저 DB(에셋) → 자소서 초안 | `user_id`, `assets`, `question`, `samples`, `draft` | P2 | Phase 3 |
| **Inspector 그래프** | 초안 + 에셋 → 보완 제안, Human-in-the-loop | `draft`, `assets`, `suggestions`, `user_edited` | P2 | Phase 3 |

- **전략 수립 그래프는 제외**를 기준으로 한다.
- Job Fit는 **User DB**(프로필·임베딩) vs **공고 파싱 API 반환값** 비교 후 점수 반환하는 단일 API로 처리.

### 2.2 그래프별 노드·엣지 (설계 초안)

**Writer 그래프**
- 노드: `retrieve_samples`(합격 자소서 검색) → `load_assets`(유저 DB 에셋 조회) → `generate_draft` → `self_consistency` → `format_output`
- State: `user_id`, `assets`, `question`, `max_chars`, `samples`, `draft`, `messages`(선택)
- 엣지: `retrieve_samples` 검증 실패 시만 END (samples 못 찾아도 load_assets 진행). `load_assets` 조회 실패 시 END.

**Inspector 그래프**
- 노드: `load_draft` → `analyze` → `suggest` → Human 입력 대기 → `re_inspect`(round < N) 또는 `end`
- State: `draft`, `assets`, `suggestions`, `user_edited`, `round`
- 엣지: `suggest` → Human → `re_inspect` / `end`.

---

## 3. 주차별 계획 (16주)

### Phase 0: 설계 공통 (1~2주)

| 주차 | 공통 (P1+P2 함께) | 마일스톤 |
|------|-------------------|----------|
| **1** | API 설계 킥오프(인증·유저·GitHub·Jobs·Job Fit·Cover Letter·Portfolio), LangGraph 설계 킥오프(Portfolio/Writer/Inspector) | API·Graph 설계 방향 확정 |
| **2** | API 상세 스펙·응답 스키마 확정, LangGraph 상세(State/노드/엣지) 확정, 문서 리뷰 | 설계 확정, 구현 준비 완료 |

### Phase 1: 데이터·파이프라인 vs 서비스·연동 (3~7주)

| 주차 | P1 (데이터·파이프라인) | P2 (서비스·연동) | 마일스톤 |
|------|------------------------|-------------------|----------|
| **3** | 합격 자소서 스키마 확정, Vector DB 스키마 설계 | GitHub OAuth redirect/callback, 토큰 저장, 레포 목록 API 연동 | 로그인 후 레포 목록 노출 |
| **4** | 합격 자소서 검색 모듈(문항/회사/연도 필터) 구현 | 선택 레포 저장/조회 UI·API, 수집 준비 | 검색 모듈 동작 |
| **5** | GitHub 수집 배치 설계, RAPTOR 설계 | Job Fit 설계(User DB vs 공고 파싱 결과) + 공고 파싱 1차 | Job Fit 설계 완료 |
| **6** | 수집 배치 1차 구현, RAPTOR 임베딩 1차 | Job Fit API 1차, 문항 입력 UI/API | Job Fit 1차 동작 |
| **7** | RAPTOR 완료, Asset 생성 파이프라인 구현 | Writer 그래프 노드 구현 시작 | Asset + Writer 연결 시작 |
| **8** | **시험기간** | **시험기간** | - |

### Phase 2: 작성/첨삭 진입 (9~11주)

| 주차 | P1 | P2 | 마일스톤 |
|------|-----|-----|----------|
| **9** | 업로드 경로 정리(pdf/ppt), Retrieval 연동 테스트 | Writer 그래프 구현/연동(FastAPI) | Writer 1차 버전 |
| **10** | 배치·Retrieval 안정화, Inspector 연동용 조회 지원 | Inspector 그래프 설계 확정 | Inspector 설계 확정 |
| **11** | 추가 데이터 API 정리 | Inspector 그래프 구현(Human-in-the-loop) | Inspector 1차 버전 |

### Phase 3: 통합·마무리 (12~16주)

| 주차 | P1 | P2 | 마일스톤 |
|------|-----|-----|----------|
| **12** | 성능·안정성 점검 | 통합 플로우 1차 테스트(공고→Job Fit→문항→Writer→Inspector) | E2E 1차 완료 |
| **13** | 버그 수정, 인덱스·쿼리 튜닝 | UI/UX 정리, 폴백 처리 | 통합 UX 정리 |
| **14** | 로그·모니터링, 데이터 파이프라인 문서화 | API·프론트 문서 정리 | 기능 완료 |
| **15** | 배치·API 안정화 | 통합 테스트 재실행 | 안정화 |
| **16** | 최종 점검, 회고 | 데모 준비, 회고 | 데모 가능 |

---

## 4. API 설계 시 분담 가이드

- **P1 제공 / P2 소비**
  - 합격 자소서 검색 모듈 (대외 API 노출 없이 Writer 내부 호출)
  - User 프로필/임베딩 저장·조회
- **P2 제공**
  - GitHub OAuth callback, 토큰·레포 목록·선택 레포 API
  - 채용 공고 파싱(담당업무/자격요건/우대사항/기업명/기업인재상/포지션명)
  - Job Fit API(User DB vs 공고 파싱 결과 비교 → 점수·순위)
  - Writer/Inspector API

---

## 5. 주간 루틴 (권장)

- 주 1회 동기화: 목표·진행률·블로커 공유
- API·Graph 변경 시 문서 동시 업데이트
- 우선순위: 공고 파싱 → Job Fit → Writer → Inspector

---

## 6. 산출물 체크리스트 (16주 종료 시)

- [ ] API 설계 문서(Phase 1~3 엔드포인트·스키마)
- [ ] LangGraph 설계 문서(Portfolio/Writer/Inspector)
- [ ] 합격 자소서 DB 저장·검색 모듈 동작
- [ ] 채용 공고 파싱(담당업무/자격요건/우대사항/기업명/기업인재상/포지션명)
- [ ] Job Fit 점수·순위 API
- [ ] Writer 그래프(문항+합격 샘플→에셋→초안)
- [ ] Inspector 그래프(초안 → 보완 제안 → 재첨삭)
- [ ] 통합 E2E 플로우 및 데모

---

## 7. 문서 이력

- 1.0: 16주 2인 분담 계획표 초안.
- 1.1: LangGraph 기반 흐름 반영.
- 1.2: API 설계·LangGraph 설계 공통 진행 구조로 정리.
- 1.3 (2026-03-04): 전략 수립 그래프 제외 기준으로 전면 정리. 8주차 플랜 삭제.
- 1.4 (2026-03-04): 8주차 시험기간 명시.
