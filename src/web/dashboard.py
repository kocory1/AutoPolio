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
      body { font-family: system-ui, -apple-system, Segoe UI, sans-serif; padding: 16px; max-width: 960px; margin: 0 auto; color: #1e293b; }
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
    </style>
  </head>
  <body>
    <h2>Autofolio Dev Dashboard</h2>
    <p class="hint">OAuth · GitHub API · 선택 레포/assets · <strong>코드 임베딩(Chroma)</strong> 개발용 화면입니다.</p>
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
      <label>repo_id (owner/repo 형식):</label>
      <input id="repoId" style="width: 260px;" value="owner/repo-a" />
    </div>

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

    <div style="margin-top: 12px; margin-bottom: 18px;">
      <h3>저장된 레포(assets 대상) 선택</h3>
      <div id="savedRepoList" style="margin-bottom: 10px;"></div>
      <div style="margin-bottom: 8px;">
        <label>active selected_repo_id:</label>
        <input id="activeSelectedRepoId" style="width: 220px;" value="" />
      </div>
      <button id="btnReloadAssets">assets 복원</button>
    </div>

    <div style="margin-top: 12px; margin-bottom: 18px;">
      <h3>assets 선택 (폴더/파일 체크)</h3>
      <button id="btnSaveRepoAssets">선택 assets 저장</button>
      <pre id="assetSelection" style="display:none;"></pre>
    </div>

    <h3>Files Tree</h3>
    <div style="margin-bottom: 12px;">
      <label>path:</label>
      <input id="filesPath" style="width: 140px;" value="/" />
      <button id="btnFilesTree">GET /api/github/repos/{repo_id}/files</button>
    </div>
    <pre id="filesTree" style="display:none;"></pre>

    <div style="margin-top: 10px; margin-bottom: 18px;">
      <h4>Files Tree (폴더 펼치기)</h4>
      <div id="treeList" style="max-height: 320px; overflow: auto; border: 1px solid #ddd; padding: 8px; margin-bottom: 10px;"></div>
    </div>

    <h3>Contents</h3>
    <div style="margin-bottom: 12px;">
      <label>encoding:</label>
      <select id="contentsEncoding">
        <option value="raw" selected>raw</option>
        <option value="base64">base64</option>
      </select>
    </div>
    <div style="margin-bottom: 12px;">
      <h4 style="margin: 0 0 8px 0;">저장된 파일(선택)</h4>
      <div id="contentsFileList" style="max-height: 220px; overflow: auto; border: 1px solid #ddd; padding: 8px;"></div>
    </div>
    <pre id="contents"></pre>

    <h3>Commits</h3>
    <div style="margin-bottom: 12px;">
      <label>author (optional):</label>
      <input id="commitsAuthor" style="width: 180px;" value="" placeholder="(empty=own user)" />
      <label>page:</label>
      <input id="commitsPage" style="width: 60px;" value="1" />
      <label>per_page:</label>
      <input id="commitsPerPage" style="width: 80px;" value="30" />
      <button id="btnCommits">GET /api/github/repos/{repo_id}/commits</button>
    </div>
    <pre id="commits"></pre>

    <section class="demo-panel" id="embeddingDemo" aria-labelledby="embed-demo-title">
      <h2 id="embed-demo-title"><span class="tag">NEW</span> GitHub 코드 임베딩 데모</h2>
      <p class="hint">
        서버가 <code>asset_hierarchy</code>·GitHub Contents·(옵션) OpenAI로 요약·벡터를 만들고
        Chroma <code>user_assets_{user_id}</code>에 넣는 흐름을 한 화면에서 시험합니다.
      </p>
      <ol class="demo-steps">
        <li><strong>GitHub 로그인</strong></li>
        <li>위에서 레포 체크 → <strong>선택 레포 저장</strong></li>
        <li><strong>저장된 레포(assets 대상)</strong> 클릭 → <strong>Files Tree</strong> 로드 → 파일/폴더 체크 → <strong>선택 assets 저장</strong></li>
        <li><strong>히스토리 → SQLite</strong>: 아래 첫 버튼으로 <code>selected_repo_assets</code>의 <code>code</code>만 <code>asset_hierarchy</code>에 반영</li>
        <li><strong>임베딩</strong>: 명시 id(현재 체크 기준) 또는 DB만 사용 · <code>.env</code>에 <code>OPENAI_API_KEY</code> 있으면 실제 LLM·임베딩</li>
      </ol>
      <div style="margin-bottom: 12px;">
        <label for="embedRef"><strong>ref</strong> (브랜치·SHA, 선택):</label>
        <input id="embedRef" style="width: 240px; padding: 8px; border-radius: 6px; border: 1px solid #cbd5e1;" placeholder="예: main" />
        <div style="margin-top: 10px;">
          <label style="cursor: pointer;">
            <input type="checkbox" id="embedIncludeSummaries" checked />
            응답에 <strong>LLM 요약문</strong> 포함 (<code>include_summaries</code>, 응답 크기 증가)
          </label>
        </div>
      </div>
      <div style="display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-bottom: 12px;">
        <button type="button" class="btn-demo-secondary" id="btnSyncHierarchy">히스토리 → asset_hierarchy (code)</button>
        <button type="button" class="btn-demo-primary" id="btnEmbedExplicit">임베딩 · 선택 코드 id 명시</button>
        <button type="button" class="btn-demo-primary" id="btnEmbedFromDb">임베딩 · DB(asset_hierarchy)만</button>
      </div>
      <p class="hint">
        API: <code>POST /api/user/asset-hierarchy/sync-from-assets</code> ·
        <code>POST /api/github/repos/&lt;owner%2Frepo&gt;/embedding</code>
        · 명시 모드는 체크된 파일로 <code>owner/repo/경로</code> id를 조합합니다.
      </p>
      <h4 style="margin: 14px 0 6px 0; color: #334155;">응답</h4>
      <pre id="embeddingResult"></pre>
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
      // 선택된 assets 키: `${assetType}:${repoPath}` 형태
      const selectedAssetKeys = new Set();
      let lastRepos = [];
      let lastFilesTreeItems = [];

      // selected_repos 로부터 얻는 mapping
      const selectedRepoIdByFullName = new Map();
      let savedRepoItems = [];
      let activeSelectedRepoId = null;
      let activeSelectedRepoFullName = '';
      let activeContentsPath = '';

      // 중첩 트리 렌더링을 위한 상태
      let fileTreeRoot = null;
      const expandedFolderPaths = new Set();

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

      const assetKeyToInputId = (key) => `asset_${sanitizeId(key)}`;

      const sanitizeId = (s) => String(s).replace(/[^a-zA-Z0-9_-]/g, '_');
      const firstOfSet = (set) => set.values().next().value;

      const setActiveRepo = (fullName) => {
        const el = document.getElementById('repoId');
        if (el) el.value = fullName || '';
      };

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

            // active repoId(트리/contents 표시용)는 savedRepoList에서만 선택하도록 둔다.
          });

          const label = document.createElement('label');
          label.htmlFor = inputId;
          label.textContent = ` ${fullName}  (${r.language || 'n/a'}, pushed: ${r.pushed_at || 'n/a'})`;

          wrapper.appendChild(cb);
          wrapper.appendChild(label);
          repoList.appendChild(wrapper);
        });

        // 최초 렌더링 시 active repo 결정
        const activeInput = document.getElementById('repoId');
        if (activeInput && (!activeInput.value || !lastRepos.some(x => x.full_name === activeInput.value))) {
          setActiveRepo(selectedRepoFullNames.size ? firstOfSet(selectedRepoFullNames) : ((lastRepos[0] && lastRepos[0].full_name) || ''));
        }
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
        items.forEach((it) => {
          if (it && it.full_name) {
            selectedRepoFullNames.add(it.full_name);
            selectedRepoIdByFullName.set(it.full_name, it.id);
          }
        });
        setPre('selectedRepos', data);

        renderSavedRepoList(items);

        // 현재 active가 사라졌거나(선택 해제) 최초 1회인 경우에만 자동 활성화
        const stillActive = items.some((it) => it && it.id === activeSelectedRepoId);
        if (!stillActive) {
          activeSelectedRepoId = null;
          activeSelectedRepoFullName = '';
        }
        if (activeSelectedRepoId === null && items.length) {
          await activateSavedRepo(items[0]);
        }

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

        // tree/contents는 repoId를 사용하므로, active selected_repo가 있으면 그걸 유지한다.
        if (activeSelectedRepoId !== null && activeSelectedRepoFullName) setActiveRepo(activeSelectedRepoFullName);
        else if (selectedRepoFullNames.size) setActiveRepo(firstOfSet(selectedRepoFullNames));
        else setActiveRepo((repos[0] && repos[0].full_name) || '');
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

      function updateAssetSelectionDebug() {
        setPre('assetSelection', Array.from(selectedAssetKeys));
        renderContentsFileList();
      }

      function renderContentsFileList() {
        const container = document.getElementById('contentsFileList');
        if (!container) return;

        const codeKeys = Array.from(selectedAssetKeys).filter((k) => k.startsWith('code:'));
        const filePaths = codeKeys
          .map((k) => k.slice('code:'.length))
          .filter((p) => p)
          .sort((a, b) => a.localeCompare(b));

        container.innerHTML = '';

        if (!filePaths.length) {
          container.textContent = '선택된 assets 코드 파일이 없습니다.';
          return;
        }

        filePaths.forEach((fp) => {
          const btn = document.createElement('button');
          btn.type = 'button';
          btn.textContent = fp;
          btn.style.display = 'block';
          btn.style.width = '100%';
          btn.style.textAlign = 'left';
          btn.style.marginBottom = '6px';
          if (activeContentsPath === fp) btn.style.fontWeight = 'bold';
          btn.addEventListener('click', async () => {
            activeContentsPath = fp;
            renderContentsFileList();
            await loadContentForPath(fp);
          });
          container.appendChild(btn);
        });
      }

      function renderFilesTree() {
        const treeList = document.getElementById('treeList');
        if (!treeList) return;
        treeList.innerHTML = '';

        if (!fileTreeRoot) {
          treeList.textContent = '먼저 Files Tree를 로드하세요.';
          return;
        }

        const renderNode = (node, level) => {
          const row = document.createElement('div');
          row.style.marginLeft = `${level * 16}px`;
          row.style.display = 'flex';
          row.style.alignItems = 'center';
          row.style.gap = '8px';

          if (node.type === 'dir') {
            const expanded = expandedFolderPaths.has(node.path);
            const arrow = document.createElement('span');
            arrow.style.cursor = 'pointer';
            arrow.textContent = expanded ? '▾' : '▸';
            arrow.addEventListener('click', () => {
              if (expanded) expandedFolderPaths.delete(node.path);
              else expandedFolderPaths.add(node.path);
              renderFilesTree();
            });

            const key = assetKey('folder', node.path);
            const inputId = assetKeyToInputId(key);
            const cb = document.createElement('input');
            cb.type = 'checkbox';
            cb.id = inputId;
            cb.checked = selectedAssetKeys.has(key);
            cb.addEventListener('change', () => {
              const allKeys = collectDescendantAssetKeys(node);
              if (cb.checked) {
                allKeys.forEach((k) => selectedAssetKeys.add(k));
              } else {
                allKeys.forEach((k) => selectedAssetKeys.delete(k));
              }
              updateAssetSelectionDebug();
              renderFilesTree();
            });

            const nameEl = document.createElement('span');
            nameEl.style.cursor = 'pointer';
            const name = node.path ? node.path.split('/').pop() : '(root)';
            nameEl.textContent = ` ${name}`;
            nameEl.addEventListener('click', () => {
              if (expanded) expandedFolderPaths.delete(node.path);
              else expandedFolderPaths.add(node.path);
              renderFilesTree();
            });

            row.appendChild(arrow);
            row.appendChild(cb);
            row.appendChild(nameEl);

            treeList.appendChild(row);

            if (expandedFolderPaths.has(node.path)) {
              (node.children || []).forEach((ch) => renderNode(ch, level + 1));
            }
          } else {
            const key = assetKey('code', node.path);
            const inputId = assetKeyToInputId(key);
            const cb = document.createElement('input');
            cb.type = 'checkbox';
            cb.id = inputId;
            cb.checked = selectedAssetKeys.has(key);
            cb.addEventListener('change', () => {
              if (cb.checked) selectedAssetKeys.add(key);
              else selectedAssetKeys.delete(key);
              updateAssetSelectionDebug();
            });

            const label = document.createElement('label');
            label.htmlFor = inputId;
            label.textContent = ` ${node.path.split('/').pop()}`;

            // 파일 클릭 시 contents 표시
            label.addEventListener('click', () => {
              loadContentForPath(node.path);
            });

            row.appendChild(cb);
            row.appendChild(label);
            treeList.appendChild(row);
          }
        };

        // root children만 렌더링(폴더는 collapsed/expanded 기준)
        (fileTreeRoot.children || []).forEach((ch) => renderNode(ch, 0));
      }

      function renderSavedRepoList(items) {
        const container = document.getElementById('savedRepoList');
        if (!container) return;
        container.innerHTML = '';

        if (!items || !items.length) {
          container.textContent = '저장된 레포가 없습니다. 먼저 레포를 선택하고 저장하세요.';
          return;
        }

        items.forEach((it) => {
          const btn = document.createElement('button');
          btn.type = 'button';
          btn.textContent = it.full_name;
          btn.style.display = 'block';
          btn.style.marginBottom = '6px';
          btn.style.textAlign = 'left';
          if (activeSelectedRepoId === it.id) {
            btn.style.fontWeight = 'bold';
          }
          btn.addEventListener('click', () => activateSavedRepo(it));
          container.appendChild(btn);
        });
      }

      async function loadRepoAssets(selectedRepoId) {
        selectedAssetKeys.clear();
        updateAssetSelectionDebug();

        if (!selectedRepoId) {
          return;
        }

        setStatus(`assets 로딩 중... (selected_repo_id=${selectedRepoId})`);
        const { res, data } = await loadJson(
          `/api/user/selected-repo-assets?selected_repo_id=${selectedRepoId}`,
        );

        if (!res.ok) {
          setStatus('assets 복원 실패');
          setPre('assetSelection', data);
          return;
        }

        const items = data.selected_repo_assets || [];
        items.forEach((it) => {
          if (!it) return;
          if (!it.asset_type || it.repo_path === undefined) return;
          selectedAssetKeys.add(assetKey(it.asset_type, it.repo_path));
        });
        updateAssetSelectionDebug();
        renderFilesTree();
      }

      async function activateSavedRepo(item) {
        if (!item) return;
        activeSelectedRepoId = item.id;
        activeSelectedRepoFullName = item.full_name || '';

        const idEl = document.getElementById('activeSelectedRepoId');
        if (idEl) idEl.value = String(activeSelectedRepoId);

        // 파일/contents API용 repoId(owner/repo)
        setActiveRepo(activeSelectedRepoFullName);

        expandedFolderPaths.clear();
        fileTreeRoot = null;
        lastFilesTreeItems = [];

        await loadRepoAssets(activeSelectedRepoId);
        // 파일 트리는 사용자가 명시적으로 로드 버튼을 눌렀을 때 호출한다(초기 로딩 지연 방지).
      }

      async function loadContentForPath(path) {
        const repoId = document.getElementById('repoId')?.value || '';
        const encoding = document.getElementById('contentsEncoding')?.value || 'raw';

        const safePath = encodeURIComponent(path);
        const url = `/api/github/repos/${repoId}/contents?path=${safePath}&encoding=${encoding}`;

        activeContentsPath = path;

        if (encoding === 'raw') {
          const { res, data } = await loadText(url);
          setStatus(res.ok ? 'contents 로딩 완료' : 'contents 로딩 실패');
          const pre = document.getElementById('contents');
          if (pre) pre.textContent = data;
        } else {
          const { res, data } = await loadJson(url);
          setStatus(res.ok ? 'contents 로딩 완료' : 'contents 로딩 실패');
          setPre('contents', data);
        }
        renderContentsFileList();
      }

      async function loadFilesTreeUI() {
        const repoId = document.getElementById('repoId')?.value || '';
        const path = encodeURIComponent(document.getElementById('filesPath')?.value || '/');

        if (!repoId) {
          setStatus('repoId가 비어있습니다.');
          return;
        }

        setStatus('Files Tree 로딩 중...');
        const url = `/api/github/repos/${repoId}/files?path=${path}`;
        const { res, data } = await loadJson(url);
        if (!res.ok) {
          setStatus('Files Tree 로딩 실패');
          fileTreeRoot = null;
          renderFilesTree();
          return;
        }

        lastFilesTreeItems = data.tree || [];
        fileTreeRoot = buildFileTreeHierarchy(lastFilesTreeItems);
        setStatus('Files Tree 로딩 완료');
        renderFilesTree();
        renderContentsFileList();
      }

      async function loadJson(url) {
        const res = await fetch(url, { credentials: 'include' });
        const data = await res.json().catch(() => ({}));
        return { res, data };
      }

      async function loadText(url) {
        const res = await fetch(url, { credentials: 'include' });
        const data = await res.text().catch(() => '');
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

      safeOnClick('btnReloadAssets', async () => {
        if (!activeSelectedRepoId) {
          setStatus('assets 복원에 필요한 active selected_repo_id가 없습니다.');
          return;
        }
        await loadRepoAssets(activeSelectedRepoId);
      });

      safeOnClick('btnSaveRepoAssets', async () => {
        if (!activeSelectedRepoId) {
          setStatus('먼저 저장된 레포를 선택하세요 (assets 대상).');
          return;
        }

        const assets = Array.from(selectedAssetKeys).map((key) => {
          const idx = key.indexOf(':');
          return {
            asset_type: key.slice(0, idx),
            repo_path: key.slice(idx + 1),
          };
        });

        if (!assets.length) {
          setStatus('저장할 assets가 없습니다.');
          return;
        }

        setStatus('assets 저장 중...');
        try {
          const res = await fetch('/api/user/selected-repo-assets', {
            method: 'PUT',
            headers: { 'content-type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({
              selected_repo_id: activeSelectedRepoId,
              assets,
            }),
          });
          const data = await res.json().catch(() => ({}));
          if (!res.ok) {
            setStatus('assets 저장 실패');
            setPre('assetSelection', data);
            return;
          }

          setStatus('assets 저장 완료');
          await loadRepoAssets(activeSelectedRepoId);
        } catch (e) {
          setStatus('assets 저장 예외');
          setPre('assetSelection', { error: String(e) });
        }
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

      safeOnClick('btnFilesTree', async () => {
        await loadFilesTreeUI();
      });

      safeOnClick('btnCommits', async () => {
        const repoId = document.getElementById('repoId').value;
        const author = document.getElementById('commitsAuthor').value.trim();
        const page = document.getElementById('commitsPage').value;
        const perPage = document.getElementById('commitsPerPage').value;
        const params = new URLSearchParams();
        params.append('page', page);
        params.append('per_page', perPage);
        if (author) params.append('author', author);
        const url = `/api/github/repos/${repoId}/commits?${params.toString()}`;
        const { res, data } = await loadJson(url);
        setStatus(res.ok ? 'GET /commits ok' : 'GET /commits failed');
        if (!res.ok) {
          setPre('commits', data);
          return;
        }

        const summary = data.summary || {};
        const commits = data.commits || [];

        const totalCommits = (summary.total_commits !== undefined && summary.total_commits !== null) ? summary.total_commits : 0;
        const authorCommits = (summary.author_commits !== undefined && summary.author_commits !== null) ? summary.author_commits : 0;
        const filesChangedTotal = (summary.files_changed_total !== undefined && summary.files_changed_total !== null) ? summary.files_changed_total : 0;
        const dateFrom = (summary.date_range && summary.date_range.from !== undefined && summary.date_range.from !== null) ? summary.date_range.from : 'n/a';
        const dateTo = (summary.date_range && summary.date_range.to !== undefined && summary.date_range.to !== null) ? summary.date_range.to : 'n/a';

        const summaryText = [
          `total_commits: ${totalCommits}`,
          `author_commits: ${authorCommits}`,
          `files_changed_total: ${filesChangedTotal}`,
          `date_range: ${dateFrom} ~ ${dateTo}`,
        ].join('\\n');

        const top = commits
          .slice(0, 10)
          .map((c) => {
            const cd = (c.date !== undefined && c.date !== null) ? c.date : '';
            const cm = (c.message !== undefined && c.message !== null) ? c.message : '';
            const fc = (c.files_changed !== undefined && c.files_changed !== null) ? c.files_changed : 0;
            return `- ${cd} | ${cm} | files: ${fc}`;
          })
          .join('\\n');
        document.getElementById('commits').textContent = `=== Summary ===\\n${summaryText}\\n\\n=== Commits (top ${Math.min(10, commits.length)}) ===\\n${top}`;
      });

      // ---- GitHub 임베딩 데모 (Chroma + LLM / 스텁) ----
      function buildExplicitCodeDocumentIds() {
        const full = (activeSelectedRepoFullName || document.getElementById('repoId')?.value || '').trim();
        if (!full) {
          return { ok: false, error: '활성 저장 레포 또는 repo_id(owner/repo)가 없습니다.' };
        }
        const ids = Array.from(selectedAssetKeys)
          .filter((k) => k.startsWith('code:'))
          .map((k) => `${full}/${k.slice('code:'.length)}`)
          .sort();
        if (!ids.length) {
          return {
            ok: false,
            error: '선택된 코드 파일이 없습니다. Files Tree에서 파일 체크 → 「선택 assets 저장」을 먼저 하세요.',
          };
        }
        return { ok: true, ids };
      }

      function focusEmbeddingPanel(message) {
        const panel = document.getElementById('embeddingDemo');
        const pre = document.getElementById('embeddingResult');
        if (pre && message) pre.textContent = message;
        if (panel) panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }

      async function postEmbeddingRequest(payload) {
        const repoId = (document.getElementById('repoId')?.value || '').trim();
        if (!repoId) {
          focusEmbeddingPanel('오류: repo_id(owner/repo) 입력이 비어 있습니다. 위에서 저장된 레포를 클릭하거나 repo_id를 채우세요.');
          setStatus('임베딩: repo_id 없음');
          return;
        }
        const url = `/api/github/repos/${encodeURIComponent(repoId)}/embedding`;
        setStatus('임베딩 요청 중… (파일 수·LLM에 따라 수 분 걸릴 수 있음)');
        focusEmbeddingPanel(
          'POST 전송됨. 서버 처리 중입니다…\\n\\n'
            + '- 상단 Status에도 같은 안내가 뜹니다.\\n'
            + '- 완료되면 여기에 JSON이 표시됩니다.\\n'
            + '- 터미널에는 응답 직후 POST .../embedding 한 줄이 찍힙니다.',
        );
        const bodyPayload = Object.assign({}, payload);
        if (document.getElementById('embedIncludeSummaries')?.checked) {
          bodyPayload.include_summaries = true;
        }
        console.info('[embedding] POST', url, bodyPayload);
        try {
          const res = await fetch(url, {
            method: 'POST',
            credentials: 'include',
            headers: { 'content-type': 'application/json' },
            body: JSON.stringify(bodyPayload),
          });
          const data = await res.json().catch(() => ({ _parse_error: true }));
          setPre('embeddingResult', { http_status: res.status, response: data });
          if (res.ok) {
            const n = (data && data.embedded !== undefined) ? data.embedded : '?';
            setStatus(`임베딩 완료 · embedded=${n}`);
          } else {
            const msg = (data && data.message) ? data.message : 'EMBEDDING_FAILED';
            setStatus(`임베딩 실패: ${msg}`);
          }
        } catch (e) {
          setStatus('임베딩 요청 예외');
          setPre('embeddingResult', { error: String(e) });
        }
      }

      safeOnClick('btnSyncHierarchy', async () => {
        if (!activeSelectedRepoId) {
          setPre('embeddingResult', { error: '저장된 레포를 먼저 선택하세요 (active selected_repo_id).' });
          setStatus('히스토리 반영: 활성 레포 없음');
          return;
        }
        setStatus('asset_hierarchy(code) 동기화 중…');
        try {
          const res = await fetch('/api/user/asset-hierarchy/sync-from-assets', {
            method: 'POST',
            credentials: 'include',
            headers: { 'content-type': 'application/json' },
            body: JSON.stringify({ selected_repo_id: activeSelectedRepoId }),
          });
          const data = await res.json().catch(() => ({}));
          setPre('embeddingResult', { http_status: res.status, response: data });
          setStatus(
            res.ok
              ? `SQLite 반영 완료 · code ${data.inserted !== undefined ? data.inserted : '?'}건`
              : 'SQLite 반영 실패',
          );
        } catch (e) {
          setStatus('SQLite 반영 예외');
          setPre('embeddingResult', { error: String(e) });
        }
      });

      safeOnClick('btnEmbedExplicit', async () => {
        const built = buildExplicitCodeDocumentIds();
        if (!built.ok) {
          setPre('embeddingResult', { error: built.error });
          setStatus(built.error);
          return;
        }
        const refRaw = (document.getElementById('embedRef')?.value || '').trim();
        const payload = { code_document_ids: built.ids };
        if (refRaw) payload.ref = refRaw;
        await postEmbeddingRequest(payload);
      });

      safeOnClick('btnEmbedFromDb', async () => {
        const refRaw = (document.getElementById('embedRef')?.value || '').trim();
        const payload = { code_document_ids: [] };
        if (refRaw) payload.ref = refRaw;
        await postEmbeddingRequest(payload);
      });

      window.addEventListener('load', () => {
        // 로딩 상태가 오래가면 사용자가 “왜 안 뜨지?”를 바로 알 수 있도록 시작 메시지를 준다.
        setStatus('loading /api/me...');
        loadMe();
      });
    </script>
  </body>
</html>
""".strip()
