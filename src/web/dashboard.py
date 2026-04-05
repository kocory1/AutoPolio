from __future__ import annotations

"""
대시보드 HTML (개발용). `src/app/main.py` 라우트에서 참조한다.
"""

dashboard_html = r"""
<!doctype html>
<html lang="ko">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Autofolio Dashboard (Dev)</title>
    <style>
      body { font-family: system-ui, -apple-system, Segoe UI, sans-serif; padding: 16px; max-width: 1200px; margin: 0 auto; color: #1e293b; }
      pre { background: #f1f5f9; padding: 12px; overflow-x: auto; border-radius: 8px; border: 1px solid #e2e8f0; font-size: 13px; }
      button { padding: 10px 14px; margin-right: 8px; margin-bottom: 6px; border-radius: 6px; cursor: pointer; border: 1px solid #cbd5e1; background: #fff; }
      button:hover { filter: brightness(0.97); }
      hr { border: none; border-top: 1px solid #e2e8f0; margin: 28px 0; }
      .demo-panel {
        border: 1px solid #93c5fd;
        border-radius: 12px;
        padding: 20px 22px;
        margin: 28px 0;
        background: linear-gradient(165deg, #eff6ff 0%, #f8fafc 55%);
        box-shadow: 0 4px 14px rgba(37, 99, 235, 0.08);
      }
      .demo-panel h2 { margin-top: 0; color: #1e40af; font-size: 1.35rem; }
      .demo-panel .tag { display: inline-block; font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 999px; background: #2563eb; color: #fff; margin-right: 6px; vertical-align: middle; }
      .demo-steps { margin: 12px 0 18px 1.2em; line-height: 1.65; color: #334155; }
      .demo-steps li { margin-bottom: 6px; }
      .btn-demo-primary { background: #2563eb !important; color: #fff !important; border-color: #1d4ed8 !important; font-weight: 600; }
      .btn-demo-secondary { background: #475569 !important; color: #fff !important; border-color: #334155 !important; }
      .btn-demo-ghost { background: #fff !important; border-color: #94a3b8 !important; color: #0f172a !important; }
      #embeddingResult { min-height: 3rem; max-height: 480px; }
      .hint { font-size: 0.9rem; color: #475569; margin: 8px 0 0 0; line-height: 1.5; }
      .section-title { color: #0f172a; border-left: 4px solid #2563eb; padding-left: 10px; margin-top: 1.5rem; }
      #writerDraftDemo .wd-q-row { border: 1px solid #d1fae5; border-radius: 8px; padding: 12px; margin-bottom: 10px; background: #fff; }
      #writerDraftDemo .wd-card { border: 1px solid #e2e8f0; border-radius: 10px; padding: 14px 16px; margin-bottom: 12px; background: #fff; box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06); }
      #writerDraftDemo .wd-card-sub { font-size: 0.85rem; color: #64748b; margin-bottom: 10px; line-height: 1.45; }
      #writerDraftDemo .wd-card-body { white-space: pre-wrap; line-height: 1.55; color: #0f172a; word-break: break-word; }
      #writerDraftDemo .wd-card-body.wd-fail { color: #b45309; }
      #writerDraftDemo .wd-char-badge { display: inline-block; margin-top: 10px; padding: 3px 10px; border-radius: 999px; background: #ecfdf5; color: #047857; font-size: 12px; font-weight: 600; border: 1px solid #a7f3d0; }
      #writerDraftDemo .wd-repo-tag { display: inline-block; margin: 4px 6px 0 0; padding: 4px 10px; border-radius: 999px; background: #ecfdf5; border: 1px solid #a7f3d0; color: #065f46; font-size: 12px; }
      #writerDraftDemo .wd-essay-yes { display: inline-block; padding: 6px 12px; border-radius: 8px; background: #dcfce7; color: #166534; font-size: 13px; font-weight: 600; border: 1px solid #86efac; }
      #writerDraftDemo .wd-essay-no { display: inline-block; padding: 6px 12px; border-radius: 8px; background: #f1f5f9; color: #64748b; font-size: 13px; border: 1px solid #e2e8f0; }
      #writerDraftDemo #writerDraftErrorArea { display: none; margin-top: 12px; padding: 12px; border-radius: 8px; background: #fef2f2; border: 1px solid #fecaca; color: #991b1b; font-size: 14px; }
      #writerDraftDemo #writerErrorJson { margin-top: 8px; background: #fff; color: #334155; border: 1px solid #e2e8f0; }
      #repoCardsGrid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
        gap: 14px;
        margin-top: 12px;
      }
      .repo-card {
        border: 1px solid #bfdbfe;
        border-radius: 10px;
        padding: 12px 14px;
        background: #fff;
        box-shadow: 0 1px 3px rgba(37, 99, 235, 0.08);
      }
      .repo-card h4 { margin: 0 0 8px 0; font-size: 0.95rem; color: #0f172a; word-break: break-all; }
      .repo-card .repo-card-actions { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px; }
      .repo-card .repo-tree-wrap {
        max-height: 240px;
        overflow: auto;
        border: 1px solid #e2e8f0;
        border-radius: 6px;
        padding: 6px 8px;
        margin: 8px 0;
        font-size: 13px;
        background: #f8fafc;
      }
      .repo-card .repo-card-status { font-size: 12px; color: #64748b; margin-top: 6px; min-height: 1.2em; }
      .repo-card .repo-save-ok { color: #15803d; font-size: 12px; font-weight: 600; }
      #btnEmbedAllRepos { font-size: 15px; padding: 12px 18px; }
      .repo-card-tabs { display: flex; flex-wrap: wrap; gap: 4px; margin: 10px 0 8px 0; font-size: 13px; border-bottom: 1px solid #e2e8f0; padding-bottom: 4px; }
      .repo-tab-btn { border: none; border-bottom: 2px solid transparent; background: transparent; cursor: pointer; padding: 6px 10px; margin-top: 2px; color: #64748b; }
      .repo-tab-btn.repo-tab-active { font-weight: 700; border-bottom-color: #2563eb; color: #1e40af; }
      .repo-tab-panel { display: none; }
      .repo-tab-panel.repo-tab-visible { display: block; }
      .repo-card-error { margin: 8px 0; padding: 8px 10px; border-radius: 6px; background: #fef2f2; border: 1px solid #fecaca; color: #991b1b; font-size: 12px; display: none; }
      .repo-tab-panel .repoBranchRef { width: 100%; max-width: 260px; padding: 6px 8px; border-radius: 4px; border: 1px solid #cbd5e1; font-size: 12px; }

      .repo-view-pre { max-height: 220px; overflow: auto; font-size: 12px; margin-top: 8px; }
      .repo-commits-pre { max-height: 220px; overflow: auto; font-size: 12px; margin-top: 8px; }
    </style>
  </head>
  <body>
    <h2>Autofolio Dev Dashboard</h2>
    <p class="hint">OAuth · GitHub API · 선택 레포/assets · <strong>코드 임베딩(Chroma)</strong> · <strong>채용공고 parse → job_id</strong> · <strong>자소서 Draft</strong> 개발용 화면입니다.</p>
    <div style="margin-bottom: 12px;">
      <button id="loginBtn">GitHub 로그인</button>
      <button id="logoutBtn">로그아웃</button>
    </div>
    <div style="margin-bottom: 12px;">
      <strong>Status:</strong>
      <span id="status">loading...</span>
    </div>
    <h3>/api/me</h3>
    <pre id="me"></pre>

    <hr style="margin: 24px 0;" />
    <h2 class="section-title" style="margin-top: 0;">GitHub API · 선택 assets</h2>

    <div style="margin-bottom: 12px;">
      <button id="btnRepos">GET /api/github/repos</button>
      <button id="btnSelectedRepos">GET /api/user/selected-repos</button>
    </div>
    <pre id="repos"></pre>
    <pre id="selectedRepos"></pre>

    <div style="margin-top: 12px; margin-bottom: 18px;">
      <h3>내 레포 선택 (저장된 레포 만들기)</h3>
      <div id="repoList" style="margin-bottom: 10px;"></div>
      <button id="btnSaveSelectedRepos">선택 레포 저장</button>
      <button id="btnLoadSelectedRepos">저장된 레포 불러오기</button>
    </div>

    <section class="demo-panel" id="embeddingDemo" aria-labelledby="embed-demo-title">
      <h2 id="embed-demo-title"><span class="tag">NEW</span> GitHub 코드 임베딩 데모</h2>
      <p class="hint">
        저장된 <strong>선택 레포 전체</strong>를 카드로 보여 줍니다. 레포마다 파일 트리를 불러 체크한 뒤
        <strong>전체 임베딩</strong>으로 순서대로 저장 → SQLite 동기화 → 임베딩을 실행합니다.
        Chroma <code>user_assets_{user_id}</code> · <code>.env</code>의 <code>OPENAI_API_KEY</code> 참고.
      </p>
      <ol class="demo-steps">
        <li><strong>GitHub 로그인</strong> → 위에서 레포 체크 → <strong>선택 레포 저장</strong></li>
        <li>카드 탭 <strong>파일 선택</strong>: 트리 로드 → 체크 → 저장 · <strong>파일 보기</strong>·<strong>커밋</strong>은 같은 레포에서 조회</li>
        <li><strong>전체 임베딩</strong>: 각 레포마다 PUT assets → sync-from-assets → POST embedding (DB)</li>
      </ol>
      <div style="margin-bottom: 12px;">
        <label for="embedRef"><strong>ref</strong> (브랜치·SHA, 선택):</label>
        <input id="embedRef" style="width: 240px; padding: 8px; border-radius: 6px; border: 1px solid #cbd5e1;" placeholder="예: main" />
        <div style="margin-top: 10px;">
          <label style="cursor: pointer;">
            <input type="checkbox" id="embedIncludeSummaries" checked />
            응답에 <strong>LLM 요약문</strong> 포함 (<code>include_summaries</code>)
          </label>
        </div>
      </div>
      <div style="margin-bottom: 14px;">
        <button type="button" class="btn-demo-primary" id="btnEmbedAllRepos">전체 임베딩 (저장된 레포 순서)</button>
        <span class="hint" style="margin-left: 10px;">각 카드에 진행 상태가 표시됩니다.</span>
      </div>
      <p class="hint">
        API: <code>PUT /api/user/selected-repo-assets</code> ·
        <code>POST /api/user/asset-hierarchy/sync-from-assets</code> ·
        <code>POST /api/github/repos/&lt;owner%2Frepo&gt;/embedding</code>
      </p>
      <div id="repoCardsGrid" aria-label="저장된 레포 카드"></div>
      <h4 style="margin: 18px 0 6px 0; color: #334155;">마지막 임베딩 응답</h4>
      <pre id="embeddingResult"></pre>
    </section>

    <section class="demo-panel" id="writerDraftDemo" aria-labelledby="writer-draft-title" style="border-color: #6ee7b7; background: linear-gradient(165deg, #ecfdf5 0%, #f8fafc 55%);">
      <h2 id="writer-draft-title"><span class="tag" style="background:#059669;">Writer</span> 자소서 초안 생성 (Writer 그래프)</h2>
      <p class="hint">
        <strong>GitHub 로그인</strong> 필수. 아래 <code>job_id</code>는 선택이며, 아래 <strong>채용공고 저장</strong>으로 받은 값을 쓰면 공고 맥락이 붙습니다.
        코드 RAG는 위 <strong>임베딩 데모</strong>를 먼저 완료하는 것이 좋습니다.
      </p>
      <div style="margin-bottom: 12px;">
        <label for="draftJobSelect">공고 선택 (최근 저장)</label><br />
        <select id="draftJobSelect" style="width: min(100%, 420px); padding: 8px; border-radius: 6px; border: 1px solid #cbd5e1; max-width: 100%;">
          <option value="">공고 맥락 없이</option>
        </select>
        <p class="hint" style="margin-top: 6px;">목록에는 <strong>기업명 · 포지션</strong>이 보이며, 초안 요청 시에는 DB의 <code>job_id</code>(UUID)가 전송됩니다.</p>
      </div>
      <div style="margin-bottom: 8px;">
        <span style="font-weight:600;color:#0f172a;">문항</span>
        <span class="hint" style="margin-left:8px;">1~5개 · 각 문항마다 본문·글자 제한을 지정합니다.</span>
      </div>
      <div id="writerQuestionList"></div>
      <div style="display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:14px;">
        <button type="button" class="btn-demo-ghost" id="btnWriterAddQ">문항 추가</button>
        <button type="button" class="btn-demo-primary" id="btnWriterDraft" style="background:#059669 !important; border-color:#047857 !important;">초안 생성</button>
      </div>
      <div id="writerDraftErrorArea" aria-live="polite">
        <div id="writerErrorLine"></div>
        <pre id="writerErrorJson"></pre>
      </div>
      <h4 style="margin: 16px 0 10px 0; color: #334155;">결과</h4>
      <div id="writerDraftCards"></div>
      <div id="writerUsedAssetsBlock" style="margin-top: 16px; padding-top: 14px; border-top: 1px solid #d1fae5;">
        <div style="font-size: 0.9rem; font-weight: 600; color: #334155; margin-bottom: 8px;">참조 레포</div>
        <div id="writerRepoTags" class="hint" style="color:#64748b;">참조 레포 없음</div>
        <div style="margin-top: 12px;">
          <span id="writerEssaysBadge" class="wd-essay-no">합격 자소서 미참조</span>
          <div id="writerEssaysList" class="wd-essay-list" style="margin-top: 8px; font-size: 0.88rem; color: #334155; padding-left: 8px;"></div>
        </div>
      </div>
    </section>

    <section class="demo-panel" id="jobParseDemo" aria-labelledby="job-parse-title" style="border-color: #fcd34d; background: linear-gradient(165deg, #fffbeb 0%, #f8fafc 55%);">
      <h2 id="job-parse-title"><span class="tag" style="background:#d97706;">Jobs</span> 채용공고 저장 (parse)</h2>
      <p class="hint">
        <code>POST /api/jobs/parse</code>로 SQLite <code>jobs</code> 테이블에 공고를 넣고 <strong>job_id</strong>를 받습니다.
        성공 시 위 <strong>자소서 초안 생성</strong>의 <strong>job_id</strong> 입력칸에 자동으로 채웁니다. 이후 <code>POST /api/cover-letter/draft</code>에 같은 id를 넘기면 공고 맥락이 붙습니다.
      </p>
      <div style="margin-bottom: 10px;">
        <label><input type="radio" name="jobSource" value="manual" checked /> manual (직접 입력)</label>
        &nbsp;&nbsp;
        <label><input type="radio" name="jobSource" value="url" /> url (페이지 가져오기 · OPENAI 있으면 구조화)</label>
      </div>
      <div id="jobManualFields">
        <div style="margin-bottom: 6px;"><label>company_name *</label><br />
          <input id="jobCompanyName" style="width: min(100%, 420px); padding: 8px; border-radius: 6px; border: 1px solid #cbd5e1;" placeholder="기업명" />
        </div>
        <div style="margin-bottom: 6px;"><label>position_title *</label><br />
          <input id="jobPositionTitle" style="width: min(100%, 420px); padding: 8px; border-radius: 6px; border: 1px solid #cbd5e1;" placeholder="포지션명" />
        </div>
        <div style="margin-bottom: 6px;"><label>company_persona (선택)</label><br />
          <input id="jobCompanyPersona" style="width: min(100%, 420px); padding: 8px; border-radius: 6px; border: 1px solid #cbd5e1;" placeholder="기업 인재상" />
        </div>
        <div style="margin-bottom: 6px;"><label>duties (한 줄에 한 항목)</label><br />
          <textarea id="jobDuties" rows="3" style="width: min(100%, 560px); padding: 8px;" placeholder="담당 업무"></textarea>
        </div>
        <div style="margin-bottom: 6px;"><label>requirements</label><br />
          <textarea id="jobRequirements" rows="2" style="width: min(100%, 560px); padding: 8px;" placeholder="자격 요건 (줄 단위)"></textarea>
        </div>
        <div style="margin-bottom: 10px;"><label>preferences</label><br />
          <textarea id="jobPreferences" rows="2" style="width: min(100%, 560px); padding: 8px;" placeholder="우대 사항 (줄 단위)"></textarea>
        </div>
      </div>
      <div id="jobUrlField" style="display: none; margin-bottom: 10px;">
        <label>채용공고 URL *</label><br />
        <input id="jobUrl" style="width: min(100%, 520px); padding: 8px; border-radius: 6px; border: 1px solid #cbd5e1;" placeholder="https://..." />
      </div>
      <button type="button" class="btn-demo-primary" id="btnJobParse" style="background:#d97706 !important; border-color:#b45309 !important;">POST /api/jobs/parse</button>
      <h4 style="margin: 14px 0 6px 0; color: #334155;">응답</h4>
      <pre id="jobParseResult"></pre>
    </section>

    <script>
      const setStatus = (text) => { document.getElementById('status').textContent = text; };
      const setMe = (obj) => { document.getElementById('me').textContent = obj ? JSON.stringify(obj, null, 2) : ''; };
      const setPre = (id, obj) => {
        const el = document.getElementById(id);
        if (!el) return;
        el.textContent = obj ? JSON.stringify(obj, null, 2) : '';
      };

      // 스크립트 실행 여부 확인용: 이 라인이 보이면 JS 파싱/실행이 정상인 것
      setStatus('script loaded');

      // JS 런타임 에러가 나도 화면이 계속 로딩처럼 보이지 않게 잡는다.
      window.addEventListener('error', (e) => {
        const msg = (e && e.message) ? e.message : ((e && e.error && e.error.message) ? e.error.message : 'unknown');
        setStatus(`JS error: ${msg}`);
      });

      const safeOnClick = (id, handler) => {
        const el = document.getElementById(id);
        if (!el) {
          setStatus(`missing element: ${id}`);
          return;
        }
        el.addEventListener('click', handler);
      };

      const selectedRepoFullNames = new Set();
      let lastRepos = [];

      const selectedRepoIdByFullName = new Map();
      /** full_name → true(임베딩됨) / false. 미설정은 미임베딩 표시. */
      const embeddingStatusCache = new Map();
      let savedRepoItems = [];

      /** full_name → 레포 카드 상태 (임베딩 데모 그리드) */
      const repoCardMap = new Map();

      const normRepoPath = (p) => {
        if (!p) return '';
        let s = String(p).trim();
        // leading slash 제거
        s = s.replace(/^\/+/, '');
        // trailing slash 제거
        s = s.replace(/\/+$/, '');
        return s;
      };

      const assetKey = (assetType, repoPath) => `${assetType}:${normRepoPath(repoPath)}`;

      const cardInputId = (fullName, keyStr) => `c_${sanitizeId(fullName)}__${sanitizeId(keyStr)}`;

      const sanitizeId = (s) => String(s).replace(/[^a-zA-Z0-9_-]/g, '_');

      function renderRepoCheckboxes(repos) {
        lastRepos = repos || [];
        const repoList = document.getElementById('repoList');
        repoList.innerHTML = '';

        if (!lastRepos.length) {
          repoList.textContent = '레포가 없습니다.';
          return;
        }

        lastRepos.forEach((r, idx) => {
          const fullName = r.full_name;
          const inputId = `repo_${sanitizeId(fullName)}_${idx}`;

          const wrapper = document.createElement('div');
          wrapper.style.marginBottom = '6px';

          const cb = document.createElement('input');
          cb.type = 'checkbox';
          cb.id = inputId;
          cb.checked = selectedRepoFullNames.has(fullName);
          cb.addEventListener('change', () => {
            if (cb.checked) selectedRepoFullNames.add(fullName);
            else selectedRepoFullNames.delete(fullName);

          });

          const label = document.createElement('label');
          label.htmlFor = inputId;
          label.textContent = ` ${fullName}  (${r.language || 'n/a'}, pushed: ${r.pushed_at || 'n/a'})`;

          wrapper.appendChild(cb);
          wrapper.appendChild(label);
          repoList.appendChild(wrapper);
        });
      }

      function ensureRepoCardState(fullName, selectedRepoId) {
        const fn = String(fullName || '').trim();
        if (!fn) return null;
        if (!repoCardMap.has(fn)) {
          repoCardMap.set(fn, {
            selected_repo_id: selectedRepoId,
            activeTab: 'files',
            fileTreeRoot: null,
            selectedAssetKeys: new Set(),
            expandedFolderPaths: new Set(),
            lastFilesTreeItems: [],
            treeWrapVisible: false,
            batchStatus: '',
            saveOk: false,
          });
        } else {
          repoCardMap.get(fn).selected_repo_id = selectedRepoId;
        }
        return repoCardMap.get(fn);
      }

      function getCardState(fullName) {
        const fn = String(fullName || '').trim();
        return repoCardMap.get(fn) || null;
      }

      async function loadSelectedReposUI() {
        const { res, data } = await loadJson('/api/user/selected-repos');
        if (!res.ok) {
          setStatus('선택 레포 불러오기 실패');
          setPre('selectedRepos', data);
          return false;
        }

        const items = data.selected_repos || [];
        savedRepoItems = items;

        selectedRepoFullNames.clear();
        selectedRepoIdByFullName.clear();
        repoCardMap.clear();
        items.forEach((it) => {
          if (it && it.full_name) {
            selectedRepoFullNames.add(it.full_name);
            selectedRepoIdByFullName.set(it.full_name, it.id);
            ensureRepoCardState(it.full_name, it.id);
          }
        });
        setPre('selectedRepos', data);

        renderAllRepoCards();

        return true;
      }

      async function loadReposUI() {
        const { res, data } = await loadJson('/api/github/repos');
        if (!res.ok) {
          setStatus('레포 목록 불러오기 실패');
          setPre('repos', data);
          return false;
        }

        setPre('repos', data);
        const repos = data.repos || [];
        renderRepoCheckboxes(repos);
        return true;
      }

      function getParentPath(p) {
        const s = normRepoPath(p);
        if (!s) return '';
        const idx = s.lastIndexOf('/');
        if (idx <= 0) return '';
        return s.slice(0, idx);
      }

      function buildFileTreeHierarchy(items) {
        // root: repo root (path = "")
        const root = { type: 'dir', path: '', children: [] };
        const nodeByPath = new Map();
        nodeByPath.set('', root);

        const ensureDir = (dirPath) => {
          const p = normRepoPath(dirPath);
          if (!nodeByPath.has(p)) {
            nodeByPath.set(p, { type: 'dir', path: p, children: [] });
          }
          return nodeByPath.get(p);
        };

        const ensureFile = (filePath) => {
          const p = normRepoPath(filePath);
          if (!nodeByPath.has(p)) {
            nodeByPath.set(p, { type: 'file', path: p, children: [] });
          }
          return nodeByPath.get(p);
        };

        (items || []).forEach((it) => {
          if (!it) return;
          const rawPath = it.path || '';
          const p = normRepoPath(rawPath);
          if (!p) return;

          const isDir = it.type === 'dir';
          if (isDir) {
            ensureDir(p);
          } else {
            ensureFile(p);
          }

          // ancestors(폴더) 보장
          const parts = p.split('/').filter(Boolean);
          if (parts.length > 1) {
            let cur = '';
            for (let i = 0; i < parts.length - 1; i++) {
              cur = cur ? `${cur}/${parts[i]}` : parts[i];
              ensureDir(cur);
            }
          }
        });

        // parent-child 연결
        const entries = Array.from(nodeByPath.entries());
        entries.forEach(([path, node]) => {
          if (!path) return; // root
          const parentPath = getParentPath(path);
          const parent = nodeByPath.get(parentPath);
          if (!parent) return;

          if (!parent.children.some((ch) => ch.path === node.path && ch.type === node.type)) {
            parent.children.push(node);
          }
        });

        const sortRec = (node) => {
          if (node.type === 'dir') {
            node.children.sort((a, b) => {
              const ad = a.type === 'dir' ? 0 : 1;
              const bd = b.type === 'dir' ? 0 : 1;
              if (ad !== bd) return ad - bd;
              return a.path.localeCompare(b.path);
            });
            node.children.forEach(sortRec);
          }
        };
        sortRec(root);
        return root;
      }

      function collectDescendantAssetKeys(node) {
        const keys = [];
        const visit = (n) => {
          if (n.path) {
            if (n.type === 'dir') keys.push(assetKey('folder', n.path));
            else if (n.type === 'file') keys.push(assetKey('code', n.path));
          }
          if (n.type === 'dir') {
            (n.children || []).forEach(visit);
          }
        };
        visit(node);
        return keys;
      }

      function setCardRepoError(fullName, text) {
        const el = document.getElementById(`repoCardErr_${sanitizeId(fullName)}`);
        if (el) {
          el.textContent = text || '';
          el.style.display = text ? 'block' : 'none';
        }
      }

      function clearCardRepoError(fullName) {
        setCardRepoError(fullName, '');
      }

      function getCardBranchRef(fullName) {
        const el = document.getElementById(`repoBranchRef_${sanitizeId(fullName)}`);
        return (el && el.value) ? String(el.value).trim() : '';
      }

      async function fetchJsonForCard(fullName, url) {
        clearCardRepoError(fullName);
        try {
          const res = await fetch(url, { credentials: 'include' });
          const data = await res.json().catch(() => ({}));
          return { res, data };
        } catch (e) {
          setCardRepoError(fullName, `접근 실패: ${String(e)}`);
          return null;
        }
      }

      async function fetchTextForCard(fullName, url) {
        clearCardRepoError(fullName);
        try {
          const res = await fetch(url, { credentials: 'include' });
          const text = await res.text();
          return { res, text };
        } catch (e) {
          setCardRepoError(fullName, `접근 실패: ${String(e)}`);
          return null;
        }
      }

      function switchRepoCardTab(fullName, tabId) {
        const st = getCardState(fullName);
        if (st) st.activeTab = tabId;
        ['files', 'view', 'commits'].forEach((t) => {
          const p = document.getElementById(`repoTabPanel_${sanitizeId(fullName)}_${t}`);
          if (p) {
            p.classList.toggle('repo-tab-visible', t === tabId);
          }
          const b = document.getElementById(`repoTabBtn_${sanitizeId(fullName)}_${t}`);
          if (b) b.classList.toggle('repo-tab-active', t === tabId);
        });
        if (tabId === 'view') refreshRepoViewSelect(fullName);
      }

      function refreshRepoViewSelect(fullName) {
        const st = getCardState(fullName);
        const sel = document.getElementById(`repoViewSelect_${sanitizeId(fullName)}`);
        if (!sel || !st) return;
        const paths = Array.from(st.selectedAssetKeys)
          .filter((k) => k.startsWith('code:'))
          .map((k) => k.slice('code:'.length))
          .filter((p) => p)
          .sort((a, b) => a.localeCompare(b));
        const prev = sel.value;
        sel.innerHTML = '';
        paths.forEach((p) => {
          const o = document.createElement('option');
          o.value = p;
          o.textContent = p;
          sel.appendChild(o);
        });
        if (paths.length && paths.includes(prev)) sel.value = prev;
        else if (paths.length) sel.value = paths[0];
      }

      async function loadRepoCardFileContent(fullName) {
        const sel = document.getElementById(`repoViewSelect_${sanitizeId(fullName)}`);
        const pre = document.getElementById(`repoViewPre_${sanitizeId(fullName)}`);
        if (!pre) return;
        const path = sel ? sel.value : '';
        if (!path) {
          pre.textContent = '선택된 코드 파일이 없습니다. 파일 선택 탭에서 체크하세요.';
          return;
        }
        const ref = getCardBranchRef(fullName);
        const enc = String(fullName).replace(/ /g, '%20');
        const pathQ = encodeURIComponent(path);
        let url = `/api/github/repos/${enc}/contents?path=${pathQ}&encoding=raw`;
        if (ref) url += `&ref=${encodeURIComponent(ref)}`;
        const result = await fetchTextForCard(fullName, url);
        if (!result) return;
        const { res, text } = result;
        if (!res.ok) {
          pre.textContent = text;
          setCardRepoError(fullName, `접근 실패: HTTP ${res.status}`);
          return;
        }
        clearCardRepoError(fullName);
        pre.textContent = text;
      }

      async function loadRepoCardCommits(fullName) {
        const authorEl = document.getElementById(`repoCommitsAuthor_${sanitizeId(fullName)}`);
        const perPageEl = document.getElementById(`repoCommitsPerPage_${sanitizeId(fullName)}`);
        const pre = document.getElementById(`repoCommitsPre_${sanitizeId(fullName)}`);
        if (!pre) return;
        const author = (authorEl && authorEl.value) ? String(authorEl.value).trim() : '';
        const enc = String(fullName).replace(/ /g, '%20');
        const params = new URLSearchParams();
        const rawPer = (perPageEl && perPageEl.value !== undefined && perPageEl.value !== null && String(perPageEl.value).trim() !== '')
          ? parseInt(String(perPageEl.value).trim(), 10)
          : 10;
        const perPage = Number.isFinite(rawPer) ? Math.min(100, Math.max(1, rawPer)) : 10;
        params.set('per_page', String(perPage));
        params.set('page', '1');
        if (author) params.set('author', author);
        const url = `/api/github/repos/${enc}/commits?${params.toString()}`;
        const result = await fetchJsonForCard(fullName, url);
        if (!result) return;
        const { res, data } = result;
        if (!res.ok) {
          pre.textContent = JSON.stringify(data, null, 2);
          setCardRepoError(fullName, `접근 실패: HTTP ${res.status}`);
          return;
        }
        clearCardRepoError(fullName);
        const commits = data.commits || [];
        const top = commits
          .slice(0, 10)
          .map((c) => {
            const shaFull = (c.sha !== undefined && c.sha !== null) ? String(c.sha) : '';
            const sha7 = shaFull ? shaFull.slice(0, 7) : '';
            const cm = (c.message !== undefined && c.message !== null) ? String(c.message) : '';
            const cd = (c.date !== undefined && c.date !== null) ? String(c.date) : '';
            const fc = (c.files_changed !== undefined && c.files_changed !== null) ? c.files_changed : 0;
            return `${sha7}  ${cm}  ${cd}  files_changed: ${fc}`;
          })
          .join('\n');
        pre.textContent = top || '(커밋 없음)';
      }

      function embeddingBadgeFor(fullName) {
        const fn = fullName ? String(fullName) : '';
        const ok = embeddingStatusCache.get(fn) === true;
        const span = document.createElement('span');
        span.style.marginLeft = '8px';
        span.style.fontSize = '0.82rem';
        span.style.whiteSpace = 'nowrap';
        if (ok) {
          span.style.color = '#15803d';
          span.textContent = '✅ 임베딩됨';
        } else {
          span.style.color = '#64748b';
          span.textContent = '⬜ 미임베딩';
        }
        return span;
      }

      function setCardStatusLine(fullName, text) {
        const el = document.getElementById(`repoCardStatus_${sanitizeId(fullName)}`);
        if (el) el.textContent = text || '';
        const st = getCardState(fullName);
        if (st) st.batchStatus = text || '';
      }

      function setCardSaveOk(fullName, ok) {
        const el = document.getElementById(`repoCardSaveOk_${sanitizeId(fullName)}`);
        if (el) el.textContent = ok ? '저장됨 ✓' : '';
        const st = getCardState(fullName);
        if (st) st.saveOk = !!ok;
      }

      async function hydrateCardAssetsFromServer(fullName) {
        const st = getCardState(fullName);
        if (!st) return;
        const url = `/api/user/selected-repo-assets?selected_repo_id=${encodeURIComponent(String(st.selected_repo_id))}`;
        const result = await fetchJsonForCard(fullName, url);
        if (!result) return;
        const { res, data } = result;
        if (!res.ok) return;
        st.selectedAssetKeys.clear();
        (data.selected_repo_assets || []).forEach((it) => {
          if (!it) return;
          if (!it.asset_type || it.repo_path === undefined) return;
          st.selectedAssetKeys.add(assetKey(it.asset_type, it.repo_path));
        });
      }

      function renderFilesTreeForRepo(fullName) {
        const st = getCardState(fullName);
        const treeList = document.getElementById(`repoTree_${sanitizeId(fullName)}`);
        if (!treeList || !st) return;
        treeList.innerHTML = '';

        if (!st.fileTreeRoot) {
          treeList.textContent = '「파일 트리 로드」를 눌러주세요.';
          return;
        }

        const renderNode = (node, level) => {
          const row = document.createElement('div');
          row.style.marginLeft = `${level * 14}px`;
          row.style.display = 'flex';
          row.style.alignItems = 'center';
          row.style.gap = '6px';

          if (node.type === 'dir') {
            const expanded = st.expandedFolderPaths.has(node.path);
            const arrow = document.createElement('span');
            arrow.style.cursor = 'pointer';
            arrow.textContent = expanded ? '▾' : '▸';
            arrow.addEventListener('click', () => {
              if (expanded) st.expandedFolderPaths.delete(node.path);
              else st.expandedFolderPaths.add(node.path);
              renderFilesTreeForRepo(fullName);
            });

            const k = assetKey('folder', node.path);
            const inputId = cardInputId(fullName, k);
            const cb = document.createElement('input');
            cb.type = 'checkbox';
            cb.id = inputId;
            cb.checked = st.selectedAssetKeys.has(k);
            cb.addEventListener('change', () => {
              const allKeys = collectDescendantAssetKeys(node);
              if (cb.checked) allKeys.forEach((x) => st.selectedAssetKeys.add(x));
              else allKeys.forEach((x) => st.selectedAssetKeys.delete(x));
              renderFilesTreeForRepo(fullName);
              setCardSaveOk(fullName, false);
              refreshRepoViewSelect(fullName);
            });

            const nameEl = document.createElement('span');
            nameEl.style.cursor = 'pointer';
            const name = node.path ? node.path.split('/').pop() : '(root)';
            nameEl.textContent = name;
            nameEl.addEventListener('click', () => {
              if (expanded) st.expandedFolderPaths.delete(node.path);
              else st.expandedFolderPaths.add(node.path);
              renderFilesTreeForRepo(fullName);
            });

            row.appendChild(arrow);
            row.appendChild(cb);
            row.appendChild(nameEl);
            treeList.appendChild(row);

            if (st.expandedFolderPaths.has(node.path)) {
              (node.children || []).forEach((ch) => renderNode(ch, level + 1));
            }
          } else {
            const k = assetKey('code', node.path);
            const inputId = cardInputId(fullName, k);
            const cb = document.createElement('input');
            cb.type = 'checkbox';
            cb.id = inputId;
            cb.checked = st.selectedAssetKeys.has(k);
            cb.addEventListener('change', () => {
              if (cb.checked) st.selectedAssetKeys.add(k);
              else st.selectedAssetKeys.delete(k);
              setCardSaveOk(fullName, false);
              refreshRepoViewSelect(fullName);
            });

            const label = document.createElement('label');
            label.htmlFor = inputId;
            label.textContent = ` ${node.path.split('/').pop()}`;
            label.addEventListener('click', () => {
              switchRepoCardTab(fullName, 'view');
              refreshRepoViewSelect(fullName);
              const sel = document.getElementById(`repoViewSelect_${sanitizeId(fullName)}`);
              if (sel) {
                sel.value = node.path;
                loadRepoCardFileContent(fullName);
              }
            });

            row.appendChild(cb);
            row.appendChild(label);
            treeList.appendChild(row);
          }
        };

        (st.fileTreeRoot.children || []).forEach((ch) => renderNode(ch, 0));
      }

      function toggleCardTreePanel(fullName, btnEl) {
        const st = getCardState(fullName);
        const wrap = document.getElementById(`repoTreeWrap_${sanitizeId(fullName)}`);
        if (!st || !wrap) return;
        st.treeWrapVisible = !st.treeWrapVisible;
        wrap.style.display = st.treeWrapVisible ? 'block' : 'none';
        if (btnEl) btnEl.textContent = st.treeWrapVisible ? '파일 트리 접기 ▾' : '파일 트리 펼치기 ▸';
      }

      async function loadFilesTreeForCard(fullName) {
        const st = getCardState(fullName);
        if (!st) return;
        setCardStatusLine(fullName, '트리 로딩 중...');
        setCardSaveOk(fullName, false);
        const enc = String(fullName).replace(/ /g, '%20');
        let url = `/api/github/repos/${enc}/files?path=${encodeURIComponent('/')}`;
        const ref = getCardBranchRef(fullName);
        if (ref) url += `&ref=${encodeURIComponent(ref)}`;
        const result = await fetchJsonForCard(fullName, url);
        if (!result) {
          st.fileTreeRoot = null;
          renderFilesTreeForRepo(fullName);
          setCardStatusLine(fullName, '실패 ❌ (트리 로드)');
          return;
        }
        const { res, data } = result;
        if (!res.ok) {
          st.fileTreeRoot = null;
          renderFilesTreeForRepo(fullName);
          setCardRepoError(fullName, `접근 실패: ${(data && data.message) ? data.message : res.status}`);
          setCardStatusLine(fullName, '실패 ❌ (트리 로드)');
          return;
        }
        st.lastFilesTreeItems = data.tree || [];
        st.fileTreeRoot = buildFileTreeHierarchy(st.lastFilesTreeItems);
        st.expandedFolderPaths.clear();
        await hydrateCardAssetsFromServer(fullName);
        st.treeWrapVisible = true;
        const wrap = document.getElementById(`repoTreeWrap_${sanitizeId(fullName)}`);
        if (wrap) wrap.style.display = 'block';
        const toggleBtn = document.getElementById(`repoToggleBtn_${sanitizeId(fullName)}`);
        if (toggleBtn) toggleBtn.textContent = '파일 트리 접기 ▾';
        clearCardRepoError(fullName);
        renderFilesTreeForRepo(fullName);
        setCardStatusLine(fullName, '');
        setStatus(`파일 트리 로드 완료: ${fullName}`);
      }

      async function saveRepoCardAssets(fullName) {
        const st = getCardState(fullName);
        if (!st) return;
        const assets = Array.from(st.selectedAssetKeys).map((key) => {
          const idx = key.indexOf(':');
          return { asset_type: key.slice(0, idx), repo_path: key.slice(idx + 1) };
        });
        if (!assets.length) {
          setCardStatusLine(fullName, '선택된 파일이 없습니다.');
          return;
        }
        setCardStatusLine(fullName, '저장 중...');
        try {
          const res = await fetch('/api/user/selected-repo-assets', {
            method: 'PUT',
            headers: { 'content-type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ selected_repo_id: st.selected_repo_id, assets }),
          });
          const data = await res.json().catch(() => ({}));
          if (!res.ok) {
            setCardRepoError(fullName, `접근 실패: ${(data && data.message) ? data.message : res.status}`);
            setCardStatusLine(fullName, '실패 ❌ (저장)');
            setPre('embeddingResult', { http_status: res.status, response: data });
            return;
          }
          clearCardRepoError(fullName);
          setCardSaveOk(fullName, true);
          setCardStatusLine(fullName, '');
          setStatus(`assets 저장 완료: ${fullName}`);
        } catch (e) {
          setCardRepoError(fullName, `접근 실패: ${String(e)}`);
          setCardStatusLine(fullName, '실패 ❌');
          setPre('embeddingResult', { error: String(e) });
        }
      }

      async function syncRepoCardHistory(fullName) {
        const st = getCardState(fullName);
        if (!st) return;
        setCardStatusLine(fullName, 'SQLite 동기화 중...');
        clearCardRepoError(fullName);
        try {
          const res = await fetch('/api/user/asset-hierarchy/sync-from-assets', {
            method: 'POST',
            credentials: 'include',
            headers: { 'content-type': 'application/json' },
            body: JSON.stringify({ selected_repo_id: st.selected_repo_id }),
          });
          const data = await res.json().catch(() => ({}));
          if (!res.ok) {
            setCardRepoError(fullName, `접근 실패: ${(data && data.message) ? data.message : res.status}`);
            setCardStatusLine(fullName, '실패 ❌ (동기화)');
            setPre('embeddingResult', { step: 'sync-from-assets', repo: fullName, http_status: res.status, response: data });
            return;
          }
          clearCardRepoError(fullName);
          setCardStatusLine(fullName, '');
          setStatus(`SQLite 동기화 완료: ${fullName}`);
          setPre('embeddingResult', { step: 'sync-from-assets', repo: fullName, http_status: res.status, response: data });
        } catch (e) {
          setCardRepoError(fullName, `접근 실패: ${String(e)}`);
          setCardStatusLine(fullName, '실패 ❌');
          setPre('embeddingResult', { error: String(e), repo: fullName });
        }
      }

      async function embedRepoCardOnly(fullName) {
        const refRaw = (document.getElementById('embedRef')?.value || '').trim();
        const includeSummaries = document.getElementById('embedIncludeSummaries')?.checked;
        const st = getCardState(fullName);
        if (!st) return;
        setCardStatusLine(fullName, '임베딩 중...');
        focusEmbeddingPanel(`임베딩: ${fullName}…`);
        clearCardRepoError(fullName);
        try {
          const assets = Array.from(st.selectedAssetKeys).map((key) => {
            const idx = key.indexOf(':');
            return { asset_type: key.slice(0, idx), repo_path: key.slice(idx + 1) };
          });
          if (assets.length) {
            const resPut = await fetch('/api/user/selected-repo-assets', {
              method: 'PUT',
              credentials: 'include',
              headers: { 'content-type': 'application/json' },
              body: JSON.stringify({ selected_repo_id: st.selected_repo_id, assets }),
            });
            const dataPut = await resPut.json().catch(() => ({}));
            if (!resPut.ok) {
              setCardStatusLine(fullName, '실패 ❌ (assets 저장)');
              setPre('embeddingResult', { step: 'PUT selected-repo-assets', repo: fullName, http_status: resPut.status, response: dataPut });
              setCardRepoError(fullName, `접근 실패: ${(dataPut && dataPut.message) ? dataPut.message : resPut.status}`);
              return;
            }
          }
          const resSync = await fetch('/api/user/asset-hierarchy/sync-from-assets', {
            method: 'POST',
            credentials: 'include',
            headers: { 'content-type': 'application/json' },
            body: JSON.stringify({ selected_repo_id: st.selected_repo_id }),
          });
          const dataSync = await resSync.json().catch(() => ({}));
          if (!resSync.ok) {
            setCardStatusLine(fullName, '실패 ❌ (asset_hierarchy)');
            setPre('embeddingResult', { step: 'sync-from-assets', repo: fullName, http_status: resSync.status, response: dataSync });
            setCardRepoError(fullName, `접근 실패: ${(dataSync && dataSync.message) ? dataSync.message : resSync.status}`);
            return;
          }
          const url = `/api/github/repos/${String(fullName).replace(/ /g, '%20')}/embedding`;
          const bodyPayload = { code_document_ids: [] };
          if (refRaw) bodyPayload.ref = refRaw;
          if (includeSummaries) bodyPayload.include_summaries = true;
          const resEmb = await fetch(url, {
            method: 'POST',
            credentials: 'include',
            headers: { 'content-type': 'application/json' },
            body: JSON.stringify(bodyPayload),
          });
          const dataEmb = await resEmb.json().catch(() => ({}));
          setPre('embeddingResult', { http_status: resEmb.status, repo: fullName, response: dataEmb });
          if (resEmb.ok) {
            const emb = (dataEmb && dataEmb.embedded !== undefined) ? Number(dataEmb.embedded) : 0;
            embeddingStatusCache.set(fullName, emb > 0);
            setCardStatusLine(fullName, emb > 0 ? '완료 ✅' : '완료 (embedded=0)');
          } else {
            setCardStatusLine(fullName, '실패 ❌ (임베딩)');
            setCardRepoError(fullName, `접근 실패: ${(dataEmb && dataEmb.message) ? dataEmb.message : resEmb.status}`);
          }
        } catch (e) {
          setCardRepoError(fullName, `접근 실패: ${String(e)}`);
          setCardStatusLine(fullName, '실패 ❌');
          setPre('embeddingResult', { error: String(e), repo: fullName });
        }
        renderAllRepoCards();
      }

      function renderAllRepoCards() {
        const grid = document.getElementById('repoCardsGrid');
        if (!grid) return;
        grid.innerHTML = '';

        if (!savedRepoItems.length) {
          grid.textContent = '저장된 레포가 없습니다. 위에서 레포를 체크한 뒤 「선택 레포 저장」을 하세요.';
          return;
        }

        savedRepoItems.forEach((it) => {
          if (!it || !it.full_name) return;
          const fn = it.full_name;
          ensureRepoCardState(fn, it.id);
          const st = getCardState(fn);

          const card = document.createElement('div');
          card.className = 'repo-card';
          card.dataset.repoFullName = fn;

          const titleRow = document.createElement('div');
          titleRow.style.display = 'flex';
          titleRow.style.alignItems = 'center';
          titleRow.style.flexWrap = 'wrap';
          titleRow.style.gap = '6px';
          const h4 = document.createElement('h4');
          h4.textContent = `[${fn}]`;
          titleRow.appendChild(h4);
          titleRow.appendChild(embeddingBadgeFor(fn));

          const at = st.activeTab || 'files';

          const refRow = document.createElement('div');
          refRow.style.marginBottom = '8px';
          const refLab = document.createElement('label');
          refLab.style.display = 'block';
          refLab.style.fontSize = '12px';
          refLab.style.color = '#64748b';
          refLab.textContent = 'ref (브랜치·SHA, 비우면 기본 브랜치 · 파일 트리·내용 보기 공통)';
          const refIn = document.createElement('input');
          refIn.type = 'text';
          refIn.className = 'repoBranchRef';
          refIn.id = `repoBranchRef_${sanitizeId(fn)}`;
          refIn.placeholder = '예: main';
          refRow.appendChild(refLab);
          refRow.appendChild(refIn);

          const tabRow = document.createElement('div');
          tabRow.className = 'repo-card-tabs';
          [['files', '파일 선택'], ['view', '파일 보기'], ['commits', '커밋']].forEach(([tid, lbl]) => {
            const b = document.createElement('button');
            b.type = 'button';
            b.className = 'repo-tab-btn' + (tid === at ? ' repo-tab-active' : '');
            b.id = `repoTabBtn_${sanitizeId(fn)}_${tid}`;
            b.textContent = lbl;
            b.addEventListener('click', () => switchRepoCardTab(fn, tid));
            tabRow.appendChild(b);
          });

          const errDiv = document.createElement('div');
          errDiv.className = 'repo-card-error';
          errDiv.id = `repoCardErr_${sanitizeId(fn)}`;

          const panelFiles = document.createElement('div');
          panelFiles.className = 'repo-tab-panel' + (at === 'files' ? ' repo-tab-visible' : '');
          panelFiles.id = `repoTabPanel_${sanitizeId(fn)}_files`;

          const actions = document.createElement('div');
          actions.className = 'repo-card-actions';

          const btnLoad = document.createElement('button');
          btnLoad.type = 'button';
          btnLoad.className = 'btn-demo-ghost';
          btnLoad.textContent = '파일 트리 로드';
          btnLoad.addEventListener('click', () => { loadFilesTreeForCard(fn); });

          const btnToggle = document.createElement('button');
          btnToggle.type = 'button';
          btnToggle.className = 'btn-demo-secondary';
          btnToggle.id = `repoToggleBtn_${sanitizeId(fn)}`;
          btnToggle.textContent = st.treeWrapVisible ? '파일 트리 접기 ▾' : '파일 트리 펼치기 ▸';
          btnToggle.addEventListener('click', () => { toggleCardTreePanel(fn, btnToggle); });

          const btnSave = document.createElement('button');
          btnSave.type = 'button';
          btnSave.className = 'btn-demo-primary';
          btnSave.textContent = '파일 선택 저장';
          btnSave.style.fontSize = '13px';
          btnSave.addEventListener('click', () => { saveRepoCardAssets(fn); });

          const btnSync = document.createElement('button');
          btnSync.type = 'button';
          btnSync.className = 'btn-demo-ghost';
          btnSync.textContent = '히스토리 → SQLite';
          btnSync.style.fontSize = '12px';
          btnSync.addEventListener('click', () => { syncRepoCardHistory(fn); });

          const btnEmbedOne = document.createElement('button');
          btnEmbedOne.type = 'button';
          btnEmbedOne.className = 'btn-demo-primary';
          btnEmbedOne.textContent = '임베딩';
          btnEmbedOne.style.fontSize = '13px';
          btnEmbedOne.addEventListener('click', () => { embedRepoCardOnly(fn); });

          actions.appendChild(btnLoad);
          actions.appendChild(btnToggle);
          actions.appendChild(btnSave);
          actions.appendChild(btnSync);
          actions.appendChild(btnEmbedOne);

          const wrap = document.createElement('div');
          wrap.className = 'repo-tree-wrap';
          wrap.id = `repoTreeWrap_${sanitizeId(fn)}`;
          wrap.style.display = st.treeWrapVisible ? 'block' : 'none';

          const treeHost = document.createElement('div');
          treeHost.id = `repoTree_${sanitizeId(fn)}`;
          wrap.appendChild(treeHost);

          panelFiles.appendChild(actions);
          panelFiles.appendChild(wrap);

          const panelView = document.createElement('div');
          panelView.className = 'repo-tab-panel' + (at === 'view' ? ' repo-tab-visible' : '');
          panelView.id = `repoTabPanel_${sanitizeId(fn)}_view`;
          const viewHint = document.createElement('div');
          viewHint.style.fontSize = '12px';
          viewHint.style.color = '#64748b';
          viewHint.style.marginBottom = '6px';
          viewHint.textContent = '파일 선택 탭에서 체크한 코드 파일';
          const sel = document.createElement('select');
          sel.id = `repoViewSelect_${sanitizeId(fn)}`;
          sel.style.width = '100%';
          sel.style.marginBottom = '6px';
          sel.style.padding = '6px';
          sel.addEventListener('change', () => { loadRepoCardFileContent(fn); });
          const viewPre = document.createElement('pre');
          viewPre.className = 'repo-view-pre';
          viewPre.id = `repoViewPre_${sanitizeId(fn)}`;
          panelView.appendChild(viewHint);
          panelView.appendChild(sel);
          panelView.appendChild(viewPre);

          const panelCommits = document.createElement('div');
          panelCommits.className = 'repo-tab-panel' + (at === 'commits' ? ' repo-tab-visible' : '');
          panelCommits.id = `repoTabPanel_${sanitizeId(fn)}_commits`;
          const cLab = document.createElement('label');
          cLab.style.display = 'block';
          cLab.style.fontSize = '12px';
          cLab.style.color = '#64748b';
          cLab.textContent = 'author (비우면 로그인 GitHub 유저)';
          const cAuth = document.createElement('input');
          cAuth.type = 'text';
          cAuth.id = `repoCommitsAuthor_${sanitizeId(fn)}`;
          cAuth.style.width = '100%';
          cAuth.style.marginBottom = '8px';
          cAuth.style.padding = '6px';
          const cPerpLab = document.createElement('label');
          cPerpLab.style.display = 'block';
          cPerpLab.style.fontSize = '12px';
          cPerpLab.style.color = '#64748b';
          cPerpLab.textContent = 'per_page (기본 10)';
          const cPerp = document.createElement('input');
          cPerp.type = 'number';
          cPerp.min = '1';
          cPerp.max = '100';
          cPerp.id = `repoCommitsPerPage_${sanitizeId(fn)}`;
          cPerp.value = '10';
          cPerp.style.width = '100%';
          cPerp.style.maxWidth = '120px';
          cPerp.style.marginBottom = '8px';
          cPerp.style.padding = '6px';
          const btnComm = document.createElement('button');
          btnComm.type = 'button';
          btnComm.className = 'btn-demo-secondary';
          btnComm.textContent = '커밋 조회';
          btnComm.addEventListener('click', () => loadRepoCardCommits(fn));
          const cPre = document.createElement('pre');
          cPre.className = 'repo-commits-pre';
          cPre.id = `repoCommitsPre_${sanitizeId(fn)}`;
          panelCommits.appendChild(cLab);
          panelCommits.appendChild(cAuth);
          panelCommits.appendChild(cPerpLab);
          panelCommits.appendChild(cPerp);
          panelCommits.appendChild(btnComm);
          panelCommits.appendChild(cPre);

          const statusEl = document.createElement('div');
          statusEl.className = 'repo-card-status';
          statusEl.id = `repoCardStatus_${sanitizeId(fn)}`;
          if (st.batchStatus) statusEl.textContent = st.batchStatus;

          const saveOkEl = document.createElement('div');
          saveOkEl.className = 'repo-save-ok';
          saveOkEl.id = `repoCardSaveOk_${sanitizeId(fn)}`;
          if (st.saveOk) saveOkEl.textContent = '저장됨 ✓';

          card.appendChild(titleRow);
          card.appendChild(refRow);
          card.appendChild(tabRow);
          card.appendChild(errDiv);
          card.appendChild(panelFiles);
          card.appendChild(panelView);
          card.appendChild(panelCommits);
          card.appendChild(statusEl);
          card.appendChild(saveOkEl);

          grid.appendChild(card);
          renderFilesTreeForRepo(fn);
          refreshRepoViewSelect(fn);
        });
      }

      async function embedAllReposSequential() {
        const refRaw = (document.getElementById('embedRef')?.value || '').trim();
        const includeSummaries = document.getElementById('embedIncludeSummaries')?.checked;

        if (!savedRepoItems.length) {
          setStatus('저장된 레포가 없습니다.');
          return;
        }

        setStatus('전체 임베딩 시작…');
        focusEmbeddingPanel('전체 임베딩 진행 중…');

        for (let i = 0; i < savedRepoItems.length; i += 1) {
          const it = savedRepoItems[i];
          const fn = it && it.full_name;
          if (!fn) continue;
          const st = getCardState(fn);
          if (!st) continue;

          setCardStatusLine(fn, '처리 중...');

          const assets = Array.from(st.selectedAssetKeys).map((key) => {
            const idx = key.indexOf(':');
            return { asset_type: key.slice(0, idx), repo_path: key.slice(idx + 1) };
          });

          try {
            if (assets.length) {
              const resPut = await fetch('/api/user/selected-repo-assets', {
                method: 'PUT',
                credentials: 'include',
                headers: { 'content-type': 'application/json' },
                body: JSON.stringify({ selected_repo_id: st.selected_repo_id, assets }),
              });
              const dataPut = await resPut.json().catch(() => ({}));
              if (!resPut.ok) {
                setCardStatusLine(fn, '실패 ❌ (assets 저장)');
                setPre('embeddingResult', { step: 'PUT selected-repo-assets', repo: fn, http_status: resPut.status, response: dataPut });
                continue;
              }
            }

            const resSync = await fetch('/api/user/asset-hierarchy/sync-from-assets', {
              method: 'POST',
              credentials: 'include',
              headers: { 'content-type': 'application/json' },
              body: JSON.stringify({ selected_repo_id: st.selected_repo_id }),
            });
            const dataSync = await resSync.json().catch(() => ({}));
            if (!resSync.ok) {
              setCardStatusLine(fn, '실패 ❌ (asset_hierarchy)');
              setPre('embeddingResult', { step: 'sync-from-assets', repo: fn, http_status: resSync.status, response: dataSync });
              continue;
            }

            const url = `/api/github/repos/${String(fn).replace(/ /g, '%20')}/embedding`;
            const bodyPayload = { code_document_ids: [] };
            if (refRaw) bodyPayload.ref = refRaw;
            if (includeSummaries) bodyPayload.include_summaries = true;

            const resEmb = await fetch(url, {
              method: 'POST',
              credentials: 'include',
              headers: { 'content-type': 'application/json' },
              body: JSON.stringify(bodyPayload),
            });
            const dataEmb = await resEmb.json().catch(() => ({}));
            setPre('embeddingResult', { http_status: resEmb.status, repo: fn, response: dataEmb });

            if (resEmb.ok) {
              const emb = (dataEmb && dataEmb.embedded !== undefined) ? Number(dataEmb.embedded) : 0;
              embeddingStatusCache.set(fn, emb > 0);
              setCardStatusLine(fn, emb > 0 ? '완료 ✅' : '완료 (embedded=0)');
            } else {
              setCardStatusLine(fn, '실패 ❌ (임베딩)');
            }
          } catch (e) {
            setCardRepoError(fn, `접근 실패: ${String(e)}`);
            setCardStatusLine(fn, '실패 ❌');
            setPre('embeddingResult', { error: String(e), repo: fn });
          }
        }

        renderAllRepoCards();
        setStatus('전체 임베딩 루프 종료');
      }

      function focusEmbeddingPanel(message) {
        const panel = document.getElementById('embeddingDemo');
        const pre = document.getElementById('embeddingResult');
        if (pre && message) pre.textContent = message;
        if (panel) panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }

      async function loadJson(url) {
        const res = await fetch(url, { credentials: 'include' });
        const data = await res.json().catch(() => ({}));
        return { res, data };
      }

      async function loadRecentJobs(selectJobId) {
        const sel = document.getElementById('draftJobSelect');
        if (!sel) return;
        try {
          const res = await fetch('/api/jobs/recent?limit=40', { credentials: 'include' });
          const data = await res.json().catch(() => ({}));
          if (!res.ok) {
            return;
          }
          const prev = selectJobId || sel.value || '';
          sel.innerHTML = '';
          const opt0 = document.createElement('option');
          opt0.value = '';
          opt0.textContent = '공고 맥락 없이';
          sel.appendChild(opt0);
          const list = data.jobs || [];
          list.forEach((j) => {
            if (!j || !j.id) return;
            const opt = document.createElement('option');
            opt.value = j.id;
            const cn = (j.company_name && String(j.company_name).trim()) ? String(j.company_name).trim() : '(기업명 없음)';
            const pos = (j.position && String(j.position).trim()) ? String(j.position).trim() : '';
            opt.textContent = pos ? `${cn} · ${pos}` : cn;
            sel.appendChild(opt);
          });
          if (prev && Array.from(sel.options).some((o) => o.value === prev)) {
            sel.value = prev;
          }
        } catch (e) {
          /* ignore */
        }
      }

      async function loadMe() {
        setStatus('loading /api/me...');
        try {
          const res = await fetch('/api/me', { credentials: 'include' });
          const data = await res.json().catch(() => ({}));
          if (!res.ok) {
            setStatus('not authorized');
            setMe(data);
            return;
          }
          setStatus('authorized');
          setMe(data);

          // 인증 이후: 내 선택 레포/전체 레포/활성 레포를 자동으로 로딩
          await loadSelectedReposUI();
          // Chroma 실제 임베딩 상태를 UI 뱃지로 동기화
          try {
            const res = await fetch('/api/user/embedding-status', { credentials: 'include' });
            const data = await res.json().catch(() => ({}));
            if (res.ok && data && data.status) {
              embeddingStatusCache.clear();
              Object.entries(data.status).forEach(([fn, ok]) => {
                embeddingStatusCache.set(fn, !!ok);
              });
              renderAllRepoCards();
            }
          } catch (e) {
            /* ignore */
          }
          await loadRecentJobs();
          // repo 전체 목록은 GitHub API를 추가로 호출하므로, 초기엔 로드하지 않는다.
        } catch (e) {
          setStatus('failed to load /api/me');
          setMe({ error: String(e) });
        }
      }

      safeOnClick('loginBtn', () => { window.location.href = '/api/auth/github/login'; });
      safeOnClick('logoutBtn', () => { window.location.href = '/api/auth/logout'; });

      safeOnClick('btnRepos', async () => {
        await loadReposUI();
        setStatus('GET /api/github/repos 완료');
      });

      safeOnClick('btnSelectedRepos', async () => {
        await loadSelectedReposUI();
        await loadReposUI();
        setStatus('GET /api/user/selected-repos 완료');
      });

      safeOnClick('btnLoadSelectedRepos', async () => {
        await loadSelectedReposUI();
        await loadReposUI();
      });

      safeOnClick('btnSaveSelectedRepos', async () => {
        const fullNames = Array.from(selectedRepoFullNames);
        if (!fullNames.length) {
          setStatus('저장할 선택 레포가 없습니다.');
          return;
        }

        setStatus('선택 레포 저장 중...');
        try {
          const res = await fetch('/api/user/selected-repos', {
            method: 'PUT',
            headers: { 'content-type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ full_names: fullNames, replace: true })
          });
          const data = await res.json().catch(() => ({}));
          if (!res.ok) {
            setStatus('선택 레포 저장 실패');
            setPre('selectedRepos', data);
            return;
          }

          // 서버 반환값 기준으로 선택 레포 상태/active를 다시 동기화
          await loadSelectedReposUI();
          // repo 체크박스 UI도 즉시 반영
          await loadReposUI();
          setStatus('선택 레포 저장 완료');
        } catch (e) {
          setStatus('선택 레포 저장 예외');
          setPre('selectedRepos', { error: String(e) });
        }
      });

      safeOnClick('btnEmbedAllRepos', async () => {
        await embedAllReposSequential();
      });

      document.querySelectorAll('input[name="jobSource"]').forEach((el) => {
        el.addEventListener('change', () => {
          const manual = document.querySelector('input[name="jobSource"]:checked').value === 'manual';
          const mf = document.getElementById('jobManualFields');
          const uf = document.getElementById('jobUrlField');
          if (mf) mf.style.display = manual ? 'block' : 'none';
          if (uf) uf.style.display = manual ? 'none' : 'block';
        });
      });

      safeOnClick('btnJobParse', async () => {
        const manual = document.querySelector('input[name="jobSource"]:checked').value === 'manual';
        let payload;
        if (manual) {
          const company = (document.getElementById('jobCompanyName')?.value || '').trim();
          const pos = (document.getElementById('jobPositionTitle')?.value || '').trim();
          if (!company || !pos) {
            setPre('jobParseResult', { error: 'company_name과 position_title은 필수입니다.' });
            setStatus('공고 parse: 필수 필드 누락');
            return;
          }
          const splitLines = (id) =>
            (document.getElementById(id)?.value || '')
              .split('\\n')
              .map((s) => s.trim())
              .filter(Boolean);
          payload = {
            source_type: 'manual',
            company_name: company,
            position_title: pos,
            company_persona: (document.getElementById('jobCompanyPersona')?.value || '').trim(),
            duties: splitLines('jobDuties'),
            requirements: splitLines('jobRequirements'),
            preferences: splitLines('jobPreferences'),
          };
        } else {
          const u = (document.getElementById('jobUrl')?.value || '').trim();
          if (!u) {
            setPre('jobParseResult', { error: 'url을 입력하세요.' });
            setStatus('공고 parse: url 없음');
            return;
          }
          payload = { source_type: 'url', url: u };
        }
        setStatus('공고 parse 요청 중…');
        const jp = document.getElementById('jobParseDemo');
        if (jp) jp.scrollIntoView({ behavior: 'smooth', block: 'start' });
        try {
          const res = await fetch('/api/jobs/parse', {
            method: 'POST',
            credentials: 'include',
            headers: { 'content-type': 'application/json' },
            body: JSON.stringify(payload),
          });
          const data = await res.json().catch(() => ({}));
          setPre('jobParseResult', { http_status: res.status, response: data });
          if (res.ok && data.job_id) {
            loadRecentJobs(data.job_id);
            setStatus(`공고 저장 완료 · job_id=${data.job_id}`);
          } else {
            const msg = (data && data.message) ? data.message : (data && data.error) ? data.error : String(res.status);
            setStatus(`공고 parse 실패: ${msg}`);
          }
        } catch (e) {
          setStatus('공고 parse 예외');
          setPre('jobParseResult', { error: String(e) });
        }
      });

      const WRITER_Q_MIN = 1;
      const WRITER_Q_MAX = 5;

      function collectWriterQuestions() {
        const list = document.getElementById('writerQuestionList');
        if (!list) return [];
        const out = [];
        list.querySelectorAll('.wd-q-row').forEach((row) => {
          const ta = row.querySelector('.wd-q-text');
          const nm = row.querySelector('.wd-q-max');
          const t = ta && ta.value ? String(ta.value).trim() : '';
          const maxChars = Math.max(1, parseInt(nm && nm.value ? nm.value : '500', 10) || 500);
          out.push({ question_text: t, max_chars: maxChars });
        });
        return out;
      }

      function refreshWriterRemoveButtons() {
        const list = document.getElementById('writerQuestionList');
        if (!list) return;
        const n = list.children.length;
        list.querySelectorAll('.wd-q-remove').forEach((btn) => {
          btn.disabled = n <= WRITER_Q_MIN;
        });
        const addBtn = document.getElementById('btnWriterAddQ');
        if (addBtn) addBtn.disabled = n >= WRITER_Q_MAX;
      }

      function addWriterQuestionRow() {
        const list = document.getElementById('writerQuestionList');
        if (!list || list.children.length >= WRITER_Q_MAX) return;
        const wrap = document.createElement('div');
        wrap.className = 'wd-q-row';
        const top = document.createElement('div');
        top.style.cssText = 'display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;gap:8px;';
        const lab = document.createElement('span');
        lab.style.fontWeight = '600';
        lab.style.color = '#0f172a';
        lab.textContent = '문항';
        const rm = document.createElement('button');
        rm.type = 'button';
        rm.className = 'wd-q-remove btn-demo-ghost';
        rm.textContent = '삭제';
        rm.addEventListener('click', () => {
          if (list.children.length <= WRITER_Q_MIN) return;
          wrap.remove();
          refreshWriterRemoveButtons();
        });
        top.appendChild(lab);
        top.appendChild(rm);
        const ta = document.createElement('textarea');
        ta.className = 'wd-q-text';
        ta.rows = 3;
        ta.placeholder = '지원 동기를 작성해주세요.';
        ta.style.cssText = 'width:100%;min-width:0;padding:8px;border-radius:6px;border:1px solid #cbd5e1;box-sizing:border-box;';
        const row2 = document.createElement('div');
        row2.style.marginTop = '8px';
        const lab2 = document.createElement('label');
        lab2.style.cssText = 'font-size:0.9rem;color:#334155;margin-right:8px;';
        lab2.textContent = 'max_chars ';
        const num = document.createElement('input');
        num.type = 'number';
        num.className = 'wd-q-max';
        num.value = '500';
        num.min = '1';
        num.style.cssText = 'width:100px;padding:6px;border-radius:6px;border:1px solid #cbd5e1;';
        row2.appendChild(lab2);
        row2.appendChild(num);
        wrap.appendChild(top);
        wrap.appendChild(ta);
        wrap.appendChild(row2);
        list.appendChild(wrap);
        refreshWriterRemoveButtons();
      }

      function initWriterQuestionList() {
        const list = document.getElementById('writerQuestionList');
        if (!list || list.children.length) return;
        addWriterQuestionRow();
      }

      function hideWriterError() {
        const el = document.getElementById('writerDraftErrorArea');
        if (el) el.style.display = 'none';
        const line = document.getElementById('writerErrorLine');
        const pre = document.getElementById('writerErrorJson');
        if (line) line.textContent = '';
        if (pre) {
          pre.textContent = '';
          pre.style.display = 'none';
        }
      }

      function resetWriterUsedAssetsDisplay() {
        const wrap = document.getElementById('writerRepoTags');
        const badge = document.getElementById('writerEssaysBadge');
        const listEl = document.getElementById('writerEssaysList');
        if (wrap) {
          wrap.innerHTML = '';
          wrap.style.color = '#64748b';
          wrap.textContent = '참조 레포 없음';
        }
        if (badge) {
          badge.className = 'wd-essay-no';
          badge.textContent = '합격 자소서 미참조';
        }
        if (listEl) {
          listEl.innerHTML = '';
          listEl.style.display = 'none';
        }
      }

      function showWriterClientMessage(text) {
        const errArea = document.getElementById('writerDraftErrorArea');
        const line = document.getElementById('writerErrorLine');
        const pre = document.getElementById('writerErrorJson');
        const cards = document.getElementById('writerDraftCards');
        if (!errArea || !line || !pre) return;
        if (cards) cards.innerHTML = '';
        resetWriterUsedAssetsDisplay();
        errArea.style.display = 'block';
        line.textContent = text;
        pre.style.display = 'none';
        pre.textContent = '';
      }

      function showWriterHttpError(status, data) {
        const errArea = document.getElementById('writerDraftErrorArea');
        const line = document.getElementById('writerErrorLine');
        const pre = document.getElementById('writerErrorJson');
        const cards = document.getElementById('writerDraftCards');
        if (!errArea || !line || !pre) return;
        if (cards) cards.innerHTML = '';
        resetWriterUsedAssetsDisplay();
        errArea.style.display = 'block';
        if (status === 401) {
          line.textContent = '로그인이 필요합니다';
          pre.style.display = 'none';
          pre.textContent = '';
        } else if (status === 400) {
          line.textContent = '문항을 확인해주세요';
          pre.style.display = 'none';
          pre.textContent = '';
        } else {
          line.textContent = '';
          pre.style.display = 'block';
          pre.textContent = JSON.stringify(data, null, 2);
        }
      }

      function setWriterUsedAssets(ua) {
        ua = ua || {};
        const repos = Array.isArray(ua.github_repos) ? ua.github_repos : [];
        const essays = Array.isArray(ua.accepted_essays) ? ua.accepted_essays : [];
        const wrap = document.getElementById('writerRepoTags');
        const badge = document.getElementById('writerEssaysBadge');
        const listEl = document.getElementById('writerEssaysList');
        if (!wrap || !badge) return;
        wrap.innerHTML = '';
        wrap.style.color = '';
        if (!repos.length) {
          wrap.style.color = '#64748b';
          wrap.textContent = '참조 레포 없음';
        } else {
          repos.forEach((r) => {
            const fn = (r && r.full_name) ? r.full_name : '';
            if (!fn) return;
            const s = document.createElement('span');
            s.className = 'wd-repo-tag';
            s.textContent = fn;
            wrap.appendChild(s);
          });
        }
        const hasEssayList = essays.length > 0;
        badge.className = ua.accepted_essays_used || hasEssayList ? 'wd-essay-yes' : 'wd-essay-no';
        badge.textContent = ua.accepted_essays_used || hasEssayList ? '합격 자소서 참조 ✓' : '합격 자소서 미참조';
        if (listEl) {
          listEl.innerHTML = '';
          if (hasEssayList) {
            listEl.style.display = 'block';
            essays.forEach((e) => {
              if (!e || typeof e !== 'object') return;
              const co = (e.company != null && String(e.company).trim()) ? String(e.company).trim() : '';
              const po = (e.position != null && String(e.position).trim()) ? String(e.position).trim() : '';
              const q = (e.question != null && String(e.question).trim()) ? String(e.question).trim() : '';
              const head = [co, po].filter(Boolean).join(' · ');
              const line = document.createElement('div');
              line.className = 'wd-essay-line';
              const qShort = q.length > 80 ? q.slice(0, 80) + '…' : q;
              line.textContent = (head ? ('- ' + head + ': "' + qShort + '"') : ('- "' + qShort + '"'));
              listEl.appendChild(line);
            });
          } else {
            listEl.style.display = 'none';
          }
        }
      }

      function renderWriterDraftsSuccess(data) {
        hideWriterError();
        const container = document.getElementById('writerDraftCards');
        if (!container) return;
        container.innerHTML = '';
        const drafts = (data && data.drafts) ? data.drafts : [];
        drafts.forEach((d) => {
          const card = document.createElement('div');
          card.className = 'wd-card';
          const sub = document.createElement('div');
          sub.className = 'wd-card-sub';
          sub.textContent = (d && d.question_text) ? d.question_text : '(문항 없음)';
          const body = document.createElement('div');
          body.className = 'wd-card-body';
          const ans = (d && d.answer !== undefined && d.answer !== null) ? String(d.answer) : '';
          if (!ans.trim()) {
            body.classList.add('wd-fail');
            body.textContent = '생성 실패 (에셋 없음 또는 API 키 미설정)';
          } else {
            body.textContent = ans;
          }
          const cb = document.createElement('span');
          cb.className = 'wd-char-badge';
          const cc = (d && d.char_count !== undefined && d.char_count !== null) ? d.char_count : ans.length;
          cb.textContent = '글자 수 ' + String(cc);
          card.appendChild(sub);
          card.appendChild(body);
          card.appendChild(cb);
          container.appendChild(card);
        });
        setWriterUsedAssets(data.used_assets || {});
      }

      safeOnClick('btnWriterAddQ', () => {
        const list = document.getElementById('writerQuestionList');
        if (!list || list.children.length >= WRITER_Q_MAX) return;
        addWriterQuestionRow();
      });

      safeOnClick('btnWriterDraft', async () => {
        const selJob = document.getElementById('draftJobSelect');
        const jobId = (selJob && selJob.value) ? String(selJob.value).trim() : '';
        const qs = collectWriterQuestions();
        if (qs.length < WRITER_Q_MIN || qs.length > WRITER_Q_MAX) {
          showWriterClientMessage('문항을 확인해주세요');
          setStatus('draft: 문항 개수 오류');
          return;
        }
        if (qs.some((q) => !q.question_text.trim())) {
          showWriterClientMessage('문항을 확인해주세요');
          setStatus('draft: 문항 텍스트 누락');
          return;
        }
        const payload = { questions: qs };
        if (jobId) payload.job_id = jobId;
        const btn = document.getElementById('btnWriterDraft');
        const prevLabel = btn ? btn.textContent : '';
        if (btn) {
          btn.disabled = true;
          btn.textContent = '생성 중...';
        }
        setStatus('자소서 초안 요청 중…');
        const panel = document.getElementById('writerDraftDemo');
        if (panel) panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
        try {
          const res = await fetch('/api/cover-letter/draft', {
            method: 'POST',
            credentials: 'include',
            headers: { 'content-type': 'application/json' },
            body: JSON.stringify(payload),
          });
          const data = await res.json().catch(() => ({}));
          if (!res.ok) {
            if (res.status === 401) {
              showWriterHttpError(401, data);
            } else if (res.status === 400) {
              showWriterHttpError(400, data);
            } else {
              showWriterHttpError(res.status, data);
            }
            const msg = (data && data.message) ? data.message : (data && data.error) ? data.error : String(res.status);
            setStatus(`자소서 draft 실패: ${msg}`);
            return;
          }
          renderWriterDraftsSuccess(data);
          const n = (data.drafts) ? data.drafts.length : 0;
          setStatus(`자소서 초안 완료 · drafts=${n}`);
        } catch (e) {
          setStatus('자소서 draft 예외');
          const errArea = document.getElementById('writerDraftErrorArea');
          const line = document.getElementById('writerErrorLine');
          const pre = document.getElementById('writerErrorJson');
          const cards = document.getElementById('writerDraftCards');
          if (cards) cards.innerHTML = '';
          resetWriterUsedAssetsDisplay();
          if (errArea && line && pre) {
            errArea.style.display = 'block';
            line.textContent = '';
            pre.style.display = 'block';
            pre.textContent = JSON.stringify({ error: String(e) }, null, 2);
          }
        } finally {
          if (btn) {
            btn.disabled = false;
            btn.textContent = prevLabel || '초안 생성';
          }
        }
      });

      window.addEventListener('load', () => {
        // 로딩 상태가 오래가면 사용자가 “왜 안 뜨지?”를 바로 알 수 있도록 시작 메시지를 준다.
        setStatus('loading /api/me...');
        loadMe();
        initWriterQuestionList();
      });
    </script>
  </body>
</html>
""".strip()
