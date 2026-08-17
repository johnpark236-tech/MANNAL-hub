from pathlib import Path
import json

index_path = Path('index.html')
text = index_path.read_text(encoding='utf-8')
affiliate = 'https://link.coupang.com/a/ginyL3iVa0'
product = '맛꾼 파손보상 촉촉쫄깃 구운계란 대란 훈제란'

anchor_pos = text.find(f'href="{affiliate}"')
if anchor_pos < 0:
    raise SystemExit('Target affiliate URL not found in index.html')

start = text.rfind('      <a ', 0, anchor_pos)
end = text.find('      </a>', anchor_pos)
if start < 0 or end < 0:
    raise SystemExit('Target ad card boundaries not found')
end += len('      </a>')

new_card = f'''      <a href="{affiliate}" target="_blank" referrerpolicy="unsafe-url" class="ad-card">\n        <div class="ad-icon ad-icon-orange"><i class="fa-solid fa-utensils"></i></div>\n        <p><b>{product}</b></p>\n        <span class="ad-cta">보러가기 →</span>\n      </a>'''
text = text[:start] + new_card + text[end:]
index_path.write_text(text, encoding='utf-8')

Path('.coupang_last_result.json').write_text(json.dumps({
    'affiliateUrl': affiliate,
    'productName': product,
    'category': '식품',
    'icon': 'fa-utensils',
    'iconColorClass': 'ad-icon-orange'
}, ensure_ascii=False, indent=2), encoding='utf-8')
print('Current egg ad updated.')
