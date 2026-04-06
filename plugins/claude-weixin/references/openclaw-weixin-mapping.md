# Claude Weixin Mapping

This plugin is intentionally modeled after `openclaw-weixin`, but adapted to the
current Claude marketplace repository format (`skills + scripts`).

## Capability mapping

| openclaw-weixin area | Claude plugin command | Notes |
|---|---|---|
| QR login start | `login-start` | Calls `login/start` and stores `session_key` |
| QR login wait | `login-wait` | Calls `login/wait` and persists returned token |
| `getupdates` | `pull` | Uses and updates `get_updates_buf` |
| `sendmessage` text flow | `send` | Sends a plain text message |
| `sendmessage` advanced flow | `send-rich` | Sends a raw `msg` payload |
| `getconfig` | `get-config` | Can store `typing_ticket` locally |
| `sendtyping` | `typing` | Sends or clears typing status |
| `getuploadurl` | `upload-url` | Only requests upload params, does not upload encrypted media |

## Expected gateway endpoints

The default config assumes:

```text
base_url   = http://127.0.0.1:3000
api_prefix = /v1/weixin
```

Effective endpoints:

```text
POST /v1/weixin/login/start
POST /v1/weixin/login/wait
POST /v1/weixin/getupdates
POST /v1/weixin/sendmessage
POST /v1/weixin/getconfig
POST /v1/weixin/sendtyping
POST /v1/weixin/getuploadurl
```

## Expected headers

```text
Content-Type: application/json
AuthorizationType: ilink_bot_token
Authorization: Bearer <token>
X-WECHAT-UIN: <optional-base64-uin>
```

## Payload examples

### `send`

```json
{
  "msg": {
    "to_user_id": "user@im.wechat",
    "context_token": "ctx-token",
    "item_list": [
      {
        "type": 1,
        "text_item": {
          "text": "hello from Claude"
        }
      }
    ]
  }
}
```

### `send-rich`

The payload file is the raw `msg` object, not the outer request envelope:

```json
{
  "to_user_id": "user@im.wechat",
  "context_token": "ctx-token",
  "item_list": [
    {
      "type": 1,
      "text_item": {
        "text": "hello from a raw payload"
      }
    }
  ]
}
```

### `pull`

```json
{
  "get_updates_buf": ""
}
```

### `typing`

```json
{
  "ilink_user_id": "user@im.wechat",
  "typing_ticket": "base64-ticket",
  "status": 1
}
```

### `upload-url`

The script computes file size and MD5 from a local file and sends them to the
gateway. For now, `filesize` is set equal to the local file size because this
plugin does not implement the OpenClaw AES-encryption upload pipeline yet.

## Design limits

- No direct Weixin protocol implementation
- No QR code rendering in terminal
- No encrypted CDN media upload
- No background gateway daemon inside the plugin itself

Those pieces should live in your custom backend, while this plugin keeps Claude
integration simple and scriptable.
