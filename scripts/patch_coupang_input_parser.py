from pathlib import Path

p = Path('index.html')
s = p.read_text(encoding='utf-8')
old = """        const url = input.value.trim();
        if (!url.startsWith('https://www.coupang.com/')) {
          status.textContent = '올바른 쿠팡 상품 링크를 입력해주세요.';
          input.focus();
          return;
        }
"""
new = """        const raw = input.value.trim();
        const match = raw.match(/https:\/\/[^\\s]+/);
        const url = match ? match[0].replace(/[.,)\\]}>\"']+$/, '') : '';
        const isCoupang = url.startsWith('https://www.coupang.com/') || url.startsWith('https://link.coupang.com/');
        if (!isCoupang) {
          status.textContent = '입력 내용에서 올바른 쿠팡 https 링크를 찾지 못했습니다.';
          input.focus();
          return;
        }
"""
if old not in s:
    raise SystemExit('Old uploader parser not found; no change made.')
s = s.replace(old, new, 1)
p.write_text(s, encoding='utf-8')
print('Uploader parser patched.')
