"""Check KRX approval, email the result, then disable the workflow on success."""

import json
import os
import smtplib
import ssl
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def check_krx(api_key):
    # A known trading day avoids confusing holidays with missing approval.
    url = "https://data-dbg.krx.co.kr/svc/apis/sto/stk_bydd_trd?basDd=20260922"
    request = Request(url, headers={"AUTH_KEY": api_key})
    try:
        with build_opener(NoRedirect).open(request, timeout=30) as response:
            data = json.load(response)
    except HTTPError as error:
        return False, "KRX HTTP {} (인증/승인 원인은 별도 확인 필요)".format(error.code)
    except (URLError, TimeoutError, OSError):
        return False, "KRX 연결 실패 또는 시간 초과"
    except (ValueError, UnicodeError):
        return False, "KRX 응답을 JSON으로 해석할 수 없음"
    rows = data.get("OutBlock_1") if isinstance(data, dict) else None
    if not isinstance(rows, list) or not rows:
        return False, "KRX 응답에 일별매매 데이터가 없음"
    if not all(isinstance(row, dict) and row.get("ISU_CD") for row in rows):
        return False, "KRX 일별매매 데이터 형식이 예상과 다름"
    return True, "2026-09-22 유가증권 일별매매정보 {}건 조회 성공".format(len(rows))


def send_result(success, detail):
    message = EmailMessage()
    message["From"] = os.environ["SMTP_USER"]
    message["To"] = os.environ["REPORT_TO"]
    message["Subject"] = "[KRX 확인] " + ("정상 조회 성공" if success else "아직 정상 조회되지 않음")
    checked_at = datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")
    next_step = "성공 메일 발송 후 자동 확인 중단을 요청합니다." if success else "6시간 주기로 다시 확인합니다."
    message.set_content("확인 시각: {}\n결과: {}\n{}\n".format(checked_at, detail, next_step))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30, context=ssl.create_default_context()) as smtp:
        smtp.login(os.environ["SMTP_USER"], os.environ["SMTP_APP_PASSWORD"])
        refused = smtp.send_message(message)
        if refused:
            raise RuntimeError("메일 수신자가 거부됨")


def disable_workflow():
    url = "https://api.github.com/repos/{}/actions/workflows/krx-monitor.yml/disable".format(
        os.environ["GITHUB_REPOSITORY"]
    )
    request = Request(url, method="PUT", headers={
        "Authorization": "Bearer " + os.environ["GITHUB_TOKEN"],
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    with build_opener(NoRedirect).open(request, timeout=30) as response:
        if response.status != 204:
            raise RuntimeError("예약 중단 요청 실패")


def main():
    required = ("KRX_API_KEY", "SMTP_USER", "SMTP_APP_PASSWORD", "REPORT_TO", "GITHUB_TOKEN", "GITHUB_REPOSITORY")
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise RuntimeError("필수 설정 누락: " + ", ".join(missing))
    success, detail = check_krx(os.environ["KRX_API_KEY"])
    print(detail)
    send_result(success, detail)
    print("결과 메일 발송 완료")
    if success:
        disable_workflow()
        print("예약 워크플로 비활성화 완료")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        # External error strings may contain credentials or email addresses.
        print("실행 실패: {}. Secrets, 메일 인증 및 Actions 권한을 확인하세요.".format(type(error).__name__))
        raise SystemExit(1)
