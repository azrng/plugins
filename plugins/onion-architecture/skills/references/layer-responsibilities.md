# 分层职责详解与代码示例

## 目录
1. 各层职责对照
2. 跨层数据流（一个请求的完整旅程）
3. 各层完整代码示例
4. .csproj 依赖关系

---

## 1. 各层职责对照

### Core（内核，零业务依赖）
**放**：DTO、Request/Response、枚举、常量、通用结果类型。纯 POCO，不引用任何项目，不引用 EFCore/HttpContext 等基础设施。
**不放**：实体、业务逻辑、数据访问、任何 `using` 基础设施包。
**包引用**：仅 `Azrng.Core`（取 `GetPageRequest`/`ResultModel` 等）等基础类库。

```csharp
using Azrng.Core.Requests;   // GetPageRequest

namespace App.Core.Models;

public class ProductDto
{
    public long Id { get; set; }
    public string Name { get; set; } = string.Empty;
    public decimal Price { get; set; }
    public int Status { get; set; }
    public DateTime CreateTime { get; set; }
}

// 分页请求：继承 GetPageRequest，免手写 PageIndex/PageSize 字段
public class ProductListRequest : GetPageRequest
{
    public string? Name { get; set; }
}

public class CreateProductRequest
{
    public string Name { get; set; } = string.Empty;
    public decimal Price { get; set; }
}
```

### IDomain（领域契约层）
**放**：实体（继承 `IdentityOperatorStatusEntity`）。**EFCore 配置类不在这层——放 EntityFramework 层**（见下）。
**不放**：DbContext、业务逻辑、DTO、EFCore 配置类。
**包引用**：`Common.EFCore`（取实体基类 + `IdHelper`）。

实体示例：
```csharp
using Azrng.EFCore.Entities;
using Coldairarrow.Util;

namespace App.IDomain.Entities;

public class Product : IdentityOperatorStatusEntity   // Id + 审计 + 软删除
{
    public Product()
    {
        Id = IdHelper.GetLongId();
        SetCreator("system");
    }

    public string Name { get; set; } = string.Empty;
    public decimal Price { get; set; }
    public int Status { get; set; } = 1;
}
```

### IApplication（应用契约层）
**放**：`I*AppService` 接口，方法签名用 Core 的 DTO。是控制器唯一依赖的契约。
**不放**：实现、仓储、实体直接暴露（接口参数/返回一律 DTO）。
**依赖**：Core、IDomain。
**返回类型**：**全局包装模式**——方法返回 `Task<T>` / `Task<GetQueryPageResult<T>>`，**不出现 `IResultModel`**。

```csharp
using Azrng.Core.Results;            // GetQueryPageResult<T>
using App.Core.Models;

namespace App.IApplication.Product;

public interface IProductAppService
{
    Task<GetQueryPageResult<ProductDto>> GetListAsync(ProductListRequest request);  // 分页查询
    Task<ProductDto> GetAsync(long id);          // 成功返 DTO，资源不存在由实现抛 NotFoundException
    Task<long> CreateAsync(CreateProductRequest request);   // 成功返 id，校验失败由实现抛 ParameterException
    Task DeleteAsync(long id);                    // 无返回数据
}
```

### Application（应用实现层）
**放**：`*AppService` 实现，承担**用例编排**（接 DTO → 调领域服务/仓储/适配器 → 返回 DTO）、实体↔DTO 映射、事务编排。**可注入 `IBaseRepository<T>` / `IUnitOfWork` 做数据访问**（并非 AppService 独占——DomainService 也会注入仓储）。实现类标 `IScopedDependency` 触发自动注册。
**不放**：HTTP 概念、`HttpContext`、`Ok()`、路由。
**依赖**：IApplication（+ 间接 Domain/EntityFramework）。
**包引用**：核心包经依赖链**传递可达**，多数无需在 Application.csproj 显式声明：
- **传递可达**（经 `Application → IApplication → IDomain → Common.EFCore → Azrng.Core / Microsoft.EntityFrameworkCore`，无需显式引）：`IBaseRepository`/`IUnitOfWork`/`ToPageListAsync`（Common.EFCore）、`FirstOrDefaultAsync`/`CountAsync`/`ToListAsync`（Microsoft.EntityFrameworkCore）、`IScopedDependency`/`ParameterException`/`NotFoundException`/`WhereIfNotNullOrWhiteSpace`/`GetQueryPageResult`/`RefAsync`/`ToUnspecifiedDateTime()`（Azrng.Core）。
  > 实测 `MovieManage.Application` 只显式引 `Azrng.Core`（可选，为注释清晰）、`JwtBearer`、`DistributeLock.Core`；synyi 的 Application 甚至一个 Azrng 包都不显式引（全靠传递）。
- **按需显式引**（独立功能包，不在传递链，AppService 真用到才加）：
  - `Azrng.AspNetCore.Authentication.JwtBearer` — 登录/鉴权 AppService 注入 `IBearerAuthService` 生成 token
  - `Azrng.DistributeLock.Core` — 并发控制 AppService 注入 `ILockProvider`

**核心约定（全局包装模式）**：成功直接 `return` 业务对象；**业务校验/规则失败 `throw new ParameterException(msg)`**；资源不存在 `NotFoundException.ThrowIfNull(entity, "...")`。**不要手写 `ResultModel.Success/Error`**（那是历史写法）。

```csharp
using Azrng.Core.CommonDto;            // RefAsync
using Azrng.Core.DependencyInjection;  // IScopedDependency
using Azrng.Core.Exceptions;           // ParameterException, NotFoundException
using Azrng.Core.Extension;            // WhereIfNotNullOrWhiteSpace
using Azrng.Core.Results;              // GetQueryPageResult
using Azrng.EFCore;                    // IBaseRepository
using Azrng.EFCore.Extensions;         // ToPageListAsync
using Microsoft.EntityFrameworkCore;
using App.Core.Models;
using App.IApplication.Product;
using App.IDomain.Entities;

namespace App.Application.Product;

// IScopedDependency 触发约定式自动注册（RegisterBusinessServices 扫描），无需手写 AddScoped
public class ProductAppService : IScopedDependency, IProductAppService
{
    private readonly IBaseRepository<Product> _productRepository;

    public ProductAppService(IBaseRepository<Product> productRepository)
        => _productRepository = productRepository;

    // 分页查询：链式 WhereIfNotNullOrWhiteSpace + ToPageListAsync（一次 Count+分页），返回 GetQueryPageResult<Dto>
    public async Task<GetQueryPageResult<ProductDto>> GetListAsync(ProductListRequest request)
    {
        var total = new RefAsync<int>();
        var list = await _productRepository.EntitiesNoTacking.Where(p => !p.Deleted)
            .WhereIfNotNullOrWhiteSpace(request.Name, p => p.Name.Contains(request.Name!))
            .OrderByDescending(p => p.CreateTime)
            .Select(p => new ProductDto
            {
                Id = p.Id, Name = p.Name, Price = p.Price,
                Status = p.Status, CreateTime = p.CreateTime
            })
            .ToPageListAsync(request, total);

        return new GetQueryPageResult<ProductDto>(list, new GetQueryPageResult(request, total));
    }

    public async Task<ProductDto> GetAsync(long id)
    {
        var product = await _productRepository.EntitiesNoTacking.FirstOrDefaultAsync(p => p.Id == id);
        NotFoundException.ThrowIfNull(product, "商品不存在");   // 资源不存在 → 由异常中间件映射成 404
        return new ProductDto { Id = product.Id, Name = product.Name, Price = product.Price, Status = product.Status };
    }

    public async Task<long> CreateAsync(CreateProductRequest request)
    {
        // 业务校验下沉到此处，不在控制器；失败抛 ParameterException → 由异常中间件映射成 400
        if (request.Price < 0)
            throw new ParameterException("价格不能为负");

        var product = new Product { Name = request.Name, Price = request.Price };
        await _productRepository.AddAsync(product, submit: true);   // submit:true 立即提交
        return product.Id;   // 成功 → 全局包装过滤器自动包成 ResultModel<long>(success)
    }

    public async Task DeleteAsync(long id)
    {
        await _productRepository.DeleteAsync(p => p.Id == id);   // 无返回值 → 过滤器包成 ResultModel(true,"成功")
    }
}
```

#### 读取追踪 vs 不追踪（`Entities` / `EntitiesNoTacking`）
- **`EntitiesNoTacking`（默认首选）**：纯查询、列表、详情读取。不进 ChangeTracker，性能好。90% 的查询用这个。
- **`Entities`（带追踪）**：读出来后**还要修改并回写**时才用——先查、改属性、`UpdateAsync` 提交，EF 靠追踪算 diff。读了不改却用 `Entities` 会白白吃追踪开销。

```csharp
// 查询列表 → NoTracking
var list = await _repo.EntitiesNoTacking.Where(x => !x.Deleted).ToListAsync();

// 读出来要改 → 带追踪（或用 GetByIdAsync 后 UpdateAsync）
var entity = await _repo.Entities.FirstOrDefaultAsync(x => x.Id == id);
entity.Status = 0;
await _repo.UpdateAsync(entity, submit: true);
```

#### 返回值与错误处理（全局包装模式）

AppService 方法**统一返回裸 `Task<T>`**（业务对象），由 `Service` 层装配的框架三件套自动包成统一 `ResultModel`。错误通过**抛业务异常**表达（不要返回错误码、不要手写 `ResultModel.Error`）：成功 `return dto;`、资源不存在 `NotFoundException.ThrowIfNull(entity, "...")`、参数/业务校验失败 `throw new ParameterException(msg)`（也可是 `LogicBusinessException`）、无权限 `throw new ForbiddenException(msg)`。

> 业务异常 → 结果映射表、三件套装配、`IResultModel<T>` 迁移期说明见 `SKILL.md → 全局返回包装`。这套要工作，**异常中间件 `app.UseGlobalException()` 必须在 Program.cs 管道最外层装配**，否则抛出的异常会变成裸 500。

需要多步原子写时用 `IUnitOfWork.CommitTransactionAsync`（自动开/提交/回滚事务，传入业务委托）：
```csharp
// 注入 IUnitOfWork；委托内各 AddAsync(..., submit: false) 不单独提交
await _unitOfWork.CommitTransactionAsync(async () =>
{
    await _orderRep.AddAsync(order);          // submit 默认 false
    await _itemRep.AddRangeAsync(items);
});
// 第二个参数可传 IsolationLevel（默认 ReadCommitted）；委托抛异常自动回滚
```

> 需要原生 SQL / `FOR UPDATE` 行锁时（如并发扣库存/抢购），AppService 注入 DbContext 直接用 `_dbContext.Database.BeginTransactionAsync()` + `FromSqlInterpolated`。这是少数 DbContext 可跨层注入 AppService 的合理场景。分页/条件查询扩展（`ToPageListAsync`/`WhereIfNotNullOrWhiteSpace`/`PagedBy` 等）完整签名见 azrng-efcore skill。

### Domain（领域服务层）
**放**：`*DomainService` 实现，封装**可复用的公共领域操作**——被多个 AppService 复用、或承载稳定的多实体领域规则/数据访问的操作（如「发会话消息」「读系统配置」「指标计算」）。**DomainService 可注入 `IBaseRepository<T>` / `IUnitOfWork` 自己读写数据**（Domain 项目依赖 EntityFramework），也可注入 Adapter/缓存等。实现类标 `IScopedDependency` 触发自动注册。
**不放**：HTTP 概念、DTO 映射（那是 AppService 的活）——DomainService 只返回/接收领域对象（Entity/Bo）。
**依赖**：IDomain、EntityFramework、Adapter。
**结对**：接口 `I{X}DomainService` 在 `IDomain/{Module}/`，实现 `{X}DomainService : IScopedDependency, I{X}DomainService` 在 `Domain/{Module}/`（与 AppService 的 IApplication/Application 结对方式一致）。**AppService 注入 `I{X}DomainService` 调用它**。

```csharp
// IDomain/SessionManager/ISessionDomainService.cs —— 接口，返回领域对象（Entity/Bo），不出现 DTO
public interface ISessionDomainService
{
    Task<string> SendSessionMessageAsync(SendSessionMessageBo dto);
    Task<ChatMemoryEntity> GetChatMemoryAsync(string messageId);
}

// Domain/SessionManager/SessionDomainService.cs —— 实现：注入多个仓储，做跨实体的领域编排（自己写库）
public class SessionDomainService : IScopedDependency, ISessionDomainService
{
    private readonly IBaseRepository<ChatSessionEntity> _sessionRepository;
    private readonly IBaseRepository<ChatMessageEntity> _chatMessageRepository;
    public SessionDomainService(IBaseRepository<ChatSessionEntity> sessionRepository,
                                IBaseRepository<ChatMessageEntity> chatMessageRepository)
    { /* ... */ }

    public async Task<string> SendSessionMessageAsync(SendSessionMessageBo dto)
    {
        var sessionId = await StartSessionAsync(...);        // 领域规则：会话不存在才创建
        await _chatMessageRepository.AddAsync(new ChatMessageEntity(...), true);  // 自己写库
        return sessionId;
    }
}

// Application/ConversationService.cs —— AppService 编排：注入并调用 DomainService，做 DTO 映射
public class ConversationService : IConversationAppService
{
    private readonly ISessionDomainService _sessionDomainService;   // 复用的公共操作
    public async Task<SendResultDto> SendAsync(SendRequest req)
    {
        var sessionId = await _sessionDomainService.SendSessionMessageAsync(MapToBo(req));  // 调领域服务
        return new SendResultDto { SessionId = sessionId };                                  // DTO 映射在 AppService
    }
}
```

> **什么时候抽 DomainService**：操作只被一个 AppService 用、不会复用 → 直接写在那个 AppService；**多个 AppService 都要用同一段操作**（参考项目里 `ISystemConfigDomainService` 被 5+ 个 AppService 共用）→ 抽成 DomainService 避免重复。纯 CRUD 项目 Domain 层可空。

### Adapter（外部适配器层）
**放**：外部系统调用的封装——`I{X}Adapter`（领域适配器）实现 + `IXxxHttpClient`（HTTP 客户端）实现。屏蔽第三方 API / 微服务 / SDK 的 HTTP/协议细节，对内暴露领域语义方法。
**不放**：业务规则、用例编排（那是 AppService/DomainService 的活）；把 HttpClient/URL 直接暴露给业务层。
**依赖**：IDomain（+ 第三方 SDK 包）。`Adapter.csproj` 只引用 `IDomain`。
**结对 + 两层**（复杂外部调用推荐）：
- 领域适配器：接口 `I{X}Adapter` 在 `IDomain/Adapter/`，实现 `{X}Adapter : IScopedDependency, I{X}Adapter` 在 `Adapter/Service/`，方法用 **Bo**（`IDomain/Adapter/{模块}/`）。
- HTTP 客户端：接口 `IXxxHttpClient` 在 `Adapter/HttpWebClient/`，实现 `XxxHttpClient : IScopedDependency, IXxxHttpClient`，用 **Ho**（`Adapter/Ho/{模块}/`），注入 `IHttpHelper` / `IHttpClientFactory` 做真实 HTTP 调用。

```csharp
// IDomain/Adapter/ISmsAdapter.cs —— 接口在 IDomain，用 Bo，不暴露 HttpClient
public interface ISmsAdapter { Task<bool> SendAsync(SendSmsBo bo); }

// Adapter/Service/SmsAdapter.cs —— 实现：标 IScopedDependency，做 Bo→Ho 转换，调下层 HttpClient
public class SmsAdapter : IScopedDependency, ISmsAdapter
{
    private readonly ISmsHttpClient _client;
    public SmsAdapter(ISmsHttpClient client) => _client = client;
    public Task<bool> SendAsync(SendSmsBo bo)
        => _client.SendAsync(new SendSmsRequestHo { Phone = bo.Phone, Content = bo.Content });
}

// Adapter/HttpWebClient/SmsHttpClient.cs —— 真实 HTTP 调用，输入/输出用 Ho
public class SmsHttpClient : IScopedDependency, ISmsHttpClient
{
    private readonly IHttpHelper _httpHelper;
    public SmsHttpClient(IHttpHelper httpHelper) => _httpHelper = httpHelper;
    public Task<bool> SendAsync(SendSmsRequestHo req)
        => _httpHelper.PostAsync<bool>("https://sms.example.com/send", req);
}

// Application/XxxAppService.cs —— 业务层只依赖 IDomain 里的接口
public class XxxAppService
{
    private readonly ISmsAdapter _smsAdapter;   // 依赖接口；外部协议升级只改 Adapter
}
```

> **什么时候用 Adapter**：调用**本系统数据库** → AppService/DomainService 直接注入 `IBaseRepository`；调用**外部系统** → 走 Adapter（业务层依赖 `I{X}Adapter` 接口）。简单外部调用可只用领域适配器一层（直接调通用 `IHttpHelper`），复杂/协议多变时才拆出 `IXxxHttpClient` 层。

### EntityFramework（基础设施-数据）
**放**：`DbContext`、EFCore 配置类（`{Entity}Etc.cs`）、迁移。
**不放**：业务逻辑、实体定义（实体在 IDomain）。
**依赖**：Core、IDomain；包引用 `Common.EFCore` + provider 包。

配置类示例（`{Entity}Etc.cs`，继承配置基类，设表名/列名/查询过滤）：
```csharp
using Azrng.EFCore.EntityTypeConfigurations;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using App.IDomain.Entities;

namespace App.EntityFramework;

public class ProductEtc : EntityTypeConfigurationIdentityOperatorStatus<Product, long>
{
    public override void Configure(EntityTypeBuilder<Product> builder)
    {
        base.Configure(builder);                          // 必调：主键/审计列/时间类型
        builder.ToTable("product");                       // 表名
        builder.HasQueryFilter(x => !x.Deleted);          // 软删除全局过滤
        builder.Property(x => x.Name).HasMaxLength(100).IsRequired().HasComment("商品名称");
        builder.Property(x => x.Price).HasComment("价格");
    }
}
```

DbContext（继承 `DbContext`，`OnModelCreating` 里扫描当前程序集的 Etc 配置）：
```csharp
using System.Reflection;
using Microsoft.EntityFrameworkCore;
using App.IDomain.Entities;

namespace App.EntityFramework;

public class AppDbContext : DbContext
{
    public AppDbContext(DbContextOptions<AppDbContext> options) : base(options) { }
    public DbSet<Product> Products { get; set; }

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.HasDefaultSchema("public");
        modelBuilder.ApplyConfigurationsFromAssembly(Assembly.GetExecutingAssembly());  // 扫描本程序集的 *Etc 配置
        base.OnModelCreating(modelBuilder);
    }
}
```

### Service（入口/组装层）
**放**：`Controllers`、`Program.cs`（DI 装配 + 中间件管道）、`appsettings`、迁移 SQL 脚本、安全/过滤器。
**不放**：EF 查询、业务校验、`IBaseRepository` 注入。
**依赖**：Application（+ Storage/EntityFramework 经传递可达）。

控制器（瘦）——**一行转发** AppService 返回值，不写 `Ok()`、不写 `ResultModel`（全局包装过滤器自动包装）：
```csharp
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using App.Core.Models;
using App.IApplication.Product;

namespace App.Service.Controllers;

[ApiController]
[Authorize]
[Route("api/[controller]")]
public class ProductController(IProductAppService productAppService) : ControllerBase
{
    [HttpGet("list")]
    public Task<GetQueryPageResult<ProductDto>> GetList([FromQuery] ProductListRequest request)
        => productAppService.GetListAsync(request);   // 一行转发，过滤器自动包成 ResultModel

    [HttpGet("{id}")]
    public Task<ProductDto> Get(long id)
        => productAppService.GetAsync(id);

    [HttpPost]
    public Task<long> Create([FromBody] CreateProductRequest request)
        => productAppService.CreateAsync(request);

    [HttpDelete("{id}")]
    public Task Delete(long id)
        => productAppService.DeleteAsync(id);
}
```

Program.cs 装配（全局包装三件套 + 异常中间件 + 自动注册）见 `SKILL.md → 全局返回包装 → Program.cs 装配` 与 `SKILL.md → 依赖注入与中间件装配`。

> 控制器直接转发 AppService 返回的 `Task<T>`，无需 `Ok()` 包装——`CustomResultPackFilter` 自动把 `Task<T>` 的结果包成 `ResultModel<T>`（含 isSuccess/code/data）。错误路径在 AppService 里 `throw new ParameterException(msg)`，由 `app.UseGlobalException()` 兜底。

---

## 2. 跨层数据流（一个 GET 请求的旅程）

```
HTTP GET /api/product/list?name=xx
  │
  ▼
[Service] ProductController.GetList(ProductListRequest)   ← 仅接参数、一行转发
  │  调用接口
  ▼
[Application] ProductAppService.GetListAsync              ← 业务+查询在这里
  │  注入 IBaseRepository<Product>；WhereIfNotNullOrWhiteSpace + ToPageListAsync
  ▼
[EntityFramework] IBaseRepository → DbContext → PostgreSQL   ← 基础设施
  │  返回 Product 实体（带审计字段）
  ▼
[Application] 实体 → ProductDto 映射（剥掉审计字段）   ← 边界转换
  │  返回 GetQueryPageResult<ProductDto>（裸业务对象，非 IResultModel）
  ▼
[Service] 控制器 return GetQueryPageResult<ProductDto>（一行转发）
  │  CustomResultPackFilter 自动包装
  ▼
HTTP 200 { isSuccess:true, code:"200", data:{ rows:[...], pageInfo:{ pageIndex, pageSize, total, totalPage } } }
```

失败路径（如 `CreateAsync` 校验不通过）：AppService `throw new ParameterException("价格不能为负")` → 冒泡穿过控制器 → 被 `app.UseGlobalException()` 捕获 → 映射成 `HTTP 400 { isSuccess:false, code:"400", message:"价格不能为负" }`。

**关键边界**：实体只在 `AppService ↔ DbContext` 之间流动；**出了 AppService 一律是 DTO**。控制器和前端永远看不到实体。

---

## 3. .csproj 依赖关系

```
Core              → (无项目引用)
IDomain           → Core
IApplication      → Core, IDomain
Domain            → IDomain, EntityFramework, Adapter    ← 纯 CRUD 可空，有复用操作则建
Application       → IApplication, Domain
EntityFramework   → Core, IDomain
Service           → Application, Storage
Adapter           → Core, IDomain                         ← 可选
Storage           → Core                                   ← 可选
```

对应 `<ProjectReference>` 示例（Application.csproj，`App` 替换成实际解决方案名）：
```xml
<ItemGroup>
  <ProjectReference Include="..\App.IApplication\App.IApplication.csproj" />
  <ProjectReference Include="..\App.Domain\App.Domain.csproj" />
</ItemGroup>
<ItemGroup>
  <PackageReference Include="Azrng.Core" Version="1.19.0" />
  <!-- 仅当 AppService 需要时才引：JWT 认证、分布式锁等 -->
</ItemGroup>
```

**依赖方向自检**：若发现内层项目（如 Core）要 `using` 外层（如 Application），说明分层错了，立刻停下来纠正。

---

## 4. 完整功能落点速查（新增"订单"功能）

| 步骤 | 文件 | 层 | 内容 |
|---|---|---|---|
| 1 | `Core/Models/OrderDto.cs` | Core | `OrderDto`/`CreateOrderRequest`；列表 Request 继承 `GetPageRequest` |
| 2 | `IDomain/Entities/Order.cs` | IDomain | 实体 + `SetCreator` |
| 3 | `EntityFramework/OrderEtc.cs` | EntityFramework | EFCore 配置类（表名/列名/查询过滤） |
| 4 | `IApplication/Order/IOrderAppService.cs` | IApplication | 接口，返回 `Task<T>` / `Task<GetQueryPageResult<T>>`（全局包装，无 IResultModel） |
| 5 | `Application/Order/OrderAppService.cs` | Application | 实现 `IScopedDependency` + 仓储 + 业务：成功 `return`、失败 `throw ParameterException`、资源不存在 `NotFoundException.ThrowIfNull`、列表用 `ToPageListAsync`+`GetQueryPageResult`（自动注册，免手写 AddScoped） |
| 6 | `Service/Controllers/OrderController.cs` | Service | 瘦控制器，一行转发 `Task<T>`（不写 `Ok()`） |
| 7 | `Service/Program.cs` | Service | 已有 `RegisterBusinessServices("App.*.dll")` + `AddMvcResultPackFilter` + `AddMvcModelVerifyFilter` + `app.UseGlobalException()`，实现 `IScopedDependency` 即自动注册，无需改 |

新增实体在 DbContext 加 `DbSet` + 写 `{Entity}Etc.cs` 配置类，`ApplyConfigurationsFromAssembly` 自动扫描。若用 SQL 脚本迁移，装 `Azrng.SqlMigration` 包 + 加 `Service/MigrationSql/x.x.x.sql`（详见 azrng-efcore「SQL 脚本迁移」）。
