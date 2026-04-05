"""
자소서 전용 페이지: 채용공고 저장 → Writer 초안 → Inspector 재첨삭.

워크스페이스(`/dashboard`)와 분리. GitHub 다크 테마(`ui_theme`) 공유.
"""

from __future__ import annotations

from pathlib import Path

from src.web.ui_theme import CSS_GITHUB_DARK, header_html

_HERE = Path(__file__).resolve().parent

_JS_PREAMBLE = """
      const setStatus = (text) => { document.getElementById('status').textContent = text; };
      const setMe = (obj) => { document.getElementById('me').textContent = obj ? JSON.stringify(obj, null, 2) : ''; };
      const setPre = (id, obj) => {
        const el = document.getElementById(id);
        if (!el) return;
        el.textContent = obj ? JSON.stringify(obj, null, 2) : '';
      };

      setStatus('script loaded');

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

"""

_JS_LOAD = """
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
          await loadRecentJobs();
        } catch (e) {
          setStatus('failed to load /api/me');
          setMe({ error: String(e) });
        }
      }

      safeOnClick('loginBtn', () => { window.location.href = '/api/auth/github/login'; });
      safeOnClick('logoutBtn', () => { window.location.href = '/api/auth/logout'; });

"""

# 채용공고 parse (파일 조각이 잘린 경우 대비해 본 페이지에 완결본 유지)
_JS_JOB = """
      document.querySelectorAll('input[name="jobSource"]').forEach((el) => {
        el.addEventListener('change', () => {
          const manual = document.querySelector('input[name="jobSource"]:checked').value === 'manual';
          const mf = document.getElementById('jobManualFields');
          const uf = document.getElementById('jobUrlField');
          if (mf) mf.classList.toggle('af-hidden', !manual);
          if (uf) uf.classList.toggle('af-hidden', manual);
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

"""


def _strip_orphan_opening(raw: str) -> str:
    """git에서 잘린 이전 블록 꼬리(`}\\n});`) 제거."""
    prefix = "        }\n      });\n\n"
    if raw.startswith(prefix):
        return raw[len(prefix) :]
    return raw


def _strip_script_close(raw: str) -> str:
    s = raw.rstrip()
    if s.endswith("</script>"):
        s = s[: -len("</script>")].rstrip()
    return s


def _replace_render_success(wb: str, replacement: str) -> str:
    mark = "      function renderWriterDraftsSuccess(data) {"
    anchor = "\n\n      safeOnClick('btnWriterAddQ'"
    start = wb.find(mark)
    if start == -1:
        raise RuntimeError("renderWriterDraftsSuccess not found in writer block")
    end = wb.find(anchor, start)
    if end == -1:
        raise RuntimeError("anchor after renderWriterDraftsSuccess not found")
    return wb[:start] + replacement.rstrip() + wb[end:]


def _darken_writer_js(wb: str) -> str:
    return (
        wb.replace("btn-demo-ghost", "af-btn af-btn-ghost")
        .replace("'#0f172a'", "'var(--fg)'")
        .replace("'#334155'", "'var(--fg-muted)'")
        .replace("'#cbd5e1'", "'var(--border)'")
    )


def _build_script() -> str:
    helpers = (_HERE / "_cover_letter_inspector_helpers.js").read_text(encoding="utf-8")
    render_ins = (_HERE / "_cover_letter_render_inspector.js").read_text(encoding="utf-8")
    writer_raw = (_HERE / "_writer_block_from_git.txt").read_text(encoding="utf-8")
    wb = _strip_orphan_opening(writer_raw)
    wb = _strip_script_close(wb)
    wb = _replace_render_success(wb, render_ins)
    idx = wb.find("      const WRITER_Q_MIN")
    if idx == -1:
        raise RuntimeError("WRITER_Q_MIN not found in writer block")
    wb = wb[:idx] + helpers + "\n" + wb[idx:]
    wb = _darken_writer_js(wb)
    return _JS_PREAMBLE + _JS_LOAD + _JS_JOB + "\n" + wb


def _cover_body_html() -> str:
    return """
    <main class="af-main">
      <div class="af-hero">
        <h1>자소서</h1>
        <p>채용 공고를 저장하고, 코드·합격 자소서 RAG를 바탕으로 초안을 쓴 뒤 Inspector로 다듬습니다. 레포 임베딩은 <a class="af-link" href="/dashboard">워크스페이스</a>에서 먼저 진행하세요.</p>
      </div>

      <section class="af-card" aria-labelledby="session-title">
        <div class="af-section-label">Session</div>
        <h2 id="session-title">계정</h2>
        <pre id="me" class="af-pre"></pre>
      </section>

      <section class="af-card" id="jobParseDemo" aria-labelledby="job-parse-title">
        <div class="af-section-label">Job</div>
        <h2 id="job-parse-title" class="af-title-row"><span class="af-tag">jobs</span> 채용공고 저장</h2>
        <p class="af-hint">
          <code>POST /api/jobs/parse</code>로 공고를 저장하고 <strong>job_id</strong>를 받습니다.
          아래 Writer에서 공고 맥락으로 사용됩니다.
        </p>
        <div class="af-radio-group">
          <label><input type="radio" name="jobSource" value="manual" checked /> 직접 입력</label>
          <label><input type="radio" name="jobSource" value="url" /> URL</label>
        </div>
        <div id="jobManualFields">
          <div class="af-field"><label class="af-label" for="jobCompanyName">company_name *</label>
            <input id="jobCompanyName" class="af-input af-w-md" placeholder="기업명" />
          </div>
          <div class="af-field"><label class="af-label" for="jobPositionTitle">position_title *</label>
            <input id="jobPositionTitle" class="af-input af-w-md" placeholder="포지션명" />
          </div>
          <div class="af-field"><label class="af-label" for="jobCompanyPersona">company_persona</label>
            <input id="jobCompanyPersona" class="af-input af-w-md" placeholder="기업 인재상" />
          </div>
          <div class="af-field"><label class="af-label" for="jobDuties">duties (한 줄에 한 항목)</label>
            <textarea id="jobDuties" class="af-textarea af-w-lg" rows="3" placeholder="담당 업무"></textarea>
          </div>
          <div class="af-field"><label class="af-label" for="jobRequirements">requirements</label>
            <textarea id="jobRequirements" class="af-textarea af-w-lg" rows="2" placeholder="자격 요건"></textarea>
          </div>
          <div class="af-field"><label class="af-label" for="jobPreferences">preferences</label>
            <textarea id="jobPreferences" class="af-textarea af-w-lg" rows="2" placeholder="우대 사항"></textarea>
          </div>
        </div>
        <div id="jobUrlField" class="af-field af-hidden">
          <label class="af-label" for="jobUrl">채용공고 URL *</label>
          <input id="jobUrl" class="af-input af-w-xl" placeholder="https://..." />
        </div>
        <button type="button" class="af-btn af-btn-emphasis" id="btnJobParse">공고 저장</button>
        <h3 class="af-subtitle">응답</h3>
        <pre id="jobParseResult" class="af-pre"></pre>
      </section>

      <section class="af-card" id="writerDraftDemo" aria-labelledby="writer-draft-title">
        <div class="af-section-label">Writer · Inspector</div>
        <h2 id="writer-draft-title" class="af-title-row"><span class="af-tag">write</span> 초안 · 첨삭</h2>
        <p class="af-hint">
          선택 <strong>job_id</strong>는 아래 공고 목록에서 고릅니다. 초안 생성 후 <strong>Inspector 제안</strong>으로 수정 루프를 돌릴 수 있습니다.
        </p>
        <div class="af-field">
          <label class="af-label" for="draftJobSelect">공고 선택 (최근 저장)</label>
          <select id="draftJobSelect" class="af-select af-w-md">
            <option value="">공고 맥락 없이</option>
          </select>
        </div>
        <div class="af-field">
          <span class="af-inline-strong">문항</span>
          <span class="af-hint af-muted-hint-inline">1~5개 · 글자 제한</span>
        </div>
        <div id="writerQuestionList"></div>
        <div class="af-row-actions">
          <button type="button" class="af-btn af-btn-ghost" id="btnWriterAddQ">문항 추가</button>
          <button type="button" class="af-btn af-btn-primary" id="btnWriterDraft">초안 생성</button>
        </div>
        <div id="writerDraftErrorArea" aria-live="polite">
          <div id="writerErrorLine"></div>
          <pre id="writerErrorJson" class="af-pre af-mt-sm af-hidden"></pre>
        </div>
        <h3 class="af-subtitle">결과</h3>
        <div id="writerDraftCards"></div>
        <div id="writerUsedAssetsBlock" class="af-block-top">
          <div class="af-block-top-title">참조 레포</div>
          <div id="writerRepoTags" class="af-hint">참조 레포 없음</div>
          <div class="af-mt-sm">
            <span id="writerEssaysBadge" class="wd-essay-no">합격 자소서 미참조</span>
            <div id="writerEssaysList" class="wd-essay-list af-essay-list"></div>
          </div>
        </div>
      </section>
    </main>
    """


cover_letter_html = (
    """<!doctype html>
<html lang="ko">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Autofolio — 자소서</title>
    <style>
"""
    + CSS_GITHUB_DARK
    + """
    .af-textarea { min-height: 72px; font-family: inherit; }
    </style>
  </head>
  <body>
"""
    + header_html("letter")
    + _cover_body_html()
    + """
    <script>
"""
    + _build_script()
    + """
    </script>
  </body>
</html>
"""
)
