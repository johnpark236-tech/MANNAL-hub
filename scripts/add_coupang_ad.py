import os
import sys
import json
import hmac
import hashlib
import datetime
import html
import urllib.request
import urllib.parse
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


def derive_copy(coupang_url: str, request_data: dict) -> tuple[str, str]:
    line1 = (request_data.get("line1") or "").strip()
    line2 = (request_data.get("line2") or "").strip()
    if line1 and line2:
        return line1, line2

    parsed = urllib.parse.urlparse(coupang_url)
    q = urllib.parse.parse_qs(parsed.query).get("q", [""])[0].strip()
    keyword = urllib.parse.unquote_plus(q) if q else "쿠팡 추천 상품"
    return line1 or f"{keyword} 추천 상품", line2 or "쿠팡에서 상품 정보를 확인해보세요!"


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
    print("Coupang affiliate ad prepared successfully.")


if __name__ == "__main__":
    main()
