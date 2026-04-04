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
| bootstrap-blazor | 自建 | BootstrapBlazor 组件库开发指南 |
| common-efcore | 自建 | Common.EFCore 库开发指南，Repository/UnitOfWork 模式 |
| console-di | 自建 | 控制台依赖注入框架，支持配置/日志/AOT |

## 可用插件

### frontend-design
创建高质量的前端界面设计。生成独特、精致的前端代码和UI设计，避免通用的AI美学。

### weather-advisor
智能天气顾问。实时天气查询、未来7天预报、穿衣建议与出行活动推荐。

### bootstrap-blazor
BootstrapBlazor 组件库开发指南。提供 .NET Blazor 项目中使用 BootstrapBlazor 的最佳实践、代码模板和常见模式。

### common-efcore
Common.EFCore 库开发指南。提供 .NET 项目中使用 Common.EFCore 封装 EF Core 的最佳实践，涵盖 Repository 模式、UnitOfWork、实体基类、多数据库提供者（MySQL/PostgreSQL/SQLite/SQLServer/InMemory）配置与使用。

### console-di
控制台依赖注入框架。为 .NET 控制台应用提供类似 ASP.NET Core 的依赖注入体验，支持 appsettings.json 配置、多日志输出（Console/Debug/文件）、环境配置和 Native AOT 编译。

## 安装方式

将此目录复制或链接到：
```
C:\Users\用户名\.claude\plugins\marketplaces\azrng-plugins
```

或通过 git clone：
```bash
git clone <your-repo-url> C:\Users\用户名\.claude\plugins\marketplaces\azrng-plugins
```

## 结构

```
azrng-plugins/
├── .claude-plugin/
│   └── marketplace.json    # 市场配置
├── plugins/                # 插件目录
│   ├── frontend-design/
│   │   ├── .claude-plugin/
│   │   │   └── plugin.json
│   │   └── skills/
│   │       └── SKILL.md
│   ├── weather-advisor/
│   │   ├── .claude-plugin/
│   │   │   └── plugin.json
│   │   ├── skills/
│   │   │   └── SKILL.md
│   │   ├── scripts/
│   │   └── data/
│   ├── bootstrap-blazor/
│   │   ├── .claude-plugin/
│   │   │   └── plugin.json
│   │   └── skills/
│   │       └── SKILL.md
│   ├── common-efcore/
│   │   ├── .claude-plugin/
│   │   │   └── plugin.json
│   │   └── skills/
│   │       └── SKILL.md
│   └── console-di/
│       ├── .claude-plugin/
│       │   └── plugin.json
│       └── skills/
│           └── SKILL.md
└── README.md
```
