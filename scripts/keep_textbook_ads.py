from pathlib import Path
import re

path = Path('index.html')
text = path.read_text(encoding='utf-8')

list_start_match = re.search(r'<div class=["\']ads-list["\']>', text, re.I)
notice_match = re.search(r'\s*</div>\s*<p class=["\']coupang-notice["\']>', text, re.I)
if not list_start_match or not notice_match or notice_match.start() <= list_start_match.end():
    raise SystemExit('Could not locate Coupang ads list safely.')

region_start = list_start_match.end()
region_end = text.rfind('</div>', region_start, notice_match.end())
if region_end < region_start:
    raise SystemExit('Could not locate ads-list closing tag.')

region = text[region_start:region_end]
start_re = re.compile(r'<a\b(?=[^>]*class=["\'][^"\']*\bad-card\b[^"\']*["\'])[^>]*>', re.I)
starts = list(start_re.finditer(region))
if not starts:
    raise SystemExit('No ad cards found.')

keywords = ('한국어', 'TOPIK', 'Student Book', 'Workbook', '교재', '문법')
kept = []
removed = []

for i, m in enumerate(starts):
    end = starts[i + 1].start() if i + 1 < len(starts) else len(region)
    chunk = region[m.start():end]
    href_m = re.search(r'href=["\']([^"\']+)', chunk, re.I)
    href = href_m.group(1) if href_m else 'no-href'
    plain = re.sub(r'<[^>]+>', ' ', chunk)
    plain = re.sub(r'\s+', ' ', plain).strip()
    if any(k.lower() in plain.lower() for k in keywords):
        close = chunk.find('</a>')
        if close < 0:
            raise SystemExit(f'Kept textbook card has no closing </a>: {href}')
        clean = chunk[:close + 4].strip()
        kept.append(clean)
        print(f'KEEP: {href} | {plain[:120]}')
    else:
        removed.append((href, plain[:120]))
        print(f'REMOVE: {href} | {plain[:120]}')

if not kept:
    raise SystemExit('Refusing to remove all ads: no textbook ads detected.')

new_region = '\n\n' + '\n\n'.join('      ' + card.replace('\n', '\n      ') for card in kept) + '\n\n    '
new_text = text[:region_start] + new_region + text[region_end:]
path.write_text(new_text, encoding='utf-8')

print(f'Ads before: {len(starts)}')
print(f'Textbook ads kept: {len(kept)}')
print(f'Non-textbook ads removed: {len(removed)}')
