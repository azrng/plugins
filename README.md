# My Claude Plugins

个人 Claude 插件市场，包含实用插件集合。

## 插件来源说明

本市场的插件来源于以下两个渠道：

### 来源一：官方插件市场
摘录自 [Anthropic 官方插件市场](https://github.com/anthropics/claude-plugins-official)，用于学习和个人使用。

| 插件名 | 来源 | 说明 |
|--------|------|------|
| frontend-design | Anthropic | 创建高质量的前端界面设计 |

### 来源二：自建/第三方插件
自行创建或来源于第三方，用于学习目的。

| 插件名 | 来源 | 说明 |
|--------|------|------|
| weather-advisor | 自建/第三方 | 智能天气顾问，提供天气查询和穿衣建议 |

## 可用插件

### frontend-design
创建高质量的前端界面设计。生成独特、精致的前端代码和UI设计，避免通用的AI美学。

### weather-advisor
智能天气顾问。实时天气查询、未来7天预报、穿衣建议与出行活动推荐。

## 安装方式

将此目录复制或链接到：
```
C:\Users\用户名\.claude\plugins\marketplaces\my-plugins
```

或通过 git clone：
```bash
git clone <your-repo-url> C:\Users\用户名\.claude\plugins\marketplaces\my-plugins
```

## 结构

```
my-plugins/
├── .claude-plugin/
│   └── marketplace.json    # 市场配置
├── plugins/                # 插件目录
│   ├── frontend-design/
│   │   ├── .claude-plugin/
│   │   │   └── plugin.json
│   │   └── skills/
│   │       └── SKILL.md
│   └── weather-advisor/
│       ├── .claude-plugin/
│       │   └── plugin.json
│       ├── skills/
│       │   └── SKILL.md
│       ├── scripts/
│       └── data/
└── README.md
```
