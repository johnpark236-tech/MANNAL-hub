from pathlib import Path
import re

p = Path('index.html')
s = p.read_text(encoding='utf-8')

pattern = re.compile(r'<script>\s*\(function \(\) \{.*?coupangUrlInput.*?issues/new.*?\}\)\(\);\s*</script>', re.S)

new_script = r'''<script>
    (function () {
      const WORKER_URL = 'https://mannal-coupang-uploader.johnpark236.workers.dev';
      const input = document.getElementById('coupangUrlInput');
      const button = document.getElementById('coupangUploadBtn');
      const status = document.getElementById('coupangUploadStatus');
      if (!input || !button || !status) return;

      function extractCoupangUrl(raw) {
        const match = String(raw || '').match(/https:\/\/[^\s]+/);
        if (!match) return '';
        const url = match[0].replace(/[.,)\]}>\"']+$/, '');
        if (url.startsWith('https://www.coupang.com/') || url.startsWith('https://link.coupang.com/')) {
          return url;
        }
        return '';
      }

      function ensureModalStyle() {
        if (document.getElementById('coupangWorkerModalStyle')) return;
        const style = document.createElement('style');
        style.id = 'coupangWorkerModalStyle';
        style.textContent = `
          .cwm-overlay{position:fixed;inset:0;background:rgba(0,0,0,.48);display:flex;align-items:center;justify-content:center;z-index:99999;padding:20px}
          .cwm-box{width:min(360px,100%);background:#fff;border-radius:18px;padding:24px;box-shadow:0 18px 60px rgba(0,0,0,.22);text-align:center}
          .cwm-title{font-size:19px;font-weight:900;margin:0 0 10px}
          .cwm-message{font-size:14px;line-height:1.6;color:#555;margin:0 0 18px}
          .cwm-input{width:100%;box-sizing:border-box;border:1.5px solid #ddd;border-radius:12px;padding:12px 14px;font-size:16px;margin:2px 0 16px;outline:none}
          .cwm-input:focus{border-color:#ff5a7d}
          .cwm-actions{display:flex;gap:10px;justify-content:center}
          .cwm-btn{border:0;border-radius:11px;padding:11px 20px;font-weight:800;cursor:pointer}
          .cwm-btn-primary{background:#ff5a7d;color:#fff}
          .cwm-btn-secondary{background:#f1f1f3;color:#333}
          .cwm-spinner{width:34px;height:34px;border:4px solid #eee;border-top-color:#ff5a7d;border-radius:50%;margin:4px auto 16px;animation:cwmspin .8s linear infinite}
          @keyframes cwmspin{to{transform:rotate(360deg)}}
        `;
        document.head.appendChild(style);
      }

      function removeModal() {
        const old = document.getElementById('coupangWorkerModal');
        if (old) old.remove();
      }

      function showMessage(title, message, onOk) {
        ensureModalStyle();
        removeModal();
        const overlay = document.createElement('div');
        overlay.className = 'cwm-overlay';
        overlay.id = 'coupangWorkerModal';
        overlay.innerHTML = `<div class="cwm-box"><h3 class="cwm-title"></h3><p class="cwm-message"></p><div class="cwm-actions"><button class="cwm-btn cwm-btn-primary" type="button">확인</button></div></div>`;
        overlay.querySelector('.cwm-title').textContent = title;
        overlay.querySelector('.cwm-message').textContent = message;
        overlay.querySelector('button').onclick = () => { removeModal(); if (onOk) onOk(); };
        document.body.appendChild(overlay);
      }

      function showLoading() {
        ensureModalStyle();
        removeModal();
        const overlay = document.createElement('div');
        overlay.className = 'cwm-overlay';
        overlay.id = 'coupangWorkerModal';
        overlay.innerHTML = `<div class="cwm-box"><div class="cwm-spinner"></div><h3 class="cwm-title">업로드 중입니다</h3><p class="cwm-message">쿠팡 광고를 처리하고 있습니다.<br>잠시만 기다려주세요.</p></div>`;
        document.body.appendChild(overlay);
      }

      function askPassword(onConfirm) {
        ensureModalStyle();
        removeModal();
        const overlay = document.createElement('div');
        overlay.className = 'cwm-overlay';
        overlay.id = 'coupangWorkerModal';
        overlay.innerHTML = `<div class="cwm-box"><h3 class="cwm-title">관리자 비밀번호</h3><p class="cwm-message">업로드 비밀번호를 입력해주세요.</p><input class="cwm-input" type="password" autocomplete="current-password" placeholder="비밀번호"><div class="cwm-actions"><button class="cwm-btn cwm-btn-secondary" type="button" data-cancel>취소</button><button class="cwm-btn cwm-btn-primary" type="button" data-ok>확인</button></div></div>`;
        const pw = overlay.querySelector('.cwm-input');
        overlay.querySelector('[data-cancel]').onclick = removeModal;
        const confirm = () => {
          if (!pw.value) { pw.focus(); return; }
          const value = pw.value;
          removeModal();
          onConfirm(value);
        };
        overlay.querySelector('[data-ok]').onclick = confirm;
        pw.addEventListener('keydown', e => { if (e.key === 'Enter') confirm(); });
        document.body.appendChild(overlay);
        setTimeout(() => pw.focus(), 30);
      }

      async function pollUntilComplete(issueNumber) {
        const deadline = Date.now() + 120000;
        while (Date.now() < deadline) {
          await new Promise(resolve => setTimeout(resolve, 2000));
          const resp = await fetch(`${WORKER_URL}/status?issue=${encodeURIComponent(issueNumber)}`, { cache: 'no-store' });
          const data = await resp.json().catch(() => ({}));
          if (!resp.ok || data.success === false) {
            throw new Error(data.message || '처리 상태 확인에 실패했습니다.');
          }
          if (data.completed) return;
        }
        throw new Error('업로드 요청은 접수되었지만 완료 확인 시간이 초과되었습니다. GitHub Actions 상태를 확인해주세요.');
      }

      button.addEventListener('click', function () {
        const raw = input.value.trim();
        const url = extractCoupangUrl(raw);
        if (!url) {
          status.textContent = '입력 내용에서 올바른 쿠팡 https 링크를 찾지 못했습니다.';
          input.focus();
          return;
        }

        askPassword(async (password) => {
          button.disabled = true;
          status.textContent = '업로드 요청 중...';
          showLoading();
          try {
            const resp = await fetch(`${WORKER_URL}/upload`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ password, text: raw })
            });
            const data = await resp.json().catch(() => ({}));
            if (!resp.ok || data.success === false) {
              if (resp.status === 401 || data.code === 'BAD_PASSWORD') {
                throw new Error('비밀번호가 올바르지 않습니다.');
              }
              throw new Error(data.message || '업로드 요청에 실패했습니다.');
            }

            await pollUntilComplete(data.issueNumber);
            status.textContent = '업로드가 완료되었습니다.';
            showMessage('완료', '업로드가 완료되었습니다.', () => {
              const u = new URL(window.location.href);
              u.searchParams.set('_refresh', Date.now().toString());
              window.location.href = u.toString();
            });
          } catch (err) {
            status.textContent = err && err.message ? err.message : '업로드 중 오류가 발생했습니다.';
            showMessage('업로드 실패', status.textContent);
          } finally {
            button.disabled = false;
          }
        });
      });
    })();
  </script>'''

m = pattern.search(s)
if not m:
    raise SystemExit('Existing Coupang uploader script block was not found.')

s = s[:m.start()] + new_script + s[m.end():]
p.write_text(s, encoding='utf-8')
print('Coupang uploader connected to Cloudflare Worker.')
