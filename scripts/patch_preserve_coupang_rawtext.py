from pathlib import Path

py = Path('scripts/add_coupang_ad.py')
s = py.read_text(encoding='utf-8')
old = """    if not product_name:\n        product_name = fetch_partner_product_name(coupang_url)\n\n    if not product_name:\n        product_name = extract_title_from_pasted_text(raw_text)\n\n    if not product_name:\n        product_name = fetch_product_title(coupang_url)\n"""
new = """    if not product_name:\n        product_name = extract_title_from_pasted_text(raw_text)\n\n    if not product_name:\n        product_name = fetch_partner_product_name(coupang_url)\n\n    if not product_name:\n        product_name = fetch_product_title(coupang_url)\n"""
if old not in s:
    raise SystemExit('product-name order target not found')
s = s.replace(old, new, 1)
py.write_text(s, encoding='utf-8')
print('Patched product-name priority.')
