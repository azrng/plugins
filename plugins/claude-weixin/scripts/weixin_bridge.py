#!/usr/bin/env python3
"""Claude Weixin bridge script modeled after openclaw-weixin."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any
from urllib import error, parse, request


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PLUGIN_ROOT / "data"
CONFIG_PATH = DATA_DIR / "weixin_bridge_config.json"

DEFAULT_CONFIG = {
    "base_url": "http://127.0.0.1:3000",
    "api_prefix": "/v1/weixin",
    "auth_type": "ilink_bot_token",
    "token": "",
    "x_wechat_uin": "",
    "account_id": "",
    "bot_type": "bot",
    "last_session_key": "",
    "last_sync_buffer": "",
    "last_typing_ticket": "",
}


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return dict(DEFAULT_CONFIG)
    with CONFIG_PATH.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    merged = dict(DEFAULT_CONFIG)
    merged.update(data)
    return merged


def save_config(config: dict[str, Any]) -> None:
    ensure_data_dir()
    with CONFIG_PATH.open("w", encoding="utf-8") as handle:
        json.dump(config, handle, ensure_ascii=False, indent=2)


def output(command: str, response: Any, *, request_meta: dict[str, Any] | None = None) -> None:
    payload = {
        "status": "success",
        "command": command,
        "request": request_meta or {},
        "response": response,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def fail(command: str, message: str, *, details: Any = None, exit_code: int = 1) -> None:
    payload = {
        "status": "error",
        "command": command,
        "message": message,
    }
    if details is not None:
        payload["details"] = details
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    raise SystemExit(exit_code)


def normalize_prefix(value: str) -> str:
    if not value:
        return ""
    prefix = value.strip()
    if not prefix.startswith("/"):
        prefix = "/" + prefix
    return prefix.rstrip("/")


def build_url(config: dict[str, Any], endpoint: str) -> str:
    base_url = str(config["base_url"]).rstrip("/")
    api_prefix = normalize_prefix(str(config.get("api_prefix", "")))
    endpoint = endpoint.lstrip("/")
    path = f"{api_prefix}/{endpoint}" if api_prefix else f"/{endpoint}"
    return parse.urljoin(base_url + "/", path.lstrip("/"))


def build_headers(config: dict[str, Any]) -> dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "AuthorizationType": str(config.get("auth_type") or DEFAULT_CONFIG["auth_type"]),
    }
    token = str(config.get("token") or "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    x_wechat_uin = str(config.get("x_wechat_uin") or "").strip()
    if x_wechat_uin:
        headers["X-WECHAT-UIN"] = x_wechat_uin
    return headers


def post_json(config: dict[str, Any], endpoint: str, body: dict[str, Any]) -> tuple[Any, dict[str, Any]]:
    url = build_url(config, endpoint)
    headers = build_headers(config)
    req = request.Request(
        url=url,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=60) as response:
            raw = response.read().decode("utf-8")
    except error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        fail(
            endpoint,
            f"HTTP {exc.code} while calling gateway",
            details={"url": url, "body": raw},
            exit_code=exc.code if isinstance(exc.code, int) else 1,
        )
    except error.URLError as exc:
        fail(endpoint, "Unable to reach gateway", details={"url": url, "reason": str(exc.reason)})
    try:
        parsed_body = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        parsed_body = {"raw": raw}
    return parsed_body, {"url": url, "headers": headers, "body": body}


def apply_config_updates(config: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    updated = dict(config)
    for key in ("base_url", "api_prefix", "auth_type", "token", "x_wechat_uin", "account_id", "bot_type"):
        value = getattr(args, key, None)
        if value is not None:
            updated[key] = value
    return updated


def first_present(data: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in data and data[key] not in (None, ""):
            return data[key]
    return None


def compute_file_meta(path_value: str) -> tuple[Path, int, str]:
    file_path = Path(path_value).expanduser().resolve()
    if not file_path.exists() or not file_path.is_file():
        fail("upload-url", f"File does not exist: {file_path}")
    hasher = hashlib.md5()
    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return file_path, file_path.stat().st_size, hasher.hexdigest()


def command_init(args: argparse.Namespace) -> None:
    config = load_config()
    if args.force:
        config = dict(DEFAULT_CONFIG)
    config = apply_config_updates(config, args)
    save_config(config)
    output("init", config, request_meta={"config_path": str(CONFIG_PATH)})


def command_show_config(_: argparse.Namespace) -> None:
    output("show-config", load_config(), request_meta={"config_path": str(CONFIG_PATH)})


def command_login_start(args: argparse.Namespace) -> None:
    config = apply_config_updates(load_config(), args)
    account_id = args.account_id or config.get("account_id") or ""
    body = {
        "account_id": account_id,
        "bot_type": args.bot_type or config.get("bot_type") or "bot",
        "force": bool(args.force_login),
    }
    if args.timeout_ms is not None:
        body["timeout_ms"] = args.timeout_ms
    response, request_meta = post_json(config, "login/start", body)
    session_key = first_present(response, "session_key", "sessionKey")
    qr_data_url = first_present(response, "qr_data_url", "qrcode_url", "qrDataUrl", "qrcodeUrl")
    if session_key:
        config["last_session_key"] = session_key
    if account_id:
        config["account_id"] = account_id
    save_config(config)
    output(
        "login-start",
        {
            **response,
            "session_key": session_key,
            "qr_data_url": qr_data_url,
        },
        request_meta=request_meta,
    )


def command_login_wait(args: argparse.Namespace) -> None:
    config = apply_config_updates(load_config(), args)
    session_key = args.session_key or config.get("last_session_key") or ""
    if not session_key:
        fail("login-wait", "Missing session key. Run login-start first or pass --session-key.")
    body = {"session_key": session_key}
    if args.timeout_ms is not None:
        body["timeout_ms"] = args.timeout_ms
    response, request_meta = post_json(config, "login/wait", body)
    token = first_present(response, "bot_token", "botToken", "token")
    account_id = first_present(response, "account_id", "accountId")
    connected = bool(first_present(response, "connected", "success"))
    if token:
        config["token"] = token
    if account_id:
        config["account_id"] = account_id
    save_config(config)
    output(
        "login-wait",
        {
            **response,
            "connected": connected,
            "account_id": account_id,
            "token_saved": bool(token),
        },
        request_meta=request_meta,
    )


def command_pull(args: argparse.Namespace) -> None:
    config = apply_config_updates(load_config(), args)
    sync_buffer = args.sync_buffer
    if sync_buffer is None:
        sync_buffer = str(config.get("last_sync_buffer") or "")
    body = {"get_updates_buf": sync_buffer}
    response, request_meta = post_json(config, "getupdates", body)
    new_buffer = first_present(response, "get_updates_buf", "getUpdatesBuf")
    if new_buffer is not None:
        config["last_sync_buffer"] = new_buffer
        save_config(config)
    output(
        "pull",
        {
            **response,
            "saved_sync_buffer": new_buffer,
        },
        request_meta=request_meta,
    )


def command_send(args: argparse.Namespace) -> None:
    config = apply_config_updates(load_config(), args)
    item_list: list[dict[str, Any]] = [
        {
            "type": 1,
            "text_item": {
                "text": args.text,
            },
        }
    ]
    msg = {
        "to_user_id": args.to,
        "item_list": item_list,
    }
    if args.context_token:
        msg["context_token"] = args.context_token
    response, request_meta = post_json(config, "sendmessage", {"msg": msg})
    output("send", response, request_meta=request_meta)


def command_send_rich(args: argparse.Namespace) -> None:
    config = apply_config_updates(load_config(), args)
    if args.payload_file:
        payload_text = Path(args.payload_file).read_text(encoding="utf-8")
    else:
        payload_text = args.payload_json
    if not payload_text:
        fail("send-rich", "Provide --payload-file or --payload-json.")
    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError as exc:
        fail("send-rich", f"Invalid JSON payload: {exc}")
    response, request_meta = post_json(config, "sendmessage", {"msg": payload})
    output("send-rich", response, request_meta=request_meta)


def command_get_config(args: argparse.Namespace) -> None:
    config = apply_config_updates(load_config(), args)
    body = {"ilink_user_id": args.user_id}
    if args.context_token:
        body["context_token"] = args.context_token
    response, request_meta = post_json(config, "getconfig", body)
    typing_ticket = first_present(response, "typing_ticket", "typingTicket")
    if typing_ticket:
        config["last_typing_ticket"] = typing_ticket
        save_config(config)
    output("get-config", response, request_meta=request_meta)


def command_typing(args: argparse.Namespace) -> None:
    config = apply_config_updates(load_config(), args)
    typing_ticket = args.typing_ticket or config.get("last_typing_ticket") or ""
    if not typing_ticket:
        fail("typing", "Missing typing ticket. Run get-config first or pass --typing-ticket.")
    body = {
        "ilink_user_id": args.user_id,
        "typing_ticket": typing_ticket,
        "status": args.status,
    }
    response, request_meta = post_json(config, "sendtyping", body)
    output("typing", response, request_meta=request_meta)


def command_upload_url(args: argparse.Namespace) -> None:
    config = apply_config_updates(load_config(), args)
    file_path, raw_size, raw_md5 = compute_file_meta(args.file)
    thumb_payload = {}
    if args.thumb_file:
        _, thumb_raw_size, thumb_raw_md5 = compute_file_meta(args.thumb_file)
        thumb_payload = {
            "thumb_rawsize": thumb_raw_size,
            "thumb_rawfilemd5": thumb_raw_md5,
            "thumb_filesize": thumb_raw_size,
        }
    media_type_map = {"image": 1, "video": 2, "file": 3}
    body = {
        "filekey": args.filekey or file_path.name,
        "media_type": media_type_map[args.media_type],
        "to_user_id": args.to,
        "rawsize": raw_size,
        "rawfilemd5": raw_md5,
        "filesize": raw_size,
        **thumb_payload,
    }
    response, request_meta = post_json(config, "getuploadurl", body)
    output("upload-url", response, request_meta=request_meta)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Claude Weixin bridge plugin helper.")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--base-url")
    common.add_argument("--api-prefix")
    common.add_argument("--auth-type")
    common.add_argument("--token")
    common.add_argument("--x-wechat-uin", dest="x_wechat_uin")
    common.add_argument("--account-id", dest="account_id")
    common.add_argument("--bot-type", dest="bot_type")

    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", parents=[common], help="Create or update local config.")
    init_parser.add_argument("--force", action="store_true", help="Reset config to defaults before applying overrides.")
    init_parser.set_defaults(func=command_init)

    show_parser = subparsers.add_parser("show-config", help="Show current local config.")
    show_parser.set_defaults(func=command_show_config)

    login_start = subparsers.add_parser("login-start", parents=[common], help="Start QR login flow.")
    login_start.add_argument("--force-login", action="store_true", help="Tell the gateway to ignore previous sessions.")
    login_start.add_argument("--timeout-ms", type=int)
    login_start.set_defaults(func=command_login_start)

    login_wait = subparsers.add_parser("login-wait", parents=[common], help="Wait for QR login completion.")
    login_wait.add_argument("--session-key")
    login_wait.add_argument("--timeout-ms", type=int)
    login_wait.set_defaults(func=command_login_wait)

    pull_parser = subparsers.add_parser("pull", parents=[common], help="Call getupdates and persist sync buffer.")
    pull_parser.add_argument("--sync-buffer")
    pull_parser.set_defaults(func=command_pull)

    send_parser = subparsers.add_parser("send", parents=[common], help="Send a plain text message.")
    send_parser.add_argument("--to", required=True)
    send_parser.add_argument("--text", required=True)
    send_parser.add_argument("--context-token")
    send_parser.set_defaults(func=command_send)

    send_rich = subparsers.add_parser("send-rich", parents=[common], help="Send a raw msg payload.")
    send_rich.add_argument("--payload-file")
    send_rich.add_argument("--payload-json")
    send_rich.set_defaults(func=command_send_rich)

    get_config = subparsers.add_parser("get-config", parents=[common], help="Fetch account config and typing ticket.")
    get_config.add_argument("--user-id", required=True)
    get_config.add_argument("--context-token")
    get_config.set_defaults(func=command_get_config)

    typing_parser = subparsers.add_parser("typing", parents=[common], help="Send typing status.")
    typing_parser.add_argument("--user-id", required=True)
    typing_parser.add_argument("--typing-ticket")
    typing_parser.add_argument("--status", type=int, choices=(1, 2), required=True)
    typing_parser.set_defaults(func=command_typing)

    upload_parser = subparsers.add_parser("upload-url", parents=[common], help="Request upload parameters for a file.")
    upload_parser.add_argument("--file", required=True)
    upload_parser.add_argument("--thumb-file")
    upload_parser.add_argument("--filekey")
    upload_parser.add_argument("--to", required=True)
    upload_parser.add_argument("--media-type", choices=("image", "video", "file"), required=True)
    upload_parser.set_defaults(func=command_upload_url)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        fail("runtime", "Interrupted by user", exit_code=130)
