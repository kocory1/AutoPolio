"""
Autofolio UI: GitHub-inspired dark shell + shared CSS.

컨셉: From Code to Career — 코드·증거를 바탕으로 이직 서사를 쌓는 도구.
"""

from __future__ import annotations

# GitHub 다크 베이스 (#0d1117, #161b22, #30363d, 초록 액센트)
CSS_GITHUB_DARK = """
:root {
  --bg: #0d1117;
  --bg-deep: #010409;
  --bg-elevated: #161b22;
  --border: #30363d;
  --border-muted: #21262d;
  --fg: #e6edf3;
  --fg-muted: #8b949e;
  --accent: #238636;
  --accent-hover: #2ea043;
  --link: #58a6ff;
  --danger: #f85149;
  --warning: #d29922;
  --purple: #a371f7;
  --shadow-card: 0 4px 24px rgba(0, 0, 0, 0.28);
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans KR", Helvetica, Arial, sans-serif;
  background-color: var(--bg);
  background-image: radial-gradient(ellipse 100% 55% at 50% -18%, rgba(88, 166, 255, 0.06), transparent 52%);
  color: var(--fg);
  line-height: 1.55;
  min-height: 100vh;
}
.af-header {
  border-bottom: 1px solid var(--border);
  background: rgba(22, 27, 34, 0.88);
  position: sticky;
  top: 0;
  z-index: 100;
  backdrop-filter: blur(10px);
}
.af-header-inner {
  max-width: 1200px;
  margin: 0 auto;
  padding: 10px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
}
.af-brand { display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; }
.af-brand a {
  color: var(--fg);
  text-decoration: none;
  font-weight: 700;
  font-size: 1.05rem;
  letter-spacing: -0.02em;
}
.af-brand a:hover { color: var(--link); }
.af-tagline {
  color: var(--fg-muted);
  font-size: 0.78rem;
  font-weight: 500;
}
.af-tag {
  display: inline-block;
  vertical-align: middle;
  margin-right: 2px;
  padding: 3px 9px;
  border-radius: 6px;
  font-size: 0.65rem;
  font-weight: 650;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: #d2a8ff;
  background: rgba(163, 113, 247, 0.12);
  border: 1px solid rgba(163, 113, 247, 0.28);
  line-height: 1.2;
}
.af-title-row {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 10px;
}
a.af-link {
  color: var(--link);
  text-decoration: none;
  border-bottom: 1px solid rgba(88, 166, 255, 0.35);
  transition: color 0.15s ease, border-color 0.15s ease;
}
a.af-link:hover {
  color: #79c0ff;
  border-bottom-color: rgba(121, 192, 255, 0.55);
}
.af-nav {
  display: flex;
  gap: 4px;
  align-items: center;
  flex-wrap: wrap;
}
.af-nav a {
  color: var(--fg-muted);
  text-decoration: none;
  padding: 6px 14px;
  border-radius: 6px;
  font-size: 0.875rem;
  border: 1px solid transparent;
}
.af-nav a:hover {
  color: var(--fg);
  background: rgba(240, 246, 252, 0.06);
}
.af-nav a.af-active {
  color: var(--fg);
  border-color: var(--border);
  background: var(--bg-elevated);
}
.af-auth { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.af-status {
  font-size: 0.75rem;
  color: var(--fg-muted);
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.af-main { max-width: 1200px; margin: 0 auto; padding: 32px 20px 64px; }
.af-hero { margin-bottom: 32px; }
.af-hero h1 {
  font-size: 1.5rem;
  font-weight: 650;
  margin: 0 0 10px 0;
  letter-spacing: -0.03em;
}
.af-hero p {
  color: var(--fg-muted);
  margin: 0;
  font-size: 0.9375rem;
  max-width: 58ch;
  line-height: 1.65;
}
.af-card {
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--bg-elevated);
  padding: 22px 24px;
  margin-bottom: 20px;
  box-shadow: var(--shadow-card);
}
.af-card h2, .af-card h3 {
  margin-top: 0;
  font-size: 1.05rem;
  font-weight: 600;
}
.af-section-label {
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--fg-muted);
  margin-bottom: 6px;
}
.af-hint { font-size: 0.88rem; color: var(--fg-muted); margin: 8px 0 0 0; line-height: 1.5; }
.af-hint code {
  font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
  font-size: 0.82em;
  background: var(--bg-deep);
  padding: 2px 6px;
  border-radius: 4px;
  border: 1px solid var(--border-muted);
  color: var(--link);
}
.af-btn {
  padding: 8px 14px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 500;
  border: 1px solid var(--border);
  background: var(--bg-elevated);
  color: var(--fg);
}
.af-btn:hover { border-color: var(--fg-muted); background: rgba(240, 246, 252, 0.06); }
.af-btn-primary {
  background: var(--accent);
  border-color: var(--accent);
  color: #fff;
}
.af-btn-primary:hover { background: var(--accent-hover); border-color: var(--accent-hover); }
.af-btn-ghost { background: transparent; color: var(--link); border-color: var(--border); }
.af-btn-ghost:hover { border-color: var(--link); background: rgba(88, 166, 255, 0.08); }
.af-btn-emphasis {
  background: linear-gradient(180deg, rgba(210, 153, 34, 0.2) 0%, rgba(210, 153, 34, 0.09) 100%);
  border-color: rgba(210, 153, 34, 0.45);
  color: #eac54f;
}
.af-btn-emphasis:hover {
  background: linear-gradient(180deg, rgba(210, 153, 34, 0.3) 0%, rgba(210, 153, 34, 0.12) 100%);
  border-color: rgba(210, 153, 34, 0.62);
  color: #f0d175;
}
.af-pre {
  background: var(--bg-deep);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 14px 16px;
  overflow-x: auto;
  font-size: 12px;
  font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
  color: #7ee787;
  line-height: 1.45;
}
.af-divider {
  border: none;
  border-top: 1px solid var(--border);
  margin: 28px 0;
}
.af-input, .af-select, .af-textarea {
  background: var(--bg-deep);
  border: 1px solid var(--border);
  color: var(--fg);
  border-radius: 6px;
  padding: 8px 10px;
  font-size: 0.875rem;
  width: 100%;
  max-width: 100%;
}
.af-input:focus, .af-select:focus, .af-textarea:focus {
  outline: none;
  border-color: var(--link);
  box-shadow: 0 0 0 3px rgba(88, 166, 255, 0.15);
}
.af-label { display: block; font-size: 0.8rem; color: var(--fg-muted); margin-bottom: 4px; }
.af-subtitle {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--fg-muted);
  margin: 1.35rem 0 0.5rem 0;
  letter-spacing: 0.02em;
}
.af-field { margin-bottom: 12px; }
.af-field:last-child { margin-bottom: 0; }
.af-w-md { max-width: 420px; }
.af-w-lg { max-width: 560px; }
.af-w-xl { max-width: 520px; }
.af-radio-group {
  display: flex;
  flex-wrap: wrap;
  gap: 18px;
  margin-bottom: 14px;
  color: var(--fg-muted);
  font-size: 0.88rem;
}
.af-radio-group label { cursor: pointer; display: inline-flex; align-items: center; gap: 8px; }
.af-radio-group input { accent-color: var(--link); }
.af-row-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  margin-bottom: 14px;
}
.af-inline-strong { font-weight: 600; color: var(--fg); }
.af-muted-hint-inline { margin-left: 8px; }
.af-block-top {
  margin-top: 18px;
  padding-top: 16px;
  border-top: 1px solid var(--border);
}
.af-block-top-title {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--fg-muted);
  margin-bottom: 10px;
}
.af-essay-list { margin-top: 10px; font-size: 0.88rem; padding-left: 8px; color: var(--fg-muted); }
.af-mt-sm { margin-top: 8px; }
.af-hidden { display: none; }
/* repo grid — hub */
#repoCardsGrid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 14px;
  margin-top: 12px;
}
.repo-card {
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 14px 16px;
  background: var(--bg-deep);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.2);
}
.repo-card h4 { margin: 0 0 8px 0; font-size: 0.9rem; color: var(--fg); word-break: break-all; }
.repo-card .repo-tree-wrap {
  max-height: 240px;
  overflow: auto;
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 8px 10px;
  margin: 8px 0;
  font-size: 12px;
  background: var(--bg-elevated);
  color: var(--fg-muted);
}
.repo-card .repo-card-status { font-size: 12px; color: var(--fg-muted); margin-top: 6px; min-height: 1.2em; }
.repo-card .repo-save-ok { color: var(--accent-hover); font-size: 12px; font-weight: 600; }
.repo-card-tabs {
  display: flex; flex-wrap: wrap; gap: 4px; margin: 10px 0 8px 0; font-size: 13px;
  border-bottom: 1px solid var(--border); padding-bottom: 4px;
}
.repo-tab-btn {
  border: none;
  border-bottom: 2px solid transparent;
  background: transparent;
  cursor: pointer;
  padding: 6px 10px;
  color: var(--fg-muted);
  font-size: 13px;
}
.repo-tab-btn.repo-tab-active {
  font-weight: 600;
  border-bottom-color: var(--link);
  color: var(--link);
}
.repo-tab-panel { display: none; }
.repo-tab-panel.repo-tab-visible { display: block; }
.repo-card-error {
  margin: 8px 0; padding: 8px 10px; border-radius: 6px;
  background: rgba(248, 81, 73, 0.12); border: 1px solid rgba(248, 81, 73, 0.35);
  color: #ffa198; font-size: 12px; display: none;
}
.repo-tab-panel .repoBranchRef {
  width: 100%; max-width: 260px; padding: 6px 8px; border-radius: 4px;
  border: 1px solid var(--border); font-size: 12px;
  background: var(--bg-deep); color: var(--fg);
}
.repo-view-pre, .repo-commits-pre {
  max-height: 220px; overflow: auto; font-size: 12px; margin-top: 8px;
  background: var(--bg-deep); border: 1px solid var(--border); padding: 8px; border-radius: 6px;
  color: var(--fg-muted);
}
#embeddingResult { min-height: 3rem; max-height: 480px; }
.demo-steps { margin: 12px 0 18px 1.2em; color: var(--fg-muted); }
.demo-steps li { margin-bottom: 6px; }
/* Writer / Inspector — cover letter page */
#writerDraftDemo .wd-q-row {
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 14px;
  margin-bottom: 12px;
  background: var(--bg-deep);
}
#writerDraftDemo .wd-card {
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px 18px;
  margin-bottom: 14px;
  background: var(--bg-deep);
}
#writerDraftDemo .wd-card-sub { font-size: 0.85rem; color: var(--fg-muted); margin-bottom: 10px; line-height: 1.45; }
#writerDraftDemo .wd-card-body { white-space: pre-wrap; line-height: 1.6; color: var(--fg); word-break: break-word; }
#writerDraftDemo .wd-card-body.wd-fail { color: var(--warning); }
#writerDraftDemo .wd-char-badge {
  display: inline-block; margin-top: 10px; padding: 4px 10px; border-radius: 999px;
  background: rgba(35, 134, 54, 0.2); color: #56d364; font-size: 12px; font-weight: 600;
  border: 1px solid rgba(35, 134, 54, 0.45);
}
#writerDraftDemo .wd-repo-tag {
  display: inline-block; margin: 4px 6px 0 0; padding: 4px 10px; border-radius: 999px;
  background: rgba(88, 166, 255, 0.1); border: 1px solid rgba(88, 166, 255, 0.35);
  color: var(--link); font-size: 12px;
}
#writerDraftDemo .wd-essay-yes {
  display: inline-block; padding: 6px 12px; border-radius: 8px;
  background: rgba(35, 134, 54, 0.2); color: #56d364; font-size: 13px; font-weight: 600;
  border: 1px solid rgba(35, 134, 54, 0.45);
}
#writerDraftDemo .wd-essay-no {
  display: inline-block; padding: 6px 12px; border-radius: 8px;
  background: var(--bg-elevated); color: var(--fg-muted); font-size: 13px;
  border: 1px solid var(--border);
}
#writerDraftDemo #writerDraftErrorArea {
  display: none; margin-top: 12px; padding: 14px; border-radius: 8px;
  background: rgba(248, 81, 73, 0.1); border: 1px solid rgba(248, 81, 73, 0.35);
  color: #ffa198; font-size: 14px;
}
#writerDraftDemo #writerErrorJson {
  margin-top: 8px; background: var(--bg-deep); color: var(--fg-muted);
  border: 1px solid var(--border);
}
.wd-inspector-wrap { margin-top: 14px; padding-top: 14px; border-top: 1px dashed var(--border); }
.wd-inspector-wrap .wd-inspector-actions { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-bottom: 8px; }
.wd-inspector-wrap .wd-inspector-suggestions {
  font-size: 0.88rem; color: var(--fg); line-height: 1.5; margin: 8px 0;
  padding: 12px 14px; background: var(--bg-elevated); border-radius: 8px;
  border: 1px solid var(--border); max-height: 280px; overflow: auto;
}
.wd-inspector-wrap .wd-inspector-suggestions li { margin-bottom: 8px; }
.wd-inspector-wrap textarea.wd-inspector-edit {
  width: 100%; min-height: 100px; padding: 10px; border-radius: 6px;
  border: 1px solid var(--border); font-size: 13px;
  background: var(--bg-deep); color: var(--fg);
}
.wd-inspector-wrap .wd-inspector-meta { font-size: 12px; color: var(--fg-muted); margin-top: 6px; }
"""


def header_html(active: str) -> str:
    """active: 'hub' | 'letter'"""
    hub_cls = "af-active" if active == "hub" else ""
    letter_cls = "af-active" if active == "letter" else ""
    return f"""
    <header class="af-header">
      <div class="af-header-inner">
        <div class="af-brand">
          <a href="/">Autofolio</a>
          <span class="af-tagline">From Code to Career</span>
        </div>
        <nav class="af-nav" aria-label="주요 메뉴">
          <a href="/dashboard" class="{hub_cls}">워크스페이스</a>
          <a href="/cover-letter" class="{letter_cls}">자소서</a>
          <a href="/docs" target="_blank" rel="noopener">API</a>
        </nav>
        <div class="af-auth">
          <button type="button" class="af-btn af-btn-ghost" id="loginBtn">GitHub 로그인</button>
          <button type="button" class="af-btn af-btn-ghost" id="logoutBtn">로그아웃</button>
          <span id="status" class="af-status">…</span>
        </div>
      </div>
    </header>
    """
