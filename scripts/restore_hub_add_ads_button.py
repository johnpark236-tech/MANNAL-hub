from pathlib import Path

path = Path('index.html')
text = path.read_text(encoding='utf-8')

# Restore original browser/header title.
text = text.replace('<title>한국어 교재 추천합니다.</title>', '<title>MANNAL 한국어 학습</title>')
text = text.replace('<h1>한국어 교재 추천합니다.</h1>', '<h1>🚀 MANNAL 한국어 학습</h1>')

# Restore previously comment-hidden learning buttons and uploader.
text = text.replace(
    '<!-- TEMP-HIDDEN LEARNING_BUTTONS: remove these comment markers to restore later.\n',
    ''
).replace('\nEND TEMP-HIDDEN LEARNING_BUTTONS -->', '')

text = text.replace(
    '<!-- TEMP-HIDDEN COUPANG_UPLOADER: remove these comment markers to restore later.\n',
    ''
).replace('\nEND TEMP-HIDDEN COUPANG_UPLOADER -->', '')

# Add CSS once.
css = '''\n    /* ── 광고만 보기 버튼 ── */\n    .ads-only-wrap {\n      margin-top: 14px;\n      text-align: center;\n    }\n    .ads-only-btn {\n      display: inline-flex;\n      align-items: center;\n      justify-content: center;\n      min-width: 180px;\n      padding: 13px 24px;\n      border-radius: 12px;\n      background: linear-gradient(135deg, var(--pink), var(--coral));\n      color: #fff;\n      text-decoration: none;\n      font-weight: 800;\n      font-size: 14px;\n      box-shadow: 0 6px 16px rgba(255,83,118,0.18);\n      transition: transform .2s ease, box-shadow .2s ease;\n    }\n    .ads-only-btn:hover {\n      transform: translateY(-2px);\n      box-shadow: 0 9px 20px rgba(255,83,118,0.25);\n    }\n'''
if '.ads-only-btn {' not in text:
    text = text.replace('\n  </style>', css + '\n  </style>', 1)

# Insert button immediately after Coupang uploader section.
button = '''\n\n    <div class="ads-only-wrap">\n      <a href="ads.html" class="ads-only-btn" aria-label="광고만 보기">📚 광고만 보기</a>\n    </div>'''
if 'class="ads-only-btn"' not in text:
    uploader_start = text.find('<section class="coupang-uploader"')
    if uploader_start < 0:
        raise SystemExit('Coupang uploader section not found after restore.')
    section_end = text.find('</section>', uploader_start)
    if section_end < 0:
        raise SystemExit('Coupang uploader closing section not found.')
    section_end += len('</section>')
    text = text[:section_end] + button + text[section_end:]

# Validation.
required = [
    '<h1>🚀 MANNAL 한국어 학습</h1>',
    '<div class="cards-grid">',
    '<section class="coupang-uploader"',
    'href="ads.html"',
]
for item in required:
    if item not in text:
        raise SystemExit(f'Missing expected content after patch: {item}')

path.write_text(text, encoding='utf-8')
print('Restored original HUB heading.')
print('Restored learning cards.')
print('Restored Coupang uploader.')
print('Added ads-only button linking to ads.html.')
