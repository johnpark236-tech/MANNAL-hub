from pathlib import Path

p = Path('index.html')
s = p.read_text(encoding='utf-8')

old = '<input id="coupangUrlInput" type="url" inputmode="url" autocomplete="off" placeholder="https://www.coupang.com/vp/products/...">'
new = '<textarea id="coupangUrlInput" rows="4" inputmode="url" autocomplete="off" placeholder="쿠팡 공유 문구 또는 https://www.coupang.com/... / https://link.coupang.com/... 링크를 붙여넣으세요."></textarea>'
if old not in s:
    raise SystemExit('Coupang input element not found.')
s = s.replace(old, new, 1)

s = s.replace('.coupang-upload-row input {', '.coupang-upload-row input,\n    .coupang-upload-row textarea {', 1)
s = s.replace('.coupang-upload-row input:focus { border-color: var(--pink); }', '.coupang-upload-row input:focus,\n    .coupang-upload-row textarea:focus { border-color: var(--pink); }', 1)

extra = '''\n    .coupang-upload-row textarea {\n      resize: vertical;\n      min-height: 92px;\n      line-height: 1.45;\n    }\n'''
marker = '    .coupang-upload-row button {'
if extra.strip() not in s and marker in s:
    s = s.replace(marker, extra + marker, 1)

old_help = '쿠팡 일반 상품 링크를 붙여넣으세요. 파트너스 링크 변환과 광고 추가는 GitHub Actions에서 안전하게 처리됩니다.'
new_help = '쿠팡 공유 문구 전체, 데스크탑 상품 링크(www.coupang.com), 또는 파트너스 링크(link.coupang.com)를 그대로 붙여넣으세요.'
s = s.replace(old_help, new_help, 1)

old_status = 'GitHub 요청 화면이 열리면 Submit new issue를 누르면 자동 처리됩니다.'
new_status = '링크 형식을 자동으로 인식해 업로드합니다.'
s = s.replace(old_status, new_status, 1)

p.write_text(s, encoding='utf-8')
print('Coupang uploader input updated to textarea.')
