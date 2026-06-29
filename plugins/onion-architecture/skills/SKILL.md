---
name: onion-architecture
description: Guide for the .NET onion/clean architecture used across Azrng solution templates (Core/IDomain/IApplication/Domain/Application/EntityFramework/Service layers, plus Storage/Adapter). Covers the two cross-cutting conventions every AppService follows — global result-packing (success returns Task<T>, business failure throws ParameterException, packed by AddMvcResultPackFilter + app.UseGlobalException) and paged queries (GetPageRequest + WhereIfNotNullOrWhiteSpace + ToPageListAsync + GetQueryPageResult<T>). Use when adding a new feature, deciding which project a class belongs in, wiring DI / middleware in Program.cs, creating a new AppService/Controller/Entity/Configuration, or reviewing where business logic vs data-access vs DTOs should live. Triggers on questions like "这个类该放哪一层", "新建一个 XXX 功能", "控制器太胖怎么拆", "接口返回值怎么写 / 要不要包 IResultModel", "分页查询怎么写", or confusion about IApplication vs Application / IDomain vs Domain project pairs.
---

# 洋葱架构（Onion / Clean Architecture）分层指南

指导在 Azrng 系列解决方案里正确分层：哪一层放什么、层间依赖方向、项目结对（接口/实现）、典型 CRUD 功能落点，以及贯穿所有 AppService 的两条横切约定——**全局返回包装**与**分页查询**。

> 本文件是**决策入口与规则总览**；各层完整代码示例、跨层数据流、`.csproj` 依赖详见 `references/layer-responsibilities.md`。

## 分层全景

依赖**由外向内**，内层不得引用外层。`Core` 是最内核（零业务依赖），`Service` 是最外层（组装+入口）。

```
                ┌─────────────────────────────────────────┐
   外层(依赖内层) │  Service（Web 入口：Controllers/Program） │
                ├─────────────────────────────────────────┤
                │  Application（应用服务实现：业务编排）      │  ← IApplication 的实现
                ├─────────────────────────────────────────┤
                │  Domain（领域服务实现：可复用公共操作）               │  ← IDomain 的实现（按需）
                ├─────────────────────────────────────────┤
                │  EntityFramework / Storage（DbContext/存储）│
                ├─────────────────────────────────────────┤
   内核(被依赖)  │  IApplication  │  IDomain  │  Core        │
                │ (服务接口+DTO入口)│(实体+配置)│(纯DTO/常量) │
                └─────────────────────────────────────────┘
```

### 标准项目清单（按依赖从内到外）

| 项目 | 角色 | 可依赖 | 典型内容 |
|---|---|---|---|
| **Core** | 最内核，纯契约/契约数据 | 仅 NuGet 基础包 | DTO、Request/Response、枚举、常量 |
| **IDomain** | 领域契约层 | Core | 实体（Entity） |
| **IApplication** | 应用契约层 | Core, IDomain | AppService 接口（`I*AppService`） |
| **Domain** | 领域实现层 | IDomain, Adapter, EntityFramework | 领域服务实现（`{X}DomainService`）：封装可复用公共领域操作，可注入 IBaseRepository 写库；纯 CRUD 可空 |
| **Application** | 应用实现层 | IApplication, Domain | AppService 实现（`*AppService`）：用例编排、实体↔DTO 映射、调用 DomainService/仓储/适配器 |
| **EntityFramework** | 基础设施-数据 | Core, IDomain | `DbContext`、EFCore 配置类（`{Entity}Etc.cs`）、迁移 |
| **Service** | 入口/组装层 | Application, Storage | `Controllers`、`Program.cs`（DI 装配 + 中间件管道）、配置 |
| **Adapter** | 外部适配器 | IDomain | 外部系统调用封装：`I{X}Adapter`（接口在 `IDomain/Adapter/`）+ HttpClient 实现（`Adapter/Service/`、`Adapter/HttpWebClient/`），屏蔽 HTTP/SDK 细节（可选） |
| **Storage** | 存储适配 | Core | 文件/对象存储封装（可选） |

> **接口/实现结对**：`I*` 项目只有抽象，对应无前缀项目是实现。`IApplication`/`Application`、`IDomain`/`Domain` 总是成对出现。控制器永远只依赖 `I*AppService`，不依赖实现。

## 核心规则（AI 必读）

1. **依赖单向向内**：外层引用内层，内层绝不引用外层。`Core` 不引用任何项目；`Service` 引用 `Application`（不直接引用 `IBaseRepository`）。
2. **控制器瘦**：控制器只做 HTTP 适配——接参数 → 调 `I*AppService` → 一行转发返回值。**不写 EF 查询、不注入 `IBaseRepository`、不写业务校验、不写 `Ok()`/`return ResultModel`**。
3. **应用编排 vs 领域操作分层**：`AppService`（应用层）承担**用例编排**——接 DTO → 调领域服务/仓储/适配器 → 返回 DTO + 实体↔DTO 映射；**可复用的公共领域操作下沉到 DomainService**（领域层），如「发会话消息」「读系统配置」这类被多个 AppService 复用的操作。**AppService 和 DomainService 都可注入 `IBaseRepository<T>` / `IUnitOfWork` 做数据访问**（并非 AppService 独占）。判断：单一用例、不复用 → 直接写在 AppService；多 AppService 复用 / 稳定领域概念 → 抽 DomainService。详见「领域服务 DomainService」。
4. **DTO 放 Core 或 IApplication**：通用业务 DTO/Request/Response 放 `Core/Models`，跨层共享（接口、实现、控制器都用）。不要在控制器内 inline 定义请求类。仅服务内部用、与某 AppService 强绑定的 DTO（如 `LoginResultDto`）可放 `IApplication/{Module}/`。
5. **实体在 IDomain、配置在 EntityFramework**：实体（继承 `IdentityOperatorStatusEntity`）放 `IDomain/Entities/`；EFCore 配置类（`{Entity}Etc.cs`，继承 `EntityTypeConfigurationIdentityOperatorStatus<TEntity, TKey>`）放 **EntityFramework 层**，`Configure` 里设表名/列名/查询过滤；DbContext 用 `ApplyConfigurationsFromAssembly(当前程序集)` 扫描它们（详见 azrng-efcore skill）。
6. **接口先行**：每个 AppService 先在 `IApplication` 定义 `IXxxAppService`，再在 `Application` 实现。控制器注入的是接口。
7. **返回值走全局包装（首选）**：AppService **成功直接 `return Task<T>`（业务对象）**，由 `CustomResultPackFilter` 自动包成 `ResultModel<T>(success)`；**业务校验/规则失败 `throw new ParameterException(msg)`**（或 `LogicBusinessException`），由全局异常中间件 `app.UseGlobalException()` 统一映射成失败结果。控制器一行转发 `return _appService.XxxAsync(...)`。**三件套缺一不可**（见「全局返回包装」）。历史写法 `Task<IResultModel<T>>` 手动 `Success/Error` 为迁移期可容忍，新代码不再使用。

## 全局返回包装（三件套 + Program.cs 装配）

这是本架构的**统一对外结果契约**：所有 action 返回值最终都是 `{ isSuccess, code, message, data }` 形态的 `ResultModel`，但**业务代码不手动包装**——靠框架三件套自动完成。

### 三件套（来自 `Azrng.AspNetCore.Core`，缺一不可）

| 件 | 注册 | 负责路径 | 行为 |
|---|---|---|---|
| 返回值包装过滤器 `CustomResultPackFilter` | `services.AddMvcResultPackFilter("/swagger")` | **成功路径** | action 返回值**非 `IResultModel`** → 包成 `ResultModel<T>(data, true, "success", "200")`；`EmptyResult`→`ResultModel(true,"成功")`；已是 `IResultModel` 则**不重复包装**；`[NoWrapper]` 特性或忽略前缀跳过 |
| 模型校验过滤器 `ModelVerifyFilter` | `services.AddMvcModelVerifyFilter()` | **模型校验失败** | 把 `ModelState` 错误转成 `ResultModel(false,"参数格式不正确","400", errors)` |
| 全局异常中间件 `CustomExceptionMiddleware` | `app.UseGlobalException()` | **业务异常 / 未处理异常** | catch 异常，按类型映射成 `ResultModel(false, msg, code)`（见下表） |

> **成功路径靠过滤器，失败路径靠异常中间件**——这是全局包装的核心。两者必须都装配，否则失败抛异常会变成裸 500。

### 业务异常 → 结果映射（`CustomExceptionMiddleware`）

| 业务场景 | 抛什么（`Azrng.Core.Exceptions`） | HTTP 状态码 | ErrorCode |
|---|---|---|---|
| 参数错误 / 业务校验失败 | `throw new ParameterException(msg)` | 400 | `"400"` |
| 业务规则不满足（语义同参数异常） | `throw new LogicBusinessException(msg)` | 400 | `"400"` |
| 资源不存在（按 id 查不到） | `NotFoundException.ThrowIfNull(entity, "记录不存在")` | 404 | `"404"` |
| 无权限 / 鉴权失败 | `throw new ForbiddenException(msg)` | 401 | `"401"` |
| 服务器内部错误 | `throw new InternalServerException(msg)` | 500 | `"500"` |
| 其他未处理异常 | （任何 `Exception`） | 500 | `"500"` |

> 默认按真实 HTTP 状态码返回（400/404/401/500）。若要统一返回 200、错误信息只放 body，配 `CommonMvcConfig.UseHttpStateCode = false`。

### Program.cs 装配（标准模板，三件套都在这里）

```csharp
var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllers();
// ① 成功路径包装（"/swagger" 等前缀不包装）
builder.Services.AddMvcResultPackFilter("/swagger");
// ② 模型校验失败统一结果
builder.Services.AddMvcModelVerifyFilter();
// ... AddEntityFramework / RegisterBusinessServices / 认证 等 ...

var app = builder.Build();

// ③ 全局异常中间件：必须放在管道最外层（最早），才能兜住后续所有中间件/控制器抛出的异常
app.UseGlobalException();

app.UseCors();
app.UseAuthentication();
app.UseAuthorization();
app.MapControllers();
app.Run();
```

> **最常见的坑**：只注册了 `AddMvcResultPackFilter` 却忘了 `app.UseGlobalException()`——此时 AppService 抛 `ParameterException` 无人接住，业务失败会返回 HTTP 500，前端拿不到统一失败结构。三件套必须齐备。

### AppService / 控制器写法（全局包装模式）

```csharp
// 接口（IApplication）：返回裸 Task<T>，不出现 IResultModel
public interface IOrderAppService
{
    Task<OrderDto> GetAsync(long id);                 // 成功返 DTO
    Task<long> CreateAsync(CreateOrderRequest req);   // 成功返 id
    Task DeleteAsync(long id);                        // 无返回数据
}

// 实现（Application）：成功直接 return；失败 throw 业务异常（不要手写 ResultModel.Error）
public async Task<OrderDto> GetAsync(long id)
{
    var order = await _repository.EntitiesNoTacking.FirstOrDefaultAsync(x => x.Id == id);
    NotFoundException.ThrowIfNull(order, "订单不存在");   // 资源不存在 → 404
    return new OrderDto { /* 实体→DTO 映射 */ };
}

public async Task<long> CreateAsync(CreateOrderRequest req)
{
    if (req.Amount <= 0)
        throw new ParameterException("金额必须大于 0");   // 业务校验失败 → 400
    var order = new Order { /* ... */ };
    await _repository.AddAsync(order, submit: true);
    return order.Id;                                     // 成功 → 过滤器包成 ResultModel<long>(success)
}
```

```csharp
// 控制器（Service）：一行转发，不写 Ok() / 不写 ResultModel
[HttpGet("{id}")]
public Task<OrderDto> Get(long id) => _orderAppService.GetAsync(id);

[HttpPost]
public Task<long> Create([FromBody] CreateOrderRequest req) => _orderAppService.CreateAsync(req);
```

> 关于 `IResultModel<T>`（历史/迁移期）：旧代码里 AppService 返回 `Task<IResultModel<T>>`、手动 `ResultModel<T>.Success/Error`，仍能工作（过滤器不重复包装），迁移期可与全局包装共存。但新代码统一用全局包装：更省事、控制器/AppService 一行转发。逐步替换即可。

## 分页查询最佳实践

列表查询**不要手写 `CountAsync()` + `Skip().Take().ToListAsync()`**，也不要自定义 `{ List, Total }` 响应类。用框架的一套：请求继承 `GetPageRequest` + 链式条件 + `ToPageListAsync` + 返回 `GetQueryPageResult<T>`。

### 四件套

| 角色 | 类型/API | 命名空间（using） |
|---|---|---|
| 分页请求基类（带 `PageIndex`/`PageSize`） | `GetPageRequest` | `Azrng.Core.Requests` |
| 条件筛选（值非空才 Where，替代手写 `if`） | `IQueryable<T>.WhereIfNotNullOrWhiteSpace(value, predicate)` | `Azrng.Core.Extension` |
| 一次完成 Count + 分页 | `IQueryable<T>.ToPageListAsync(GetPageRequest, RefAsync<int>)` | `Azrng.EFCore.Extensions` |
| 总数引用容器 | `RefAsync<int>` | `Azrng.Core.CommonDto` |
| 分页结果（`Rows` + `PageInfo`） | `GetQueryPageResult<T>` | `Azrng.Core.Results` |

### 标准写法（AppService）

```csharp
// 1) 请求类继承 GetPageRequest，只声明业务筛选字段（PageIndex/PageSize 由基类提供）
public class EmployeeListRequest : GetPageRequest
{
    public string? Username { get; set; }
    public string? Role { get; set; }
}

// 2) AppService：链式 WhereIfNotNullOrWhiteSpace + ToPageListAsync，返回 GetQueryPageResult<Dto>
public async Task<GetQueryPageResult<EmployeeDto>> GetListAsync(EmployeeListRequest request)
{
    var total = new RefAsync<int>();                 // 接收总数
    var list = await _repository.EntitiesNoTacking.Where(e => !e.Deleted)
        .WhereIfNotNullOrWhiteSpace(request.Username, t => t.Username.Contains(request.Username!))
        .WhereIfNotNullOrWhiteSpace(request.Role, t => t.Role == request.Role)
        .OrderByDescending(e => e.CreateTime)
        .Select(t => new EmployeeDto { Id = t.Id, Username = t.Username, /* ... */ })
        .ToPageListAsync(request, total);            // 内部一次 Count + Skip/Take

    return new GetQueryPageResult<EmployeeDto>(list, new GetQueryPageResult(request, total));
    // 或等价的四参构造：new GetQueryPageResult<EmployeeDto>(list, request.PageIndex, request.PageSize, total);
}
```

> `RefAsync<T>` 有到 `T` 的隐式转换，所以 `new GetQueryPageResult(request, total)` 里 `RefAsync<int>` 可直接当 `long totalCount` 用。
> 返回的 `GetQueryPageResult<Dto>` 经全局包装过滤器自动包成 `ResultModel<GetQueryPageResult<EmployeeDto>>(success)`，前端拿到 `{ isSuccess, data: { rows:[...], pageInfo:{ pageIndex, pageSize, total, totalPage } } }`。
> 分页/条件扩展 API 的完整签名（`PagedBy`、`WhereIfNotNull<T,F>`、`WhereAny` 等）见 azrng-efcore skill「分页/条件查询扩展」。

## 领域服务 DomainService（可复用公共操作）

当一段领域操作**会被多个 AppService 复用**，或封装**稳定的多实体领域规则/数据访问**时，不要在每个 AppService 里重复写——抽成 DomainService。典型：会话消息收发、系统配置读写、指标计算、同义词管理等“公共能力”。

**结对模式**（与 AppService 一致：接口在 `I*`、实现在无前缀项目）：

| | 位置 | 命名 |
|---|---|---|
| 接口 | `IDomain/{Module}/` | `I{X}DomainService` |
| 实现 | `Domain/{Module}/` | `{X}DomainService : IScopedDependency, I{X}DomainService` |

**关键点**：
- DomainService **可注入 `IBaseRepository<T>` / `IUnitOfWork` 自己读写数据**（`Domain` 项目依赖 `EntityFramework`），也可注入 Adapter/缓存等——**数据访问并非 AppService 独占**。
- AppService 注入 `I{X}DomainService` 调用它，自己只做用例编排 + 实体↔DTO 映射。
- DomainService 返回领域对象（Entity/Bo），**不碰 HTTP 与 DTO 映射**（那是 AppService 的活）；同样标 `IScopedDependency` 自动注册。

> 完整代码示例（接口/实现/AppService 调用三方结对）见 `references/layer-responsibilities.md → Domain 层`。

> **判断门槛**：操作只被**一个 AppService 用、不会复用**时，直接写在那个 AppService 里即可，不必提前抽 DomainService（避免过度设计）。复用真正出现、或领域规则变复杂时再下沉——`ISystemConfigDomainService` 就是后来被 5+ 个 AppService 共用才抽出来的。

## 外部适配器 Adapter（封装第三方/外部系统调用）

调用**外部系统**（第三方 API、其他微服务、SDK、外部协议）时，用 Adapter 层封装——把 HTTP/协议细节屏蔽在 Adapter 内，对内暴露领域语义方法，让 AppService/DomainService 依赖**接口**而非具体 HttpClient。

### 两层结构（复杂外部调用推荐）

| 层 | 接口位置 | 实现位置 | 数据对象 | 职责 |
|---|---|---|---|---|
| 领域适配器 `I{X}Adapter` | `IDomain/Adapter/` | `Adapter/Service/` | **Bo**（`IDomain/Adapter/{模块}/`） | 对外领域语义方法、Bo↔Ho 转换 |
| HTTP 客户端 `IXxxHttpClient` | `Adapter/HttpWebClient/` | `Adapter/HttpWebClient/` | **Ho**（`Adapter/Ho/{模块}/`） | 真实 HTTP 调用（URL/token/序列化） |

### 关键点

- **接口放 IDomain/Adapter/（不放 Core）**：这样 AppService/DomainService 只依赖 IDomain 就能用 Adapter，而 HttpClient/SDK 等**实现细节留在 Adapter 项目**，依赖方向正确（外层 Adapter 实现内层 IDomain 接口；IDomain 不依赖 Adapter）。`Adapter.csproj` 只引用 `IDomain`。
- **Bo vs Ho**：`Bo`（业务对象，接口签名用）在 IDomain；`Ho`（HTTP 传输对象）在 Adapter。Adapter 实现里做 Bo↔Ho 转换——外部协议/字段变了只改 Adapter，不波及业务层。
- 实现（`{X}Adapter`、`XxxHttpClient`）都标 `IScopedDependency`，经 `RegisterBusinessServices` 自动注册；底层 HttpClient 还可配 `IHttpClientFactory` / 框架的 `AddHttpClientService`。
- **`IHttpHelper` 来自 `Common.HttpClients` 包**：Adapter 项目（或 Core）安装 `dotnet add package Common.HttpClients`（参考项目用 v2.0.0，按需选版本）后即可注入 `IHttpHelper` 做统一 HTTP 调用（GetAsync/PostAsync 等）。
- **简单场景可只用一层**（领域适配器直接调通用 `IHttpHelper`），外部调用复杂、协议多变时才拆出 `IXxxHttpClient` 层。

> 完整代码示例（接口/两层实现/AppService 调用）见 `references/layer-responsibilities.md → Adapter 层`。

> **判断门槛**：调用**本系统数据库** → AppService/DomainService 直接注入 `IBaseRepository`；调用**外部系统** → 走 Adapter（接口 `I{X}Adapter` 在 IDomain，实现+HttpClient 在 Adapter），业务层只依赖接口。

## JSON 序列化（IJsonSerializer）

需要 JSON 序列化时，统一注入 `IJsonSerializer`（`Azrng.Core.IJsonSerializer`），**不要在各处直接用 `JsonSerializer`/`JsonConvert`**——底层切换 STJ↔Newtonsoft 只改一处。API：`ToJson<T>(obj)`、`ToObject<T>(json)`、`Clone<T>(obj)`（深拷贝）、`ToList<T>(json)`。

- 实现 + 注册：`Azrng.Core.Json`（System.Text.Json 实现 `SysTextJsonSerializer`，推荐、AOT 友好）或 `Azrng.Core.NewtonsoftJson`（`NewtonsoftJsonSerializer`，兼容旧代码）。Service 项目装实现包后 `builder.Services.ConfigureDefaultJson();`（`using Azrng.Core.Json;`）注册。
- 默认配置（`DefaultJsonSerializerOptions`）：驼峰命名、不转义中文（`UnsafeRelaxedJsonEscaping`）、内置 Enum/DateTime/Long→String 等转换器。

> 业务层依赖 `IJsonSerializer` 接口；切换底层只改 Service 项目装的实现包 + 注册，不波及业务。

## 新增一个完整 CRUD 功能的标准流程

以"商品(Product)管理"为例，自内向外依次落地（详版含每步完整代码见 `references/layer-responsibilities.md → 完整功能落点速查`）：

1. **Core/Models/ProductDto.cs** — `ProductDto` / `CreateProductRequest` / `UpdateProductRequest`；列表 Request 继承 `GetPageRequest`。
2. **IDomain/Entities/Product.cs** — 实体继承 `IdentityOperatorStatusEntity`，构造函数 `SetCreator("system")`。
3. **EntityFramework/ProductEtc.cs** — 配置类继承 `EntityTypeConfigurationIdentityOperatorStatus<Product, long>`，`base.Configure(builder)` 后设表名/列名/查询过滤。
4. **IApplication/Product/IProductAppService.cs** — 接口，返回 `Task<T>` / `Task<GetQueryPageResult<T>>`（全局包装，不出现 IResultModel）。
5. **Application/Product/ProductAppService.cs** — 实现类加 `IScopedDependency`（自动注册），注入 `IBaseRepository<Product>`，写查询/校验/CRUD；成功 `return dto`，业务失败 `throw new ParameterException(msg)`，资源不存在 `NotFoundException.ThrowIfNull`；列表用 `WhereIfNotNullOrWhiteSpace` + `ToPageListAsync` + `GetQueryPageResult<T>`。
6. **Service/Controllers/ProductController.cs** — 注入 `IProductAppService`，每个 action 一行转发。无需手写 `AddScoped`（扫描注册自动完成）。

> 配置类由 DbContext 的 `ApplyConfigurationsFromAssembly(当前程序集)` 自动扫描应用；新增实体只需在 DbContext 加 `DbSet` + 写一个 `{Entity}Etc.cs` 配置类。如用 SQL 脚本迁移，在 `Service/MigrationSql/` 增版本脚本（详见 azrng-efcore skill）。

## 命名约定

| 类型 | 命名 | 位置 |
|---|---|---|
| 应用服务接口 | `I{Entity}AppService` | IApplication |
| 应用服务实现 | `{Entity}AppService` | Application |
| 控制器 | `{Entity}Controller` | Service/Controllers |
| 实体 | 单数 `{Entity}` | IDomain/Entities |
| 配置类 | `{Entity}Etc` | EntityFramework |
| DbContext | `{Solution}DbContext` | EntityFramework |

## 何时该拆/不该拆（决策速查）

只列**决策增量**——基础规则见上方「核心规则」，分页/全局包装写法见对应章节。

- **该不该新建项目？** 标准模板共 9 个项目：7 个核心分层（Core/IDomain/IApplication/Domain/Application/EntityFramework/Service）+ 2 个可选基础设施（Adapter 外部 API 封装、Storage 文件/对象存储）。只有引入全新基础设施（如 Redis、消息队列、第三方 SDK）才新增独立项目（如 `Cache`/`Notification`），并保持单向依赖。多数纯 CRUD 项目初期 Domain/Adapter/Storage 可空，出现对应需求（复用操作 / 外部调用 / 文件存储）再建。
- **读取用 `Entities` 还是 `EntitiesNoTacking`？** 只读查询默认 `EntitiesNoTacking`（不带追踪、更快）；读出来还要改并回写才用 `Entities`。
- **事务该用 `IUnitOfWork` 还是直接注入 DbContext？** 多步原子写优先用 `IUnitOfWork.CommitTransactionAsync(async () => {...})`（自动开/提交/回滚）。只有需要原生 SQL / `FOR UPDATE` 行锁（如并发扣库存/抢购）才让 AppService 注入 DbContext 用 `BeginTransactionAsync()` + `FromSqlInterpolated`——这是 DbContext 跨层注入的少数合理场景。
- **控制器能不能调多个 AppService？** 可以，但要警惕——若一个请求要协调多个服务完成一个事务，说明该把编排逻辑下沉到一个 AppService（用 `IUnitOfWork` 包事务），控制器只调这一个。

## 依赖注入与中间件装配（Program.cs）

AppService 用**约定式自动扫描注册**：实现类实现 `Azrng.Core.DependencyInjection.IScopedDependency`（或 `ITransientDependency`/`ISingletonDependency`），再调一次 `RegisterBusinessServices` 扫描程序集，按生命周期接口自动注册。完整 Program.cs 装配代码（含三件套）见上方「全局返回包装 → Program.cs 装配」。

```csharp
builder.Services.AddEntityFramework<AppDbContext>(o =>
{
    o.ConnectionString = builder.Configuration.GetConnectionString("DefaultConnection")!;
    o.Schema = "public";
});

// 扫描匹配程序集，把实现 IScope/Transient/SingletonDependency 的类自动注册
builder.Services.RegisterBusinessServices("App.*.dll");
```

AppService 实现类标接口即可被扫到（无需手写 `AddScoped`）：
```csharp
using Azrng.Core.DependencyInjection;

public class ProductAppService : IScopedDependency, IProductAppService  // ← IScopedDependency 触发自动注册
{ /* ... */ }
```

> 早期代码里逐个 `AddScoped<IXxx, Xxx>()` 的写法仍在（迁移过渡期），新代码用 `IScopedDependency` + 扫描注册，避免漏注册。控制器由 `AddControllers()` 自动发现，无需注册。
> **Service.csproj 需引用的包**：`Azrng.AspNetCore.Core`（三件套 + `RegisterBusinessServices`）、provider 包（如 `Npgsql.EntityFrameworkCore.PostgreSQL`，提供 `AddEntityFramework<TDbContext>`）、按需 `Azrng.SqlMigration`（SQL 迁移）/ `Azrng.AspNetCore.Authentication.JwtBearer`（JWT）/ `Swashbuckle.AspNetCore`（Swagger）/ `Azrng.Core.Json`（`ConfigureDefaultJson` + `IJsonSerializer`）。

## 常见反模式（最易踩）

| 反模式 | 正确做法 |
|---|---|
| 控制器注入 `IBaseRepository<T>` 写查询 / 写业务校验 | 查询和校验移到 AppService，控制器只一行转发 |
| 列表查询手写 `CountAsync()` + `Skip().Take()` + 自定义 `{List,Total}` 类 | 用分页四件套（`ToPageListAsync` + `GetQueryPageResult<T>`） |
| 实体直接作为 API 返回值 | AppService 映射成 Core 的 DTO 再返回；实体只在 AppService↔DbContext 间流动 |
| 新功能不建接口直接写实现类 | 先 `I*AppService` 接口，控制器依赖接口 |

> 遇到存量项目未遵循上述约定（如用 Newtonsoft、自研 ResultFilter、`QueryableWhereIf`），按现有代码风格走、不强行改写可工作代码；新增功能才按本指南。

## 深入参考

- **各层职责详细对照 + 跨层数据流 + 完整代码示例（全局包装 / 分页写法）**：见 references/layer-responsibilities.md
- **数据访问（仓储/工作单元/实体基类/配置类/DbContext + 分页条件扩展 API）细节**：用 azrng-efcore skill
