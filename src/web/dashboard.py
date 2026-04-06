from __future__ import annotations

from src.web.ui_theme import CSS_GITHUB_DARK, header_html

# 워크스페이스 HTML: GitHub 연결 · 레포 선택 · 코드 임베딩(RAG).
# 자소서 작성/수정은 `cover_letter_page` 참고.

dashboard_html = (
    r"""<!doctype html>
<html lang="ko">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Autofolio — 워크스페이스</title>
    <style>
"""
    + CSS_GITHUB_DARK
    + r"""
    </style>
  </head>
  <body>
"""
    + header_html("hub")
    + r"""
    <main class="af-main">
      <div class="af-hero">
        <h1>워크스페이스</h1>
        <p>GitHub 레포와 코드를 연결하고 임베딩해 증거 기반 자소서·포트폴리오에 쓸 RAG를 만듭니다. 자소서 초안·첨삭은 <a class="af-link" href="/cover-letter">자소서</a> 페이지에서 이어갑니다.</p>
      </div>

      <section class="af-card" aria-labelledby="session-title">
        <div class="af-section-label">Session</div>
        <h2 id="session-title">계정</h2>
        <p class="af-hint">상단 <strong>GitHub 로그인</strong> 후 세션 상태가 아래에 표시됩니다.</p>
        <h3 class="af-subtitle">GET /api/me</h3>
        <pre id="me" class="af-pre"></pre>
      </section>

      <section class="af-card" aria-labelledby="github-api-title">
        <div class="af-section-label">Repository</div>
        <h2 id="github-api-title">GitHub API · 선택 레포</h2>
        <p class="af-hint">공개 레포 목록을 불러오고, 지원에 쓸 레포를 선택해 저장합니다.</p>
        <div class="af-row-actions" style="margin:14px 0;">
          <button type="button" class="af-btn af-btn-ghost" id="btnRepos">GET /api/github/repos</button>
          <button type="button" class="af-btn af-btn-ghost" id="btnSelectedRepos">GET /api/user/selected-repos</button>
        </div>
        <pre id="repos" class="af-pre"></pre>
        <pre id="selectedRepos" class="af-pre af-mt-sm"></pre>

        <h3 class="af-subtitle">내 레포 선택</h3>
        <div id="repoList" class="af-field"></div>
        <div class="af-row-actions">
          <button type="button" class="af-btn af-btn-primary" id="btnSaveSelectedRepos">선택 레포 저장</button>
          <button type="button" class="af-btn af-btn-ghost" id="btnLoadSelectedRepos">저장된 레포 불러오기</button>
        </div>
      </section>

      <section class="af-card" id="embeddingDemo" aria-labelledby="embed-demo-title">
        <div class="af-section-label">Evidence · RAG</div>
        <h2 id="embed-demo-title" class="af-title-row"><span class="af-tag">embed</span> 코드 임베딩</h2>
        <p class="af-hint">
          선택한 레포의 코드를 <strong>Chroma</strong>에 임베딩합니다. Writer·Inspector가 레포 근거를 인용할 수 있습니다.
          컬렉션 <code>user_assets_{user_id}</code> · <code>.env</code>의 <code>OPENAI_API_KEY</code>.
        </p>
        <ol class="demo-steps">
          <li><strong>GitHub 로그인</strong> → 레포 체크 → <strong>선택 레포 저장</strong></li>
          <li>카드 <strong>파일 선택</strong>: 트리 로드 → 체크 → 저장 · <strong>파일 보기</strong>·<strong>커밋</strong></li>
          <li><strong>전체 임베딩</strong>: PUT assets → sync-from-assets → POST embedding</li>
        </ol>
        <div style="margin-bottom: 12px;">
          <label class="af-label" for="embedRef">ref (브랜치·SHA, 선택)</label>
          <input id="embedRef" class="af-input" style="max-width:280px;" placeholder="예: main" />
          <div style="margin-top: 10px;">
            <label style="cursor: pointer; color: var(--fg-muted); font-size: 0.88rem;">
              <input type="checkbox" id="embedIncludeSummaries" checked />
              응답에 LLM 요약 포함 (<code>include_summaries</code>)
            </label>
          </div>
        </div>
        <div style="margin-bottom: 14px;">
          <button type="button" class="af-btn af-btn-primary" id="btnEmbedAllRepos">전체 임베딩 (저장된 레포 순서)</button>
          <span class="af-hint" style="margin-left: 10px;">카드별 진행 상태가 표시됩니다.</span>
        </div>
        <p class="af-hint">
          <code>PUT /api/user/selected-repo-assets</code> ·
          <code>POST /api/user/asset-hierarchy/sync-from-assets</code> ·
          <code>POST /api/github/repos/&lt;owner%2Frepo&gt;/embedding</code>
        </p>
        <div id="repoCardsGrid" aria-label="저장된 레포 카드"></div>
        <h2 class="af-subtitle">마지막 임베딩 응답</h2>
        <pre id="embeddingResult" class="af-pre"></pre>
      </section>
    </main>

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

      window.addEventListener('load', () => {
        setStatus('loading /api/me...');
        loadMe();
      });
    </script>
  </body>
</html>
""".strip()
)
