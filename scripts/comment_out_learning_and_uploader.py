from pathlib import Path
import re

path = Path('index.html')
text = path.read_text(encoding='utf-8')

# 1) Update visible/header/browser title copy.
text = text.replace('<title>MANNAL 한국어 학습</title>', '<title>한국어 교재 추천합니다.</title>')
text = text.replace('<h1>🚀 MANNAL 한국어 학습</h1>', '<h1>한국어 교재 추천합니다.</h1>')


def wrap_matching_block(source: str, start_literal: str, tag_name: str, label: str) -> str:
    start = source.find(start_literal)
    if start < 0:
        if f'TEMP-HIDDEN {label}' in source:
            return source
        raise SystemExit(f'Could not find start marker for {label}')

    tag_re = re.compile(rf'</?{tag_name}\b[^>]*>', re.I)
    depth = 0
    end = None
    for m in tag_re.finditer(source, start):
        token = m.group(0)
        if token.startswith('</'):
            depth -= 1
            if depth == 0:
                end = m.end()
                break
        else:
            depth += 1
    if end is None:
        raise SystemExit(f'Could not find matching closing {tag_name} for {label}')

    block = source[start:end]
    wrapped = (
        f'<!-- TEMP-HIDDEN {label}: remove these comment markers to restore later.\n'
        f'{block}\n'
        f'END TEMP-HIDDEN {label} -->'
    )
    return source[:start] + wrapped + source[end:]


# 2) Hide the three Korean-learning cards while preserving their HTML for later reuse.
text = wrap_matching_block(text, '<div class="cards-grid">', 'div', 'LEARNING_BUTTONS')

# 3) Hide the Coupang uploader UI while preserving it for later reuse.
text = wrap_matching_block(text, '<section class="coupang-uploader"', 'section', 'COUPANG_UPLOADER')

# 4) If uploader JavaScript expects the now-commented DOM nodes, guard its setup.
# Existing code commonly binds through coupangUploadBtn. Convert direct addEventListener use to optional chaining.
text = text.replace(
    "document.getElementById('coupangUploadBtn').addEventListener(",
    "document.getElementById('coupangUploadBtn')?.addEventListener("
)
text = text.replace(
    'document.getElementById("coupangUploadBtn").addEventListener(',
    'document.getElementById("coupangUploadBtn")?.addEventListener('
)

path.write_text(text, encoding='utf-8')
print('Updated title/header text.')
print('Commented out learning buttons block.')
print('Commented out Coupang uploader block.')
