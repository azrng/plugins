# Claude Weixin

`claude-weixin` 是一个参考 `openclaw-weixin` 设计思路实现的 Claude 微信插件骨架。

它本身不直接实现微信协议，而是通过本地脚本把 Claude 侧操作转成 HTTP JSON 请求，转发给你自己的微信网关服务。

## 目录结构

```text
claude-weixin/
|-- .claude-plugin/
|   `-- plugin.json
|-- data/
|   `-- weixin_bridge_config.json
|-- references/
|   `-- openclaw-weixin-mapping.md
|-- scripts/
|   `-- weixin_bridge.py
|-- skills/
|   `-- SKILL.md
`-- README.md
```

## 适用场景

- 想模仿 `openclaw-weixin` 给 Claude 增加微信接入能力
- 已经有自己的微信后端网关，想快速接入 Claude
- 想先做本地联调，再逐步补全扫码登录、轮询和发消息能力

## 当前能力

- 初始化本地配置
- 发起扫码登录
- 等待扫码登录完成
- 长轮询拉取消息
- 发送文本消息
- 发送完整结构消息
- 获取配置和 typing ticket
- 发送 typing 状态
- 申请上传参数

## 前置条件

需要本机可用的 Python:

```bash
python --version
```

这套插件默认不依赖第三方 Python 包，使用标准库即可运行。

另外你还需要一个可访问的微信网关服务。

## 默认网关约定

默认配置如下:

```text
base_url   = http://127.0.0.1:3000
api_prefix = /v1/weixin
```

因此脚本会默认访问这些接口:

```text
POST /v1/weixin/login/start
POST /v1/weixin/login/wait
POST /v1/weixin/getupdates
POST /v1/weixin/sendmessage
POST /v1/weixin/getconfig
POST /v1/weixin/sendtyping
POST /v1/weixin/getuploadurl
```

## 快速开始

### 1. 初始化配置

```bash
python plugins/claude-weixin/scripts/weixin_bridge.py init ^
  --base-url http://127.0.0.1:3000 ^
  --api-prefix /v1/weixin ^
  --account-id demo-bot
```

执行后会生成:

`plugins/claude-weixin/data/weixin_bridge_config.json`

### 2. 查看当前配置

```bash
python plugins/claude-weixin/scripts/weixin_bridge.py show-config
```

### 3. 发起扫码登录

```bash
python plugins/claude-weixin/scripts/weixin_bridge.py login-start --account-id demo-bot
```

返回中通常应包含:

- `session_key`
- `qr_data_url` 或 `qrcode_url`

### 4. 等待登录完成

```bash
python plugins/claude-weixin/scripts/weixin_bridge.py login-wait
```

如果登录成功，脚本会自动把返回的 token 保存到本地配置里。

### 5. 拉取新消息

```bash
python plugins/claude-weixin/scripts/weixin_bridge.py pull
```

脚本会自动读取并更新 `get_updates_buf`，模拟 `openclaw-weixin` 的同步游标行为。

### 6. 发送文本消息

```bash
python plugins/claude-weixin/scripts/weixin_bridge.py send ^
  --to user@im.wechat ^
  --text "你好，这里是 Claude 微信桥接插件。"
```

### 7. 获取 typing ticket

```bash
python plugins/claude-weixin/scripts/weixin_bridge.py get-config --user-id user@im.wechat
```

### 8. 发送 typing 状态

```bash
python plugins/claude-weixin/scripts/weixin_bridge.py typing ^
  --user-id user@im.wechat ^
  --status 1
```

`status` 说明:

- `1`: 正在输入
- `2`: 取消输入

### 9. 申请上传参数

```bash
python plugins/claude-weixin/scripts/weixin_bridge.py upload-url ^
  --file .\demo.png ^
  --to user@im.wechat ^
  --media-type image
```

## 命令说明

### `init`

初始化或更新本地配置。

常用参数:

- `--base-url`
- `--api-prefix`
- `--auth-type`
- `--token`
- `--x-wechat-uin`
- `--account-id`
- `--bot-type`
- `--force`

### `show-config`

显示当前本地配置。

### `login-start`

调用扫码登录开始接口。

常用参数:

- `--account-id`
- `--bot-type`
- `--force-login`
- `--timeout-ms`

### `login-wait`

等待扫码登录完成。

常用参数:

- `--session-key`
- `--timeout-ms`

如果不传 `--session-key`，会读取本地缓存的 `last_session_key`。

### `pull`

调用 `getupdates` 拉取消息。

常用参数:

- `--sync-buffer`

如果不传，会自动读取本地保存的 `last_sync_buffer`。

### `send`

发送纯文本消息。

常用参数:

- `--to`
- `--text`
- `--context-token`

### `send-rich`

发送完整 `msg` JSON 结构，适合图片、文件、引用消息等复杂场景。

使用方式:

```bash
python plugins/claude-weixin/scripts/weixin_bridge.py send-rich --payload-file .\payload.json
```

也可以直接传 JSON:

```bash
python plugins/claude-weixin/scripts/weixin_bridge.py send-rich --payload-json "{\"to_user_id\":\"user@im.wechat\",\"item_list\":[{\"type\":1,\"text_item\":{\"text\":\"hello\"}}]}"
```

### `get-config`

读取某个用户上下文的配置，通常用于拿 `typing_ticket`。

常用参数:

- `--user-id`
- `--context-token`

### `typing`

发送 typing 状态。

常用参数:

- `--user-id`
- `--typing-ticket`
- `--status`

如果不传 `--typing-ticket`，会优先读取本地缓存的 `last_typing_ticket`。

### `upload-url`

向网关申请媒体上传参数。

常用参数:

- `--file`
- `--thumb-file`
- `--filekey`
- `--to`
- `--media-type`

支持的 `media-type`:

- `image`
- `video`
- `file`

## 配置文件说明

本地配置文件路径:

`plugins/claude-weixin/data/weixin_bridge_config.json`

典型内容如下:

```json
{
  "base_url": "http://127.0.0.1:3000",
  "api_prefix": "/v1/weixin",
  "auth_type": "ilink_bot_token",
  "token": "",
  "x_wechat_uin": "",
  "account_id": "demo-bot",
  "bot_type": "bot",
  "last_session_key": "",
  "last_sync_buffer": "",
  "last_typing_ticket": ""
}
```

字段说明:

- `base_url`: 网关根地址
- `api_prefix`: 接口前缀
- `auth_type`: 默认是 `ilink_bot_token`
- `token`: 登录成功后保存的 token
- `x_wechat_uin`: 可选请求头
- `account_id`: 当前机器人账号标识
- `bot_type`: 机器人类型
- `last_session_key`: 最近一次登录流程的 session key
- `last_sync_buffer`: 最近一次轮询游标
- `last_typing_ticket`: 最近一次 typing ticket

## 请求头约定

脚本默认发送这些请求头:

```text
Content-Type: application/json
AuthorizationType: ilink_bot_token
Authorization: Bearer <token>
X-WECHAT-UIN: <optional>
```

## 常见问题

### 1. 执行 `login-wait` 提示缺少 session key

先执行:

```bash
python plugins/claude-weixin/scripts/weixin_bridge.py login-start --account-id demo-bot
```

或者手动传入:

```bash
python plugins/claude-weixin/scripts/weixin_bridge.py login-wait --session-key your-session-key
```

### 2. 执行命令时报无法连接网关

检查:

- `base_url` 是否正确
- 网关服务是否已经启动
- 本机防火墙或端口占用情况

### 3. `typing` 提示缺少 ticket

先执行:

```bash
python plugins/claude-weixin/scripts/weixin_bridge.py get-config --user-id user@im.wechat
```

### 4. `upload-url` 不是完整上传

当前实现只负责申请上传参数，不负责:

- 文件 AES 加密
- 真正上传到 CDN
- 生成完整媒体消息体

这部分如果你要，我可以继续帮你补。

## 与 openclaw-weixin 的差异

相同点:

- 命令和能力分层尽量对齐
- 核心接口名字尽量对齐
- 同样采用扫码登录、轮询、发消息的模型

不同点:

- 这里是 Claude 插件，不是 OpenClaw SDK 插件
- 这里通过本地脚本转发 HTTP 请求
- 暂时没有实现 OpenClaw 里的媒体加密和完整消息管线

## 后续可扩展方向

- 增加二维码终端渲染
- 增加消息格式适配器
- 增加媒体上传与加密
- 增加一个 mock 微信网关用于本地联调
- 增加自动回复示例

## 参考

- `references/openclaw-weixin-mapping.md`
- `skills/SKILL.md`
- `D:/SourceCode/AISample/openclaw-sample/openclaw-weixin`
