## Week2 - API·LangGraph 설계 정리 & 1번 포트폴리오 그래프 구현

**주차 목표**
- 1~2주 공통 설계 마무리: LangGraph 설계 문서(`AUTOFOLIO_LangGraph_설계.md`) 확정.
- 그래프 구조 구현: State / 노드(주석) / 엣지 / 그래프 조립, main에서 PNG 시각화까지 검증.

**이번 주 작업 범위**
1. LangGraph 설계 문서: 4개 그래프(포트폴리오·전략·Writer·Inspector) 노드·엣지·State 정리.
2. 포트폴리오 생성 그래프: `load_profile` → `build_star_sentence` → `self_consistency` → `build_portfolio`, 조건엣지(재진입/__fallback__).
3. 공용 유틸: 그래프 시각화(visualize_graph, NodeStyles), main에서 PNG 생성.
4. github_embedding 디렉터리 구조(login/, embedding/) 확정.

---

### 1. 레퍼런스 문서 요약
- `AUTOFOLIO_LangGraph_설계.md`: 1번=포트폴리오 생성(문항 미사용), 2번=전략 수립(문항+공고+에셋→전략 JSON), 3번=Writer, 4번=Inspector.
- 1번 그래프 State: `user_id`, `profile`, `assets`, `star`, `is_hallucination`, `is_star`, `star_retry_count`, `portfolio`, `consistency_feedback`.
- self_consistency 실패 시 `consistency_feedback`를 build_star_sentence 재진입 시 프롬프트에 반영, 재시도 상한 후 __fallback__.

---

### 2. 이번 주 TODO
- [x] LangGraph 설계 문서 정리 (포트폴리오/전략/Writer/Inspector, 문항별 멀티에이전트 옵션)
- [x] 1번 그래프 State·노드·엣지·graph.py 구현 (노드 내부는 주석/플레이스홀더)
- [x] 조건엣지: self_consistency 후 통과→build_portfolio, 실패&retry<N→build_star_sentence, 실패&retry≥N→__fallback__
- [x] main에서 포트폴리오 그래프 PNG 생성 (docs/portfolio_graph.png)
- [x] src/utils: visualize_graph, NodeStyles, generate_random_hash
- [x] src/github_embedding: login/, embedding/ 디렉터리 구조
- [ ] 2번 Writer 그래프 구현 (state/node/edge/graph, 주석 또는 플레이스홀더)
- [ ] 3번 Inspector 그래프 구현 (state/node/edge/graph, 주석 또는 플레이스홀더)

---

### 3. 진행 로그
- 2026-03-02
  - [x] main 기준 최신 반영 (`git pull origin main`)
  - [x] week-issues 형식 확인 (week1-github-oauth.md) 및 week2 이슈 문서 작성
