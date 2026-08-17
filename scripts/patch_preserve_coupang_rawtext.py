from pathlib import Path

wf = Path('.github/workflows/add-coupang-ad.yml')
s = wf.read_text(encoding='utf-8')
old = """          with open('/tmp/coupang_request.json', 'w', encoding='utf-8') as f:\n              json.dump({'url': url}, f, ensure_ascii=False)\n"""
new = """          with open('/tmp/coupang_request.json', 'w', encoding='utf-8') as f:\n              json.dump({'url': url, 'rawText': body}, f, ensure_ascii=False)\n"""
if old not in s:
    raise SystemExit('workflow target not found')
s = s.replace(old, new, 1)
wf.write_text(s, encoding='utf-8')

py = Path('scripts/add_coupang_ad.py')
s = py.read_text(encoding='utf-8')
old = """    if not product_name:\n        product_name = fetch_partner_product_name(coupang_url)\n\n    if not product_name:\n        product_name = extract_title_from_pasted_text(raw_text)\n\n    if not product_name:\n        product_name = fetch_product_title(coupang_url)\n"""
new = """    if not product_name:\n        product_name = extract_title_from_pasted_text(raw_text)\n\n    if not product_name:\n        product_name = fetch_partner_product_name(coupang_url)\n\n    if not product_name:\n        product_name = fetch_product_title(coupang_url)\n"""
if old not in s:
    raise SystemExit('product-name order target not found')
s = s.replace(old, new, 1)
py.write_text(s, encoding='utf-8')
print('Patched rawText preservation and product-name priority.')
