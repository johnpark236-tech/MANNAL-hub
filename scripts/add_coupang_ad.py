import os
import sys
import json
import hmac
import hashlib
import datetime
import html
import re
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path

API_HOST = "https://api-gateway.coupang.com"
DEEPLINK_PATH = "/v2/providers/affiliate_open_api/apis/openapi/v1/deeplink"


def make_auth(access_key: str, secret_key: str) -> str:
    now = datetime.datetime.now(datetime.timezone.utc)
    signed_date = now.strftime("%y%m%dT%H%M%SZ")
    message = signed_date + "POST" + DEEPLINK_PATH
    signature = hmac.new(secret_key.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()
    return (
        "CEA algorithm=HmacSHA256, "
        f"access-key={access_key}, signed-date={signed_date}, signature={signature}"
    )


def extract_first_url(raw_text: str) -> str:
    raw_text = (raw_text or "").strip()
    pos = raw_text.find("https://")
    if pos < 0:
        return ""
    candidate = raw_text[pos:].split()[0].strip()
    return candidate.rstrip('.,)\]}>"\'')


def convert_to_deeplink(coupang_url: str) -> str:
    # Already a Coupang Partners short link: publish it directly.
    if coupang_url.startswith("https://link.coupang.com/"):
        return coupang_url

    access_key = os.environ.get("COUPANG_ACCESS_KEY", "").strip()
    secret_key = os.environ.get("COUPANG_SECRET_KEY", "").strip()
    if not access_key or not secret_key:
        raise RuntimeError("Coupang Partners secrets are not configured.")

    body = json.dumps({"coupangUrls": [coupang_url]}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        API_HOST + DEEPLINK_PATH,
        data=body,
        method="POST",
        headers={
            "Authorization": make_auth(access_key, secret_key),
            "Content-Type": "application/json;charset=UTF-8",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Coupang Deeplink API failed: HTTP {e.code}: {body_text[:500]}") from None

    if str(payload.get("rCode")) != "0" or not payload.get("data"):
        raise RuntimeError(f"Coupang Deeplink API returned an error: {payload.get('rMessage', 'unknown error')}")

    item = payload["data"][0]
    return item.get("shortenUrl") or item.get("landingUrl") or ""


def clean_product_title(value: str) -> str:
    value = html.unescape(value or "")
    value = re.sub(r"\s+", " ", value).strip()
    for suffix in (
        " | 쿠팡!",
        " - 쿠팡!",
        " : 쿠팡!",
        " | Coupang",
        " - Coupang",
    ):
        if value.endswith(suffix):
            value = value[:-len(suffix)].strip()
    return value


def fetch_product_title(coupang_url: str) -> str:
    """Best-effort product-title lookup. Short links are followed automatically."""
    req = urllib.request.Request(
        coupang_url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            page = resp.read(2_000_000).decode("utf-8", errors="replace")
    except Exception as exc:
        print(f"Product title lookup skipped: {exc}")
        return ""

    patterns = [
        r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:title["\']',
        r'<meta[^>]+name=["\']twitter:title["\'][^>]+content=["\']([^"\']+)["\']',
        r'<title[^>]*>(.*?)</title>',
    ]
    for pattern in patterns:
        match = re.search(pattern, page, re.I | re.S)
        if match:
            title = clean_product_title(match.group(1))
            if title and title.lower() not in {"coupang", "쿠팡!"}:
                return title

    # Coupang pages sometimes embed the product name in JSON instead of meta tags.
    for pattern in (
        r'"productName"\s*:\s*"((?:\\.|[^"\\])+)"',
        r'"title"\s*:\s*"((?:\\.|[^"\\])+)"',
    ):
        match = re.search(pattern, page, re.I)
        if match:
            try:
                decoded = json.loads('"' + match.group(1) + '"')
            except Exception:
                decoded = match.group(1)
            title = clean_product_title(decoded)
            if title and len(title) >= 3:
                return title

    return ""


def derive_copy(coupang_url: str, request_data: dict) -> tuple[str, str]:
    line1 = (request_data.get("line1") or "").strip()
    line2 = (request_data.get("line2") or "").strip()
    if line1 and line2:
        return line1, line2

    # Prefer an explicitly supplied product name if a future request includes one.
    product_name = (
        request_data.get("productName")
        or request_data.get("product_name")
        or request_data.get("title")
        or ""
    ).strip()

    # Otherwise obtain the real Coupang product title from the product/short-link page.
    if not product_name:
        product_name = fetch_product_title(coupang_url)

    # Last-resort fallback: use the q= search keyword when present.
    if not product_name:
        parsed = urllib.parse.urlparse(coupang_url)
        q = urllib.parse.parse_qs(parsed.query).get("q", [""])[0].strip()
        product_name = urllib.parse.unquote_plus(q) if q else "쿠팡 추천 상품"

    return line1 or "쿠팡을 추천 합니다! 🛒", line2 or product_name


def append_ad(index_path: Path, affiliate_url: str, line1: str, line2: str) -> None:
    text = index_path.read_text(encoding="utf-8")
    if affiliate_url in text:
        print("Affiliate URL already exists; no duplicate ad added.")
        return

    marker = '    </div>\n\n    <p class="coupang-notice">'
    if marker not in text:
        raise RuntimeError("Could not find the end of the Coupang ads list in index.html.")

    ad = f'''      <a href="{html.escape(affiliate_url, quote=True)}" target="_blank" referrerpolicy="unsafe-url" class="ad-card">\n        <div class="ad-icon ad-icon-orange"><i class="fa-solid fa-drumstick-bite"></i></div>\n        <p>{html.escape(line1)}<br>\n           <b>{html.escape(line2)}</b></p>\n        <span class="ad-cta">보러가기 →</span>\n      </a>\n\n'''
    text = text.replace(marker, ad + marker, 1)
    index_path.write_text(text, encoding="utf-8")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: add_coupang_ad.py <request.json>")

    request_path = Path(sys.argv[1])
    data = json.loads(request_path.read_text(encoding="utf-8"))
    raw_url = data.get("url") or ""
    coupang_url = extract_first_url(raw_url)

    if not (
        coupang_url.startswith("https://www.coupang.com/")
        or coupang_url.startswith("https://link.coupang.com/")
    ):
        raise RuntimeError("Request must contain a valid Coupang URL beginning with https://.")

    affiliate_url = convert_to_deeplink(coupang_url)
    if not affiliate_url:
        raise RuntimeError("Coupang API returned no affiliate URL.")

    line1, line2 = derive_copy(coupang_url, data)
    append_ad(Path("index.html"), affiliate_url, line1, line2)

    Path(".coupang_last_result.json").write_text(
        json.dumps({"affiliateUrl": affiliate_url, "line1": line1, "line2": line2}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Coupang affiliate ad prepared successfully: {line2}")


if __name__ == "__main__":
    main()
