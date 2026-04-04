---
name: console-di
description: "Azrng.ConsoleApp.DependencyInjection 库开发指南。.NET 控制台应用依赖注入框架，支持 appsettings.json 配置、多日志输出（Console/Debug/文件）、环境配置、AOT 编译。Keywords: ConsoleAppServer, IServiceStart, ConsoleApp, 依赖注入, DependencyInjection, Console DI, Azrng.ConsoleApp."
---

## 概述

Azrng.ConsoleApp.DependencyInjection 为 .NET 控制台应用提供类似 ASP.NET Core 的依赖注入体验。命名空间：`Azrng.ConsoleApp.DependencyInjection`。目标框架：net8.0 / net9.0 / net10.0，支持 Native AOT。

**触发关键词**: ConsoleAppServer, IServiceStart, ConsoleApp, 控制台依赖注入, Console DI, Azrng.ConsoleApp

**适用场景**：
- 使用 Azrng.ConsoleApp.DependencyInjection 构建 .NET 控制台应用
- 控制台应用需要依赖注入、配置文件、日志
- 替代手动搭建 ServiceProvider 的场景

**不适用场景**：
- ASP.NET Core Web 应用（已有内置 DI）
- 不使用此库的原生控制台应用

## 前置条件

```bash
dotnet add package Azrng.ConsoleApp.DependencyInjection
```

## 核心组件

### IServiceStart 接口

所有控制台应用服务必须实现此接口：

```csharp
using Azrng.ConsoleApp.DependencyInjection;

public class MyService : IServiceStart
{
    private readonly ILogger<MyService> _logger;
    private readonly IConfiguration _config;

    public MyService(ILogger<MyService> logger, IConfiguration config)
    {
        _logger = logger;
        _config = config;
    }

    public string Title => "我的控制台应用";

    public async Task RunAsync()
    {
        _logger.LogInformation("应用已启动");
        // 业务逻辑
    }
}
```

### ConsoleAppServer 构建器

核心构建器，自动完成：加载配置 → 创建服务容器 → 配置日志。

**构造函数行为**：
1. 从 `AppContext.BaseDirectory` 加载 `appsettings.json`（可选）
2. 检测 `DOTNET_ENVIRONMENT` 或 `ASPNETCORE_ENVIRONMENT` 环境变量，加载 `appsettings.{Environment}.json`
3. 加载 `ASPNETCORE_` 前缀的环境变量（自动移除前缀）
4. 加载命令行参数
5. 创建 ServiceCollection 并注册 IConfiguration
6. 配置日志：Console + Debug + 自定义文件日志（ExtensionsLoggerProvider）

**配置加载优先级**（低→高）：`appsettings.json` → 环境配置文件 → 环境变量 → 命令行参数

## 使用模式

### 模式一：简单使用

```csharp
// Program.cs
var builder = new ConsoleAppServer(args);
await using var sp = builder.Build<MyService>();
await sp.RunAsync();
```

### 模式二：注入额外服务

```csharp
var builder = new ConsoleAppServer(args);

// 通过 Services 属性注册服务
builder.Services.AddHttpClient();
builder.Services.AddScoped<IRepository, SqlRepository>();

await using var sp = builder.Build<MyService>();
await sp.RunAsync();
```

### 模式三：委托方式注册（AOT 友好）

```csharp
var builder = new ConsoleAppServer(args);
await using var sp = builder.Build<MyService>(services =>
{
    services.AddHttpClient();
    services.Configure<MyOptions>(builder.Configuration.GetSection("MyOptions"));
});
await sp.RunAsync();
```

## 配置系统

### appsettings.json

```json
{
  "Logging": {
    "LogLevel": {
      "Default": "Information",
      "Microsoft": "Warning"
    }
  },
  "AppSettings": {
    "ConnectionString": "localhost",
    "Timeout": 30
  }
}
```

### 环境变量

环境变量必须加 `ASPNETCORE_` 前缀，用 `__` 代替 `:` 层级：

```bash
# Linux/Mac
export ASPNETCORE_AppSettings__ConnectionString="prod-server"
export DOTNET_ENVIRONMENT="Production"

# Windows
set ASPNETCORE_AppSettings__ConnectionString=prod-server
```

读取：`Configuration["AppSettings:ConnectionString"]`

### 命令行参数

```bash
dotnet run --AppSettings:ConnectionString "override-server"
```

### 访问配置

```csharp
public class MyService : IServiceStart
{
    private readonly IConfiguration _config;

    public MyService(IConfiguration config) => _config = config;

    public async Task RunAsync()
    {
        var connStr = _config["AppSettings:ConnectionString"];
        var timeout = _config.GetValue<int>("AppSettings:Timeout");
    }
}
```

### 访问 Configuration 注入选项

```csharp
// 在 Build 委托中注册
builder.Build<MyService>(services =>
{
    services.Configure<AppOptions>(builder.Configuration.GetSection("App"));
});

// 在服务中注入
public class MyService : IServiceStart
{
    private readonly AppOptions _options;

    public MyService(IOptions<AppOptions> options) => _options = options.Value;
}
```

## 日志系统

自动配置三种日志输出：

| 输出目标 | 说明 |
|---------|------|
| Console | 控制台输出 |
| Debug | Visual Studio 调试窗口 |
| ExtensionsLogger | 本地文件（通过 `LocalLogHelper`） |

日志级别由 `appsettings.json` 的 `Logging:LogLevel:Default` 控制，文件日志额外受 `CoreGlobalConfig.MinimumLevel` 约束。

```csharp
public class MyService : IServiceStart
{
    private readonly ILogger<MyService> _logger;

    public MyService(ILogger<MyService> logger) => _logger = logger;

    public async Task RunAsync()
    {
        _logger.LogInformation("处理用户 {UserId}", userId);
        _logger.LogError(ex, "处理失败 {Error}", ex.Message);
    }
}
```

## RunAsync 扩展方法

`ServiceProvider.RunAsync()` 执行流程：
1. 创建 AsyncScope
2. 解析 `IServiceStart` 实例
3. 打印标题分隔线（`ConsoleTool.PrintTitle`）
4. 调用 `service.RunAsync()`
5. 异常自动记录到本地日志文件

## ConsoleAppServer API

| 属性/方法 | 说明 |
|----------|------|
| `Services` | IServiceCollection，可手动注册服务 |
| `Configuration` | IConfiguration，已构建的配置 |
| `Build<T>()` | 注册 IServiceStart 并构建 ServiceProvider |
| `Build<T>(Action<IServiceCollection>)` | 委托注册服务后构建 |

## 完整开发步骤

### Step 1：创建控制台项目

```bash
dotnet new console -n MyConsoleApp
cd MyConsoleApp
dotnet add package Azrng.ConsoleApp.DependencyInjection
```

### Step 2：添加 appsettings.json

```json
{
  "Logging": {
    "LogLevel": {
      "Default": "Information"
    }
  }
}
```

设置文件属性：复制到输出目录 → 如果较新则复制。

### Step 3：定义服务

```csharp
using Azrng.ConsoleApp.DependencyInjection;

public class AppService : IServiceStart
{
    public string Title => "我的应用";
    private readonly ILogger<AppService> _logger;

    public AppService(ILogger<AppService> logger) => _logger = logger;

    public async Task RunAsync()
    {
        _logger.LogInformation("开始执行");
        // 业务逻辑
    }
}
```

### Step 4：编写入口

```csharp
// Program.cs
var builder = new ConsoleAppServer(args);
await using var sp = builder.Build<AppService>();
await sp.RunAsync();
```

## Native AOT 支持

项目已配置 AOT 兼容（`IsAotCompatible`、`TrimMode=link`）。发布：

```bash
dotnet publish -c Release -r win-x64 /p:PublishAot=true
```

AOT 注意事项：
- `Build<T>()` 使用 `DynamicallyAccessedMembers` 特性保证构造函数可用
- 避免反射、`Activator.CreateInstance`
- 使用委托方式 `Build<T>(Action<IServiceCollection>)` 注册服务

## 验证清单

- [ ] 服务类实现 `IServiceStart` 接口（Title + RunAsync）
- [ ] `appsettings.json` 设为"复制到输出目录"
- [ ] 使用 `await using` 确保 ServiceProvider 正确释放
- [ ] 环境变量加 `ASPNETCORE_` 前缀
- [ ] 环境变量层级用 `__`（双下划线）代替 `:`
- [ ] AOT 场景使用委托方式注册服务，避免反射

## 参考资源

- [NuGet 包](https://www.nuget.org/packages/Azrng.ConsoleApp.DependencyInjection)
- [GitHub 源码](https://github.com/azrng/nuget-packages)
- [Microsoft.Extensions.DependencyInjection 文档](https://learn.microsoft.com/dotnet/core/extensions/dependency-injection)
