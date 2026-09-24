# KRX 승인 확인 자동화

GitHub Actions가 KRX 유가증권 일별매매정보를 HTTPS로 조회하고 매번 Gmail SMTP로 결과를 보냅니다.
2026-09-22의 실제 종목 데이터가 반환되고 성공 메일 발송까지 완료되면 이 워크플로를 비활성화합니다.
이 검사는 해당 API의 접근만 검증하며 다른 KRX API 전체의 승인을 보장하지 않습니다.

## 설정

기본 브랜치에 워크플로가 있어야 예약이 실행됩니다.
저장소 Settings → Secrets and variables → Actions에서 다음 Repository secrets를 등록하세요.

| 이름 | 값 |
| --- | --- |
| `KRX_API_KEY` | 발급받은 KRX 키 |
| `SMTP_USER` | 메일을 발송할 Gmail 주소 |
| `SMTP_APP_PASSWORD` | 해당 계정의 Google 앱 비밀번호 (일반 로그인 비밀번호 아님) |
| `REPORT_TO` | `najjun6@gmail.com` |

앱 비밀번호는 Google 계정의 2단계 인증이 필요하며 계정 정책에 따라 제공되지 않을 수 있습니다.
https://support.google.com/accounts/answer/185833

Secrets 등록 후 Variables 탭에 `KRX_MONITOR_ENABLED`를 값 `true`로 추가하세요.
이 플래그가 없으면 조회와 메일 발송은 실행되지 않습니다.
Actions → KRX approval monitor → Run workflow로 처음 한 번 수동 실행해 메일 수신까지 확인하세요.
자동 발송에는 이 대화의 Gmail 연결이 아닌 별도 SMTP 인증을 사용합니다.
API 키와 비밀번호는 코드·커밋·이슈에 붙여 넣지 마세요.

## 실행 및 중단

- UTC 00:17, 06:17, 12:17, 18:17 / 한국시간 03:17, 09:17, 15:17, 21:17에 실행합니다.
- GitHub 사정에 따라 실행이 지연되거나 누락될 수 있어 정확한 시각을 보장하지 않습니다.
- 공개 저장소는 60일간 저장소 활동이 없으면 예약이 자동 비활성화될 수 있습니다.
- 실패·빈 데이터이면 결과를 메일로 보내고 다음 실행을 기다립니다.
- 메일 발송이 실패하면 예약을 유지합니다. Actions 실행은 실패로 표시됩니다.
- 정상 조회·메일 발송 후 GitHub API로 자기 워크플로를 중단합니다 (`actions: write` 필요).
- 중단 API가 실패하면 실행이 실패로 표시되고 다음 주기에 성공 메일이 중복될 수 있습니다.
- 수동 중단: Actions에서 Disable workflow. 재개: Enable workflow.
- 정상 상태에서도 수동 실행하면 조회·메일 발송 후 다시 비활성화됩니다.

## 로컬 검증

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

테스트는 네트워크·메일·GitHub 변경을 모의 처리합니다. 실제 발송과 예약 중단은 Secrets 등록 후 GitHub에서 확인해야 합니다.
