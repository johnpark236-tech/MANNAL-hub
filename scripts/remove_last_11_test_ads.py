from pathlib import Path
import re

path = Path('index.html')
text = path.read_text(encoding='utf-8')

pattern = re.compile(
    r'\n\s*<a\b(?=[^>]*class=["\'][^"\']*\bad-card\b[^"\']*["\'])[^>]*>.*?</a>\s*',
    re.I | re.S,
)
matches = list(pattern.finditer(text))

if len(matches) < 11:
    raise SystemExit(f'Expected at least 11 ad cards, found {len(matches)}')

remove = matches[-11:]
print(f'Ad cards before: {len(matches)}')
for i, m in enumerate(remove, 1):
    block = m.group(0)
    href = re.search(r'href=["\']([^"\']+)', block, re.I)
    plain = re.sub(r'<[^>]+>', ' ', block)
    plain = re.sub(r'\s+', ' ', plain).strip()
    print(f'Removing {i}/11: {(href.group(1) if href else "no-href")} | {plain[:120]}')

for m in reversed(remove):
    text = text[:m.start()] + '\n' + text[m.end():]

remaining = list(pattern.finditer(text))
if len(remaining) != len(matches) - 11:
    raise SystemExit(f'Unexpected ad count after removal: {len(remaining)}')

path.write_text(text, encoding='utf-8')
print(f'Ad cards after: {len(remaining)}')
