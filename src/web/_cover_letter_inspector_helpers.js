      const inspectorNextRoundByDraft = new Map();

      function buildInspectorSuggestionList(items) {
        const ol = document.createElement('ol');
        ol.style.margin = '0';
        ol.style.paddingLeft = '1.2em';
        (items || []).forEach((it) => {
          if (!it || typeof it !== 'object') return;
          const li = document.createElement('li');
          const sec = (it.section != null && String(it.section).trim()) ? String(it.section).trim() : '';
          const sug = (it.suggestion != null && String(it.suggestion).trim()) ? String(it.suggestion).trim() : '';
          const rat = (it.rationale != null && String(it.rationale).trim()) ? String(it.rationale).trim() : '';
          const strong = document.createElement('strong');
          strong.textContent = sec || '제안';
          li.appendChild(strong);
          li.appendChild(document.createTextNode(': ' + sug));
          if (rat) {
            li.appendChild(document.createElement('br'));
            const sp = document.createElement('span');
            sp.style.color = 'var(--fg-muted)';
            sp.textContent = '근거: ' + rat;
            li.appendChild(sp);
          }
          ol.appendChild(li);
        });
        return ol;
      }

      async function runCoverLetterInspect(draftId, { userEdited, round }) {
        const payload = { draft_id: draftId, round: round };
        if (userEdited && String(userEdited).trim()) payload.user_edited = String(userEdited).trim();
        const res = await fetch('/api/cover-letter/inspect', {
          method: 'POST',
          credentials: 'include',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify(payload),
        });
        const data = await res.json().catch(() => ({}));
        return { res, data };
      }

