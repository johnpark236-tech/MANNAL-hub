from pathlib import Path
import re

path = Path('index.html')
text = path.read_text(encoding='utf-8')

# Locate the end of the Coupang ads list. New ads are always appended immediately
# before this notice, so deleting from the 11th-last ad start to this marker
# removes exactly the bottom 11 visual ad entries even if an older card has
# slightly malformed closing markup.
marker_re = re.compile(r'\s*</div>\s*<p class=["\']coupang-notice["\']>', re.I)
marker_match = marker_re.search(text)
if not marker_match:
    raise SystemExit('Could not find Coupang ads-list end marker.')

ads_region = text[:marker_match.start()]
start_re = re.compile(
    r'<a\b(?=[^>]*class=["\'][^"\']*\bad-card\b[^"\']*["\'])[^>]*>',
    re.I,
)
starts = list(start_re.finditer(ads_region))
if len(starts) < 11:
    raise SystemExit(f'Expected at least 11 ad cards, found {len(starts)}')

before = len(starts)
cut_start = starts[-11].start()

# Show the 11 card starts that are being removed for auditability.
for i, m in enumerate(starts[-11:], 1):
    tag = m.group(0)
    href = re.search(r'href=["\']([^"\']+)', tag, re.I)
    print(f'Removing bottom ad {i}/11: {(href.group(1) if href else "no-href")}')

# Preserve the actual closing </div> and notice from the marker onward.
closing_start = text.rfind('</div>', 0, marker_match.end())
if closing_start < cut_start:
    raise SystemExit('Could not resolve ads-list closing tag safely.')

new_text = text[:cut_start] + text[closing_start:]

new_marker = marker_re.search(new_text)
if not new_marker:
    raise SystemExit('Ads-list end marker missing after cleanup.')
remaining_starts = list(start_re.finditer(new_text[:new_marker.start()]))
expected = before - 11
if len(remaining_starts) != expected:
    raise SystemExit(f'Unexpected ad count after removal: {len(remaining_starts)} (expected {expected})')

path.write_text(new_text, encoding='utf-8')
print(f'Ad cards before: {before}')
print(f'Ad cards after: {len(remaining_starts)}')
print('Removed exactly the bottom 11 test ads.')
