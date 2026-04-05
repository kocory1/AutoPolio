      function renderWriterDraftsSuccess(data) {
        hideWriterError();
        const container = document.getElementById('writerDraftCards');
        if (!container) return;
        container.innerHTML = '';
        inspectorNextRoundByDraft.clear();
        const drafts = (data && data.drafts) ? data.drafts : [];
        drafts.forEach((d) => {
          const draftId = (d && d.draft_id) ? String(d.draft_id) : '';
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

          const insWrap = document.createElement('div');
          insWrap.className = 'wd-inspector-wrap';
          const insRow = document.createElement('div');
          insRow.className = 'wd-inspector-actions';
          const btnInspect = document.createElement('button');
          btnInspect.type = 'button';
          btnInspect.className = 'af-btn af-btn-ghost';
          btnInspect.style.fontSize = '13px';
          btnInspect.textContent = 'Inspector 제안';
          const btnReinspect = document.createElement('button');
          btnReinspect.type = 'button';
          btnReinspect.className = 'af-btn af-btn-primary';
          btnReinspect.style.fontSize = '13px';
          btnReinspect.style.background = '#6e40c9';
          btnReinspect.style.borderColor = '#6e40c9';
          btnReinspect.textContent = '수정본으로 재첨삭';
          btnReinspect.style.display = 'none';
          const sugBox = document.createElement('div');
          sugBox.className = 'wd-inspector-suggestions';
          sugBox.style.display = 'none';
          const taEdit = document.createElement('textarea');
          taEdit.className = 'wd-inspector-edit af-textarea';
          taEdit.placeholder = '수정한 초안을 붙여 넣은 뒤 재첨삭하세요.';
          taEdit.style.display = 'none';
          const insMeta = document.createElement('div');
          insMeta.className = 'wd-inspector-meta';
          insMeta.style.display = 'none';

          const runFirstInspect = async () => {
            if (!draftId) {
              insMeta.textContent = 'draft_id가 없습니다.';
              insMeta.style.display = 'block';
              insWrap.style.display = 'block';
              return;
            }
            if (!ans.trim()) {
              insMeta.textContent = '초안이 비어 있어 Inspector를 호출할 수 없습니다.';
              insMeta.style.display = 'block';
              insWrap.style.display = 'block';
              return;
            }
            btnInspect.disabled = true;
            btnReinspect.disabled = true;
            insMeta.style.display = 'block';
            insMeta.textContent = 'Inspector 호출 중…';
            insWrap.style.display = 'block';
            try {
              const { res, data: insp } = await runCoverLetterInspect(draftId, { userEdited: null, round: 0 });
              if (!res.ok) {
                const msg = (insp && insp.message) ? insp.message : (insp && insp.error) ? insp.error : String(res.status);
                insMeta.textContent = '실패: ' + msg;
                btnInspect.disabled = false;
                return;
              }
              sugBox.innerHTML = '';
              sugBox.appendChild(buildInspectorSuggestionList(insp.suggestions || []));
              sugBox.style.display = 'block';
              taEdit.style.display = 'block';
              taEdit.value = ans;
              btnReinspect.style.display = 'inline-block';
              const sr = (insp.round != null) ? insp.round : 0;
              const mx = (insp.max_rounds != null) ? insp.max_rounds : 5;
              inspectorNextRoundByDraft.set(draftId, sr + 1);
              insMeta.textContent = '라운드 ' + sr + ' · 다음 재첨삭 round ' + (sr + 1) + ' / max ' + mx;
              if (sr + 1 >= mx) {
                btnReinspect.disabled = true;
                insMeta.textContent += ' (재첨삭 상한)';
              }
            } catch (e) {
              insMeta.textContent = '예외: ' + String(e);
            } finally {
              btnInspect.disabled = false;
            }
          };

          const runResumeInspect = async () => {
            if (!draftId) return;
            const nextR = inspectorNextRoundByDraft.has(draftId) ? inspectorNextRoundByDraft.get(draftId) : 1;
            const edited = taEdit.value ? String(taEdit.value).trim() : '';
            if (!edited) {
              insMeta.style.display = 'block';
              insMeta.textContent = '수정본을 입력해 주세요.';
              return;
            }
            btnInspect.disabled = true;
            btnReinspect.disabled = true;
            insMeta.textContent = '재첨삭 요청 중… (round ' + nextR + ')';
            try {
              const { res, data: insp } = await runCoverLetterInspect(draftId, { userEdited: edited, round: nextR });
              if (!res.ok) {
                const msg = (insp && insp.message) ? insp.message : (insp && insp.error) ? insp.error : String(res.status);
                insMeta.textContent = '실패: ' + msg;
                btnReinspect.disabled = false;
                return;
              }
              sugBox.innerHTML = '';
              sugBox.appendChild(buildInspectorSuggestionList(insp.suggestions || []));
              sugBox.style.display = 'block';
              const sr = (insp.round != null) ? insp.round : nextR;
              const mx = (insp.max_rounds != null) ? insp.max_rounds : 5;
              inspectorNextRoundByDraft.set(draftId, sr + 1);
              insMeta.textContent = '라운드 ' + sr + ' · 다음 재첨삭 round ' + (sr + 1) + ' / max ' + mx;
              btnReinspect.disabled = false;
              if (sr + 1 >= mx) {
                btnReinspect.disabled = true;
                insMeta.textContent += ' (재첨삭 상한)';
              }
            } catch (e) {
              insMeta.textContent = '예외: ' + String(e);
              btnReinspect.disabled = false;
            } finally {
              btnInspect.disabled = false;
            }
          };

          btnInspect.addEventListener('click', runFirstInspect);
          btnReinspect.addEventListener('click', runResumeInspect);

          insRow.appendChild(btnInspect);
          insRow.appendChild(btnReinspect);
          insWrap.appendChild(insRow);
          insWrap.appendChild(sugBox);
          insWrap.appendChild(taEdit);
          insWrap.appendChild(insMeta);
          card.appendChild(insWrap);
          container.appendChild(card);
        });
        setWriterUsedAssets(data.used_assets || {});
      }
