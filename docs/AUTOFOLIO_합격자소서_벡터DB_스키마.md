# 합격 자소서 Vector DB 스키마

**문서 버전:** 1.3  
**기준:** [AUTOFOLIO_RAG_파이프라인_핵심.md](AUTOFOLIO_RAG_파이프라인_핵심.md), [AUTOFOLIO_Writer_그래프_파이프라인_제안.md](AUTOFOLIO_Writer_그래프_파이프라인_제안.md) §4.1, [AUTOFOLIO_Inspector_그래프_파이프라인_제안.md](AUTOFOLIO_Inspector_그래프_파이프라인_제안.md), 기존 크롤링 데이터 구조

---

## 1. 개요

합격 자소서는 **Writer·Inspector**에서 "문항 유사 검색"으로 조회된다.  
검색 조건: 문항(question) 유사도 + 회사/포지션/연도 필터.

**저장 단위:** **문항(question+answer) 단위 청크**. 한 자소서에 여러 문항이 있으므로, 각 질문-답변 쌍을 하나의 벡터 문서로 저장.

---

## 2. 필수 스키마 (최소)

| 필드 | 타입 | 설명 |
|------|------|------|
| `id` | str | 청크 고유 ID. `{source}_{doc_id}_{q_idx}`. 동일 자소서 문항 묶음은 id에서 `_q_idx` 제거해 추출 |
| `question` | str | 자소서 문항 (질문 텍스트) |
| `answer` | str | 답변 텍스트 |
| `company` | str | 회사명 (메타데이터 필터) |
| `position` | str | 포지션명 (메타데이터 필터) |
| `year` | str | 연도 (메타데이터 필터) |
| `source` | str | 출처 (`"잡코리아"` \| `"링커리어"`) |
| `embedding` | list[float] | 아래 형식 텍스트 임베딩 |

---

## 3. 임베딩 대상

**임베딩할 텍스트:** `{company_name}의 {year}년 {position} 공고의 자기소개서 문항 {n} : {question}`

- **예:** `콜로소의 2022년 데이터 분석가 공고의 자기소개서 문항 1 : 회고 분석을 통한 인사이트 도출에 대해 서술해주세요`
- **이유:** 검색 시 동일 형식으로 쿼리 (`embed(회사명의 year년 position 공고의 자기소개서 문항 n : user_question)`) → 공고 맥락·문항이 같은 의미 공간에서 비교됨
- **answer**는 메타데이터로 저장, 검색 결과와 함께 반환

---

## 4. 검색 흐름

```
[Writer/Inspector] retrieve_passed_cover_letters(
    question="회고 분석을 통한 인사이트 도출",
    company_name="콜로소",      # job_parsed.기업명 (선택)
    position="데이터 분석가",   # job_parsed.포지션명 (선택)
    year=2022,                 # (선택)
    keywords=[...],            # (선택, 쿼리 확장용)
    top_k=5
)
    │
    ▼
1. `embed("{company_name}의 {year}년 {position} 공고의 자기소개서 문항 {n} : {user_question}")` → 쿼리 벡터
2. Vector DB: embedding 유사도 검색 (top_k * N, 여유 있게)
3. 메타데이터 필터: company, position, year (있으면 적용)
4. 상위 top_k개 반환
```

---

## 5. 크롤링 데이터 매핑

| 크롤링 필드 | 스키마 필드 | 비고 |
|-------------|-------------|------|
| `id` | `id` | `{source}_{원본id}_{q_idx}` 생성 (예: linkareer_31241_0) |
| `source` | `source` | 잡코리아/링커리어 |
| `company` | `company` | 링커리어는 `company`에 "회사/포지션/연도" 합쳐진 경우 있음 → 파싱 필요 |
| `position` | `position` | |
| `year` | `year` | |
| `questions[].question` | `question` | |
| `questions[].answer` | `answer` | |
| - | `embedding` | `embed("{company}의 {year}년 {position} 공고의 자기소개서 문항 {q_idx+1} : {question}")` 인덱싱 시 생성 |

---

## 6. 선택 필드 (추후 확장)

| 필드 | 타입 | 용도 |
|------|------|------|
| `url` | str | 출처 URL (크롤링 원문) |
| `expert_feedback` | str | 전문가 피드백 (있으면) |
| `crawled_at` | datetime | 수집 시각 |

---

## 7. 문서 관계

- DB 스키마 전체: [AUTOFOLIO_DB_스키마_설계.md](AUTOFOLIO_DB_스키마_설계.md)
- 검색 모듈 인터페이스: [AUTOFOLIO_Writer_그래프_파이프라인_제안.md](AUTOFOLIO_Writer_그래프_파이프라인_제안.md) §4.1
- RAG 파이프라인: [AUTOFOLIO_RAG_파이프라인_핵심.md](AUTOFOLIO_RAG_파이프라인_핵심.md)
- 16주 계획표: [AUTOFOLIO_16주_계획표.md](AUTOFOLIO_16주_계획표.md) 3주(스키마 확정), 4주(검색 모듈)

---

## 8. 문서 이력

- 1.0: 합격 자소서 Vector DB 스키마 초안. 필수 항목만. 문항 단위 청크, question+answer 임베딩.
- 1.1: question만 임베딩. document_id 제거(id 하나로 통합). [AUTOFOLIO_DB_스키마_설계.md](AUTOFOLIO_DB_스키마_설계.md)와 정렬.
- 1.2: 임베딩 대상 복원 → question+answer. [AUTOFOLIO_DB_스키마_설계.md](AUTOFOLIO_DB_스키마_설계.md)와 정렬.
- 1.3: 임베딩 형식 → `{company}의 {year}년 {position} 공고의 자기소개서 문항 {n} : {question}`. [AUTOFOLIO_DB_스키마_설계.md](AUTOFOLIO_DB_스키마_설계.md)와 정렬.
