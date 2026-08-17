# 쿠팡 파트너스 광고 자동 등록 지침서

## 목적
사용자가 일반 쿠팡 상품 URL 하나만 전달하면 `johnpark236-tech/MANNAL-hub`의 `main/index.html`에서 기존 쿠팡 광고의 맨 마지막 항목 바로 아래에 새 광고를 추가한다.

## 고정 처리 규칙
1. 입력은 `https://www.coupang.com/...` 형식의 일반 쿠팡 상품 URL을 사용한다.
2. 일반 쿠팡 URL을 그대로 광고 링크로 게시하지 않는다.
3. GitHub Repository Secrets에 등록된 `COUPANG_ACCESS_KEY`, `COUPANG_SECRET_KEY`를 사용하여 쿠팡파트너스 Deeplink API로 변환한다.
4. Access Key와 Secret Key의 실제 값은 소스, HTML, JSON 요청 파일, 커밋 메시지, Actions 로그에 절대로 기록하지 않는다.
5. 변환 결과의 파트너스 URL만 `index.html`에 게시한다.
6. 기존 광고를 삭제하거나 덮어쓰지 않고 `.ads-list`의 맨 마지막 광고 밑에 새 광고를 누적 추가한다.
7. 동일한 파트너스 URL이 이미 `index.html`에 존재하면 중복 추가하지 않는다.
8. 광고 문구가 요청 파일에 지정되어 있으면 해당 문구를 우선 사용한다.
9. 문구가 지정되지 않은 경우 URL의 `q` 검색어를 이용하여 첫 문구를 만들고, 두 번째 문구는 상품 확인 안내 문구로 자동 작성한다.
10. 광고 추가 후 GitHub Actions가 `index.html`을 `main` 브랜치에 커밋하고 GitHub Pages가 기존 설정에 따라 배포한다.

## 보안 규칙
- `COUPANG_ACCESS_KEY`: GitHub Repository Secret으로만 보관한다.
- `COUPANG_SECRET_KEY`: GitHub Repository Secret으로만 보관한다.
- Python에서 키를 `print()` 하지 않는다.
- Authorization 헤더 전체를 로그에 출력하지 않는다.
- 워크플로 권한은 광고 파일을 커밋하는 데 필요한 `contents: write`만 사용한다.
- 키 유출이 의심되면 쿠팡파트너스에서 즉시 키를 재발급하고 GitHub Secret 값을 교체한다.

## 저장소 구성
- `scripts/add_coupang_ad.py`: 쿠팡 Deeplink 변환 및 HTML 광고 추가
- `.github/workflows/add-coupang-ad.yml`: 요청 파일이 추가될 때 자동 실행
- `coupang_requests/*.json`: 한 번의 광고 등록 요청
- `.coupang_last_result.json`: 마지막으로 공개 게시된 파트너스 URL과 문구 확인용. 비밀키는 포함하지 않는다.

## 요청 파일 형식
URL만 사용하는 기본 형식:

```json
{
  "url": "https://www.coupang.com/vp/products/..."
}
```

문구를 직접 지정하는 경우:

```json
{
  "url": "https://www.coupang.com/vp/products/...",
  "line1": "첫 번째 광고 문구",
  "line2": "두 번째 광고 문구"
}
```

## 사용자와의 기본 작업 방식
앞으로 사용자가 쿠팡 상품 URL만 전달하면 다음 절차를 수행한다.

`일반 쿠팡 URL → 요청 파일 추가 → GitHub Actions 실행 → 쿠팡파트너스 Deeplink 생성 → index.html 마지막 광고 아래 추가 → main 커밋 → 반영 확인`

사용자는 Access Key/Secret Key를 채팅에 다시 전달하지 않는다.
