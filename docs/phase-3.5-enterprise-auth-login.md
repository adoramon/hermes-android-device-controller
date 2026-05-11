# Phase 3.5: Enterprise Auth Login

Phase 3.5 adds authorized login support for the enterprise Android app
configured locally.

## .env Setup

Create a local `.env` file from `.env.example`:

```bash
cp .env.example .env
```

Then fill:

```text
ENTERPRISE_APP_PACKAGE=
ENTERPRISE_APP_USERNAME=
ENTERPRISE_APP_PASSWORD=
```

Do not commit `.env`. It is ignored by Git.

## Login Flow

Run from the repo root:

```bash
PYTHONPATH=src python3 scripts/enterprise_login.py
```

The script:

1. Opens the enterprise app.
2. Detects the login page from UIAutomator XML.
3. Finds the username field, password field, and `登录` button.
4. Enters credentials from local environment configuration.
5. Taps `登录`.
6. Waits for page change.
7. Stops if an SMS verification page appears.

Passwords are not printed in script output.

Password entry uses character-by-character ADB input. If a character input command fails, it falls back to clipboard paste and clears the clipboard immediately. This avoids cases where a full-string `adb input text` call drops the last character or taps login before the input method commits the final character.

If the app asks the user to modify or update the password after login, Hermes may only tap a safe postpone option such as `忽略`, `暂不修改`, `暂时不修改`, `稍后`, `以后再说`, `跳过`, or `取消`. Hermes must not enter a password-change workflow.

## SMS Verification

If the app asks for SMS verification, Hermes should ask the user:

```text
已进入短信验证码验证，请回复：企信验证码：xxxxxx
```

The user must reply through WeChat in this exact format:

```text
企信验证码：123456
```

Hermes can then call:

```bash
PYTHONPATH=src python3 scripts/submit_enterprise_sms_code.py 123456
```

The code must be 4-8 digits. Hermes does not read SMS messages and does not bypass SMS verification.

## Safety Boundary

Allowed:

- Open the authorized enterprise app.
- Fill username/password from local `.env` or environment variables.
- Ask the user for SMS verification through WeChat.
- Submit only the user-provided SMS code.

Not allowed:

- Do not write credentials into code, logs, README, or tests.
- Do not commit `.env`.
- Do not read SMS messages.
- Do not bypass SMS verification.
- Do not enter password-change workflows; only postpone/ignore when the app offers that option.
- Do not perform attendance/check-in submission.
- Do not perform approval pass/submission.
- Do not implement anti-detection behavior, hidden Mock Location, Root, or Hook.

## Troubleshooting

If credentials are missing, check:

```bash
test -f .env
grep -n '^ENTERPRISE_APP_' .env
```

If the login page is not detected, run the read-only probe:

```bash
PYTHONPATH=src python3 scripts/probe_enterprise_app.py
```

If SMS submission fails, confirm the current page is the SMS verification page and that the WeChat text matches:

```text
企信验证码：xxxxxx
```

If no confirm/login/submit button is found after entering the code, the tool reports `need_manual_confirm=true`; the user must confirm manually.
