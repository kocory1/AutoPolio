# Autofolio 16주 팀 계획표 (2인 분담)

**팀 구성:** 2명 (P1 + P2)  
**기간:** 16주  
**기준:** AUTOFOLIO_파이프라인.md Phase 1~3, **LangGraph** 기반 오케스트레이션, API·Graph 설계 → 구현 순서

---

## 1. 분담 구조 개요

### 1.1 역할 정의

| 역할 | 담당 축 | 담당 영역 요약 |
|------|---------|----------------|
| **P1** | **데이터·파이프라인** | 이력서/합격 자소서 DB, Vector DB, RAPTOR, 임베딩, Asset 생성, 배치, Retrieval |
| **P2** | **서비스·연동·LangGraph** | GitHub OAuth, 채용 공고 파싱, Job Fit, 문항/전략 API·UI, **Writer/Inspector/전략 LangGraph 설계·구현**, Human-in-the-loop |

### 1.2 설계 공통 → 구현 분담

- **1~2주 (공통):** **API 설계**와 **LangGraph 설계**를 **둘 다 함께** 진행. 역할 나누지 않고 설계만 완료.
  - API: Phase 1~3 엔드포인트·스키마·Provider(P1)–Consumer(P2) 정리.
  - LangGraph: 전략/Writer/Inspector 그래프 노드·엣지·State, 그래프가 호출할 API 스펙까지 맞춤.
- **3주~ (분담):** 설계 문서 기준으로 P1은 데이터/검색 API 구현, P2는 OAuth·Job Fit·그래프 구현. **설계 다 하고 나서 구현** 들어가는 구조.
- **연동:** 설계 단계에서 P1 제공 API ↔ 그래프 노드 인터페이스를 맞춰 두어서, 구현 시 충돌·재작업을 줄임.

### 1.3 의존성 방향

```
P1 (데이터) ── 제공 ──►  P2 (서비스 · LangGraph)
  · 합격 자소서 검색 모듈     · Writer 그래프: retrieve 노드에서 모듈 호출 (API 아님)
  · User 프로필/임베딩       · Job Fit가 프로필·공고 임베딩 사용
  · RAPTOR/에셋 저장        · 전략 그래프·Writer 그래프가 에셋 조회
```

→ **설계는 공통:** API·LangGraph 모두 1~2주에 **함께** 설계하고 문서 확정 후, 3주부터 각자 구현.

**합격 자소서 검색 모듈이 4주인 이유:** 파이프라인상 검색 결과는 **자소서 작성 AI·첨삭 AI(LangGraph)** 로 들어가지만, **검색 모듈은 P1이 제공**하고 Writer 그래프가 **내부에서 호출**하는 구조라서, **모듈을 먼저 준비(4주)** 해 두어야 9주 Writer 그래프 구현 시 `retrieve_samples` 노드에서 사용할 수 있음. 대외 API로 노출하지 않음.

---

## 2. LangGraph·Graph 설계 (공통 설계)

오케스트레이션을 **처음부터 LangGraph**로 두고, Writer/Inspector/전략 수립 흐름을 **그래프로 설계·구현**한다.  
**§2 내용은 1~2주 공통 설계**에서 P1+P2가 함께 정하고, `AUTOFOLIO_LangGraph_설계.md`·API 스펙에 반영한다.

### 2.1 그래프 목록 및 담당

| 그래프 | 용도 | State 핵심 필드 | 담당 | 비고 |
|--------|------|------------------|------|------|
| **전략 수립 그래프** | 문항 + 공고 + 에셋 → 문항 유형·매칭 에셋·Gap·전략 JSON | `question`, `job_parsed`, `assets`, `strategy` | P2 | Phase 2. 선형 노드 3~4개. |
| **Writer 그래프** | 전략 + 에셋 + 합격 샘플 → 자소서 초안 | `strategy`, `assets`, `samples`, `draft` | P2 | Phase 3. retrieve → generate → format. |
| **Inspector 그래프** | 초안 + 전략 + 에셋 → 보완 제안, Human-in-the-loop | `draft`, `strategy`, `suggestions`, `user_edited` | P2 | Phase 3. 조건 엣지로 재첨삭 분기. |

전략 수립은 별도 API 없음. 자소서 초안(draft) 요청 시 내부에서 전략 수립 그래프 호출 후 Writer로 이어짐.  
Job Fit는 **User DB**(프로필·임베딩) vs **공고 파싱 API 반환값** 비교 후 점수 반환하는 단일 API로 처리.

### 2.2 그래프별 노드·엣지 (설계 초안)

**전략 수립 그래프**

- 노드: `classify_question` → `select_assets` → `gap_analysis` → `build_strategy`
- State: `question`, `job_parsed`, `user_profile_id`, `assets`(조회 결과), `strategy`(최종 JSON)
- 엣지: 선형. 에러 시 `__fallback__` 또는 종료 노드.

**Writer 그래프**

- 노드: `load_context` → `retrieve_samples`(**합격 자소서 검색 모듈** 호출, 별도 API 아님) → `generate_draft`(LLM) → `format_output`
- State: `strategy`, `assets`, `question`, `samples`, `draft`, `messages`(선택)
- 엣지: 선형. `retrieve_samples`에서 내부 검색 모듈 호출.

**Inspector 그래프**

- 노드: `load_draft` → `analyze`(LLM 보완점 분석) → `suggest`(제안 출력) → Human 입력 대기 → 조건: `re_inspect`(round < N) 또는 `end`
- State: `draft`, `strategy`, `assets`, `suggestions`, `user_edited`, `round`
- 엣지: `suggest` → Human → `re_inspect` / `end`.

### 2.3 State 스키마 공통 규칙

- 그래프별 **TypedDict 또는 Pydantic** State를 `docs/` 또는 코드에 정의.
- 노드 간 데이터는 **State 필드만** 사용. P1 API 호출 결과는 State에 적어 다음 노드에서 재사용.
- **모듈 인터페이스:** `retrieve_samples`가 사용할 합격 자소서 검색 모듈의 입출력 형식은 설계 시 정리 (대외 API로 노출하지 않음).

### 2.4 설계 산출물 (1~2주 공통 목표)

- `docs/AUTOFOLIO_LangGraph_설계.md`: 그래프별 다이어그램(노드·엣지), State 스키마, 노드별 입출력, 그래프가 호출할 API 목록.
- `docs/AUTOFOLIO_API_스펙.md`: Phase 1~3 엔드포인트·요청/응답·Writer/전략 그래프 호출 포인트.
→ **둘 다 1~2주에 함께 작성·확정** 후, 3주부터 구현 분담.

---

## 3. 주차별 계획 (16주)

### Phase 0: 설계 공통 (1~2주) — API + LangGraph 둘 다 함께

1~2주는 **역할 분담 없이** 둘 다 **API 설계**와 **LangGraph 설계**에만 집중. 설계 문서 확정 후 3주부터 P1/P2 구현 분담.

| 주차 | 공통 (P1+P2 함께) | 마일스톤 |
|------|-------------------|----------|
| **1** | 프로젝트 셋업 공유. **API 설계 킥오프**: 인증·사용자·레포 목록·선택, Phase 1~3 API 목록. **LangGraph 설계 킥오프**: 패키지·버전 조사, 전략/Writer/Inspector 그래프 개요, State 공통 필드. Vector DB·OAuth·채용 공고 등 기술 후보 정리 | 킥오프·역할 합의. API·Graph 설계 방향 확정. |
| **2** | **API 상세 설계**: Phase 1~3 엔드포인트·요청/응답·스키마, Provider(P1)–Consumer(P2) 매트릭스, 합격 자소서 DB·선택 레포 저장 구조. **LangGraph 상세 설계**: 전략/Writer/Inspector 노드·엣지·State, 그래프가 호출할 API 목록. `AUTOFOLIO_API_스펙.md`, `AUTOFOLIO_LangGraph_설계.md` 초안 작성·리뷰 | **API 설계 확정**. **Graph 설계 확정**. 3주부터 구현 분담 시작 가능. |

---

### Phase 1: 데이터·파이프라인 vs 서비스·연동 병렬 구축 (3~5주)

| 주차 | P1 (데이터·파이프라인) | P2 (서비스·연동) | 마일스톤 |
|------|------------------------|-------------------|----------|
| **3** | 합격 자소서 스키마 확정, 잡코리아/링커리어 JSON 검증·빈 문항·중복 id 정리. ChromaDB(또는 선정 Vector DB) 스키마 설계, 이전 스크립트·임베딩 필드 정의 | GitHub OAuth: redirect/callback 구현, 토큰 발급·저장 플로우, 레포 목록 API 연동, “선택 레포” 저장 구조 구현 | 합격 자소서 DB 형식 확정 / GitHub 로그인 후 레포 목록 노출 |
| **4** | ChromaDB 이전 완료, **합격 자소서 검색 모듈**(문항/회사/연도 필터) 구현 → 9주 Writer 그래프 `retrieve_samples`에서 호출 (별도 API 노출 없음) | 레포 선택 UI/API, 기본 제외 경로(node_modules 등) 설정, 트리/블롭/커밋 수집 진입 준비 | 이력서 DB·검색 모듈 동작 / “선택 레포” 기준 수집 준비 |
| **5** | GitHub 수집 배치 설계: 선택 레포 트리/블롭/커밋 수집, 제외 경로 적용. RAPTOR 설계(단위·요약 단계·임베딩 저장) | Job Fit 설계: **User DB**(프로필·임베딩) vs **공고 파싱 API 반환값** 비교 → 점수 API. 채용 공고 파싱 스펙 정리·LLM 크롤링 1차 구현 | Phase 1·2 경계 정리, 수집·Job Fit 설계 완료 |

---

### Phase 1 심화 (6~8주)

| 주차 | P1 | P2 | 마일스톤 |
|------|-----|-----|----------|
| **6** | GitHub 레포 트리/블롭/커밋 수집 배치 구현, 기본 제외 적용. RAPTOR 임베딩 파이프라인(선택 레포 기준) 설계·1차 구현 | Job Fit API 구현: User DB 프로필·임베딩 vs 공고 파싱 API 반환값 비교 → 점수·순위. 자기소개서 문항 입력 UI/API(문항 리스트 저장, 문항별 메타) | Job Fit 1차 버전 동작 / 문항 입력 가능 |
| **7** | RAPTOR 임베딩 파이프라인 완료, Vector DB에 사용자 프로필 저장. Asset 생성 파이프라인: 코드/커밋/문서 → STAR 성과 문장 후보, DB 저장 | 문항별 전략 수립 스펙 정리. **전략 수립 그래프** 노드 구현: `classify_question`, `select_assets`, `gap_analysis`, `build_strategy`. LangGraph로 그래프 조립·테스트 | RAPTOR + 전략 그래프 1차 연결 |
| **8** | 합격 자소서 검색 모듈 인터페이스 정리(문항/회사/키워드), Writer 그래프 `retrieve_samples`에서 쓸 입출력 형식 확정 | 전략 수립 그래프 E2E(별도 API 없음). **Writer 그래프** 설계 확정: State·노드(`load_context`, `retrieve_samples`, `generate_draft`, `format_output`), 프롬프트 초안 | 전략 그래프 E2E / Writer 그래프 스펙 확정 |

---

### Phase 2 완성 & Phase 3 진입 (9~11주)

| 주차 | P1 | P2 | 마일스톤 |
|------|-----|-----|----------|
| **9** | 이력서/포트폴리오 업로드 경로 정리(pdf/ppt → 텍스트 추출), 필요 시 멀티모달 연동 검토. Retrieval 연동 테스트·문서화 | **Writer 그래프** 구현: 노드 구현 후 LangGraph 조립, FastAPI 엔드포인트 연동, 간단 테스트 UI 또는 CLI | Phase 3 Writer 그래프 1차 버전 |
| **10** | 배치·Retrieval API 안정화, 로그·에러 핸들링 점검. Inspector가 참조할 “초안+전략+에셋” 조회 API 지원 | **Inspector 그래프** 설계 확정: State·노드(`load_draft`, `analyze`, `suggest`), Human 대기·`re_inspect` 조건 엣지. 스펙 문서 반영 | Writer 그래프 안정화 / Inspector 그래프 스펙 확정 |
| **11** | 포트폴리오 생성 또는 추가 데이터 API 필요 시 구현. P2 Inspector 연동용 데이터 API 정리 | **Inspector 그래프** 구현: 노드·조건 엣지 구현, Human-in-the-loop(수정 → 재첨삭) 플로우, API 연동 | Inspector 그래프 1차 버전 |

---

### Phase 3 완성 & 통합 (12~14주)

| 주차 | P1 | P2 | 마일스톤 |
|------|-----|-----|----------|
| **12** | 전체 배치·검색·Retrieval 성능·안정성 점검, Rate limit·재시도 정책 정리 | 통합 플로우 1차 테스트: 공고 → Job Fit → 문항 입력 → 전략 → Writer → Inspector. API 에러 케이스 처리 | E2E 통합 1차 완료 |
| **13** | 버그 수정, Vector DB 인덱스·쿼리 튜닝, 배치 스케줄·실패 복구 정리 | Split-View UI 또는 에디터 연동, 대화형 첨삭 UX 정리. 폴백(URL 실패 시 텍스트 붙여넣기) 적용 | 통합 플로우 + UX 정리 |
| **14** | 로그·모니터링, 데이터 파이프라인 문서화. 합격 자소서·RAPTOR·에셋 스키마 최종 정리 | API·프론트 문서 정리, 데모 시나리오 정리 | Phase 1~3 기능 완료 |

---

### 마무리 (15~16주)

| 주차 | P1 | P2 | 공통·마일스톤 |
|------|-----|-----|----------------|
| **15** | 배치·API 안정화, 회귀 버그 수정, 운영 체크리스트(백업·환경 변수·시크릿) 정리 | 통합 테스트 재실행, 에지 케이스·예외 처리 보완 | 통합 테스트·안정화 |
| **16** | 최종 데이터 파이프라인 점검, 회고 | 최종 데모 준비, 회고 | **16주 데모 가능, 회고** |

---

## 4. API 설계 시 분담 가이드

**설계(1~2주)는 공통**으로 함께 진행하므로 아래는 **구현 단계**에서 누가 제공(Provider)/소비(Consumer)인지 정리할 때 참고.

- **공통으로 정할 것**
  - 인증: 토큰 방식(OAuth 이후 JWT/세션 등), 인증 실패 시 응답 형식.
  - 사용자·레포: 사용자 ID, “선택 레포” 목록 저장 API 소유자(P2), 저장 형식은 P1이 사용하는 스키마와 호환.
- **P1이 제공(Provider)·P2가 소비(Consumer)**
  - 합격 자소서 검색 **모듈** (문항/회사/연도/키워드) — 대외 API 노출 없이 Writer 그래프 내부에서 호출.
  - User 프로필/임베딩 저장·조회(RAPTOR 결과, 에셋 목록).
  - (선택) 채용 공고 임베딩 저장은 P2가 파싱 후 P1 API로 저장할지, P2가 직접 저장할지 설계 시 결정.
- **P2가 제공**
  - GitHub OAuth callback, 토큰·레포 목록·선택 레포 API.
  - 채용 공고 파싱(담당업무/자격요건/우대사항/기업명/기업인재상/포지션명), Job Fit API(User DB vs 공고 파싱 결과 비교 → 점수·순위), Writer/Inspector API.
- **문서**
  - `docs/`에 `AUTOFOLIO_API_스펙.md`(또는 OpenAPI)를 두고, 엔드포인트별 담당(P1/P2)과 Provider/Consumer 표기.
  - `docs/AUTOFOLIO_LangGraph_설계.md`: 그래프별 노드·엣지·State, Writer 그래프가 호출하는 P1 API 명시.

---

## 5. 주간 루틴 (권장)

- **주 1회 동기화:** 주차 목표·진행률·블로커 공유 (30분~1시간).
- **API·Graph 변경:** API 스펙 또는 `AUTOFOLIO_LangGraph_설계.md`에 반영 후 상대 역할에게 공유.
- **우선순위:** “공고 파싱 → Job Fit → 전략 → Writer → Inspector” 순서 유지 시 Phase 2·3 데모가 수월함.

---

## 6. 산출물 체크리스트 (16주 종료 시)

- [ ] **API 설계:** Phase 1~3 엔드포인트·스키마 문서화, P1/P2 Provider–Consumer 정리
- [ ] **LangGraph 설계:** 전략/Writer/Inspector 그래프 State·노드·엣지 문서화, `AUTOFOLIO_LangGraph_설계.md` 확정
- [ ] 합격 자소서 DB: Vector DB 저장·검색 API 동작
- [ ] 채용 공고: URL 입력 → 담당업무/자격요건/우대사항/기업명/기업인재상/포지션명 추출 저장
- [ ] Job Fit: 공고–프로필 유사도 점수·순위 API
- [ ] 문항별 전략: 문항 유형·매칭 에셋·Gap 출력
- [ ] Writer 그래프: 전략+에셋+합격 샘플 → 자소서 초안 (LangGraph 기반 API)
- [ ] Inspector 그래프: 초안 → 보완 제안, 수정 후 재첨삭 (Human-in-the-loop)
- [ ] 통합 E2E 플로우 및 데모

---

## 7. 문서 이력

- 1.0: 16주 2인 분담 계획표 초안. API 설계 1~2주 포함, P1(데이터·파이프라인) / P2(서비스·연동) 역할, Provider–Consumer 정리.
- 1.1: **LangGraph** 첨부터 반영. Graph 설계 섹션 추가(전략/Writer/Inspector 그래프, 노드·엣지·State), 7~11주 그래프 구현 반영. 산출물에 `AUTOFOLIO_LangGraph_설계.md` 추가.
- 1.2: **API 설계·LangGraph 설계를 공통으로** 진행. 1~2주는 역할 분담 없이 둘 다 설계만, 설계 확정 후 3주부터 구현 분담. Phase 0 테이블을 "공통 (P1+P2 함께)" 구조로 변경.
