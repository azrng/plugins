---
name: claude-weixin
description: 使用本地微信桥接脚本，通过仿 openclaw-weixin 的 HTTP JSON 网关完成扫码登录、拉取消息、发送消息、typing 状态和上传参数申请。
---

## 概览

`claude-weixin` 是一个面向 Claude 的微信插件骨架，设计思路参考 `openclaw-weixin`：

- 扫码登录分为 `login-start` 和 `login-wait`
- 接收消息使用 `getupdates` 长轮询模型
- 发送消息使用 `sendmessage`
- typing 状态使用 `sendtyping`
- 媒体上传前先申请 `getuploadurl`

这个插件本身不直接实现微信协议，而是把 Claude 侧能力收敛成一个本地脚本，去对接你自己的微信 HTTP 网关。

## 适用范围

**适用场景**
- 想仿照 `openclaw-weixin` 为 Claude 接一个微信桥接层
- 已经有自建微信后端，或者准备先做一个兼容接口的 mock 服务
- 需要把“扫码登录 / 拉消息 / 发消息 / typing / 上传参数”整理成固定命令流

**不适用场景**
- 需要一个已经内置真实微信逆向协议的完整实现
- 需要直接在插件里完成 CDN AES 加密上传
- 需要 GUI 扫码界面而不是 CLI/JSON 输出

**触发关键词**: 微信插件, Claude 微信, weixin plugin, 微信桥接, 微信网关, openclaw-weixin, 扫码登录, sendmessage, getupdates

## 前置条件

```bash
python --version
```

说明:
- 脚本只依赖 Python 标准库，无需额外安装包
- 你需要准备一个兼容接口的微信 HTTP 网关

## 核心能力

### 能力1: 初始化本地配置
生成并维护 `data/weixin_bridge_config.json`，保存网关地址、token、账号和轮询游标。

### 能力2: 扫码登录
通过 `login-start` 获取二维码地址和 `session_key`，再通过 `login-wait` 等待登录成功并落盘 token。

### 能力3: 长轮询拉消息
通过 `pull` 调用 `getupdates`，并自动记住 `get_updates_buf`。

### 能力4: 发送文本或高级消息
通过 `send` 发送文本消息，或者通过 `send-rich` 直接提交完整 `msg` JSON。

### 能力5: typing 和上传参数
通过 `get-config` 获取 typing ticket，通过 `typing` 发出输入中状态；通过 `upload-url` 申请媒体上传参数。

## 命令列表

| 命令 | 说明 | 用法 |
|------|------|------|
| `init` | 初始化或更新本地配置 | `python plugins/claude-weixin/scripts/weixin_bridge.py init --base-url http://127.0.0.1:3000 --api-prefix /v1/weixin` |
| `show-config` | 查看当前配置 | `python plugins/claude-weixin/scripts/weixin_bridge.py show-config` |
| `login-start` | 发起扫码登录 | `python plugins/claude-weixin/scripts/weixin_bridge.py login-start --account-id demo-bot` |
| `login-wait` | 等待扫码登录完成 | `python plugins/claude-weixin/scripts/weixin_bridge.py login-wait --session-key xxx` |
| `pull` | 拉取新消息 | `python plugins/claude-weixin/scripts/weixin_bridge.py pull` |
| `send` | 发送文本消息 | `python plugins/claude-weixin/scripts/weixin_bridge.py send --to user@im.wechat --text "hello"` |
| `send-rich` | 发送完整 `msg` JSON | `python plugins/claude-weixin/scripts/weixin_bridge.py send-rich --payload-file payload.json` |
| `get-config` | 获取账号配置 | `python plugins/claude-weixin/scripts/weixin_bridge.py get-config --user-id user@im.wechat` |
| `typing` | 发送/取消输入中状态 | `python plugins/claude-weixin/scripts/weixin_bridge.py typing --user-id user@im.wechat --status 1` |
| `upload-url` | 申请上传参数 | `python plugins/claude-weixin/scripts/weixin_bridge.py upload-url --file demo.png --to user@im.wechat --media-type image` |

## 处理步骤

### Step 1: 初始化网关配置

**目标**: 建立 Claude 插件与微信网关的基础连接配置。

**执行**
```bash
python plugins/claude-weixin/scripts/weixin_bridge.py init \
  --base-url http://127.0.0.1:3000 \
  --api-prefix /v1/weixin \
  --auth-type ilink_bot_token
```

**检查点**: `data/weixin_bridge_config.json` 已生成，输出中 `status` 为 `success`。

### Step 2: 发起扫码登录

**目标**: 获取二维码地址和会话 key。

**执行**
```bash
python plugins/claude-weixin/scripts/weixin_bridge.py login-start --account-id demo-bot
```

**检查点**: 返回 JSON 中存在 `session_key`，并尽量存在 `qr_data_url` 或 `qrcode_url`。

### Step 3: 等待登录成功

**目标**: 轮询扫码结果并持久化 token。

**执行**
```bash
python plugins/claude-weixin/scripts/weixin_bridge.py login-wait
```

**检查点**: 返回 JSON 中 `connected` 为 `true`，本地配置文件里的 `token` 已更新。

### Step 4: 拉取用户消息

**目标**: 模拟 `openclaw-weixin` 的 `getupdates` 流程。

**执行**
```bash
python plugins/claude-weixin/scripts/weixin_bridge.py pull
```

**检查点**: 返回体里出现 `msgs` 或 `items`，并且新的 `get_updates_buf` 已自动缓存。

### Step 5: 回复消息

**目标**: 向微信用户发送文本或高级结构消息。

**执行**
```bash
python plugins/claude-weixin/scripts/weixin_bridge.py send \
  --to user@im.wechat \
  --text "你好，这里是 Claude 微信桥接插件。"
```

**检查点**: 返回体里存在 `ret = 0`、`message_id` 或其他成功标识。

## 验证清单

- [ ] `plugins/claude-weixin/.claude-plugin/plugin.json` 存在
- [ ] `python plugins/claude-weixin/scripts/weixin_bridge.py --help` 可执行
- [ ] `init` 能生成本地配置
- [ ] `login-start` / `login-wait` 能与网关交互
- [ ] `pull` 能保存 `get_updates_buf`
- [ ] `send` 至少能正确发出 `sendmessage` 请求

## 输出格式

```json
{
  "status": "success",
  "command": "send",
  "request": {
    "endpoint": "/v1/weixin/sendmessage"
  },
  "response": {
    "ret": 0,
    "message_id": "123456"
  }
}
```

## 参考资料

- `references/openclaw-weixin-mapping.md`
- `D:/SourceCode/AISample/openclaw-sample/openclaw-weixin`

## 注意事项

- 这是 Claude 插件骨架，不是微信协议逆向实现
- `upload-url` 只负责申请上传参数，不负责 CDN 加密上传
- 如果后端字段命名和示例略有不同，脚本已兼容 `snake_case` / `camelCase` 的常见返回字段
