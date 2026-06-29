---
name: azrng-efcore
description: Guide for using the Azrng Common.EFCore family of NuGet packages to operate databases in .NET apps. Use when building or modifying data-access code that relies on these packages — installing/injecting the EFCore provider (PostgreSQL, MySQL, SQLite, SQLServer, InMemory), defining entities with the IdentityBaseEntity/IdentityOperatorEntity base classes, calling IBaseRepository CRUD and IUnitOfWork transactions, configuring SQL migrations, or diagnosing PostgreSQL timestamp errors like "Cannot write DateTime with Kind=Unspecified to timestamp with time zone".
---

# Azrng EFCore (Common.EFCore) 数据访问指南

指导如何用 `Common.EFCore` 系列包在 .NET 项目中操作数据库（仓储 / 工作单元 / 迁移）。

## 包与适用范围

`Common.EFCore`（基础包）+ 按数据库选一个 provider 包。所有 provider 共享同一套 `IBaseRepository<T>` / `IUnitOfWork` 抽象，provider 包只负责注入与底层驱动。

| 数据库 | Provider 包 | 命名空间 | 驱动 |
|---|---|---|---|
| PostgreSQL | `Common.EFCore.PostgresSql` | `Azrng.EFCore.PostgresSql` | Npgsql |
| MySQL | `Common.EFCore.MySQL` | `Azrng.EFCore.MySQL` | Pomelo |
| SQLite | `Common.EFCore.SQLite` | `Azrng.EFCore.SQLite` | Microsoft.Data.Sqlite |
| SQLServer | `Common.EFCore.SQLServer` | `Azrng.EFCore.SQLServer` | Microsoft.Data.SqlClient |
| 内存库(测试) | `Common.EFCore.InMemory` | `Azrng.EFCore.InMemory` | EFCore.InMemory |

> 包名注意：实际 NuGet 包 id 是 `Common.EFCore.PostgresSql`（非 PostgreSQL），按上表原样引用。

## 核心工作流（5 步）

### 1. 安装包

数据访问项目（含 DbContext 的项目）引用：基础包 `Common.EFCore` + 对应 provider 包。实体所在项目引用 `Common.EFCore`（取基类/时间扩展）即可。

```xml
<!-- EntityFrameworkal 项目 -->
<PackageReference Include="Common.EFCore" Version="1.7.0" />
<PackageReference Include="Common.EFCore.PostgresSql" Version="1.7.0" />
<!-- IDomain 项目（仅实体） -->
<PackageReference Include="Common.EFCore" Version="1.7.0" />
```

### 2. 注入（Program.cs）

provider 包的 `AddEntityFramework<TDbContext>` 扩展在 `Microsoft.Extensions.DependencyInjection` 命名空间下，自动注册 DbContext + `IBaseRepository<T>` + 非泛型 `IUnitOfWork`。**仅当**要用泛型 `IUnitOfWork<TDbContext>`（多上下文场景）时才追加 `.AddUnitOfWork<TDbContext>()`（来自 `Azrng.EFCore` 基础包）。

```csharp
using Azrng.EFCore;                       // AddUnitOfWork（仅泛型版本需要）
// 按数据库引入 provider 命名空间（AddEntityFramework<T> 来自它）
// PostgreSQL 无需显式 using（扩展在 Microsoft.Extensions.DependencyInjection）

builder.Services.AddEntityFramework<AppDbContext>(config =>
{
    config.ConnectionString = builder.Configuration.GetConnectionString("Default")!;
    config.Schema = "public";             // PostgreSQL schema；其它库可留空
    config.WorkId = 1;                    // 分布式 Id 生成机器号
    config.IsSnakeCaseNaming = true;      // 是否蛇形命名（默认 true）
    config.UseOldUpdateColumn = false;    // 是否用旧字段名 creator/modifyer/modify_time
});
// 多数场景到此即可，注入 IUnitOfWork 直接用。多 DbContext 时才追加：
// .AddUnitOfWork<AppDbContext>();
```

> 自定义 DbContext 时重写 `OnModelCreating`，调 `ApplyConfigurationsFromAssembly(Assembly.GetExecutingAssembly())` 扫描本程序集（EntityFramework 层）的 `*Etc` 配置类；加 `HasDefaultSchema(...)` 设默认 schema。详见 references/entities-and-context.md。

### 3. 定义实体

优先用包提供的基类，自动带主键（long，IdHelper 雪花 ID）和审计字段。基类无参构造函数已自动 `Id = IdHelper.GetLongId()`，业务实体只需在构造函数里 `SetCreator` 填审计信息：

```csharp
using Azrng.EFCore.Entities;
using Coldairarrow.Util;        // IdHelper
using Azrng.Core.Extension;    // ToUnspecifiedDateTime

public class User : IdentityOperatorStatusEntity   // Id+审计+软删除/禁用
{
    public string Account { get; set; } = string.Empty;

    public User()
    {
        Id = IdHelper.GetLongId();   // 可省略（基类已设），显式写更清晰
        SetCreator("system");
    }

    public User(string account) : this()   // 链式调无参构造
    {
        Account = account;
    }
}
```

> 配套在 EntityFramework 层写 `{Entity}Etc.cs` 配置类（继承包的配置基类 `EntityTypeConfigurationIdentityOperatorStatus<TEntity, TKey>`）+ DbContext 用 `ApplyConfigurationsFromAssembly` 扫描，完整套路见 references/entities-and-context.md。

**时间字段统一用无时区值**：`DateTime.Now.ToUnspecifiedDateTime()`，配合 `IsUnTimeZoneDateTime()` 列声明。完整基类对照与选择见 references/entities-and-context.md。

### 4. CRUD（注入 IBaseRepository<T>）

```csharp
public class UserService
{
    private readonly IBaseRepository<User> _repo;
    public UserService(IBaseRepository<User> repo) => _repo = repo;

    public Task<User?> GetAsync(long id) => _repo.GetAsync(x => x.Id == id);
    public Task AddAsync(User user) => _repo.AddAsync(user, submit: true);   // submit=true 立即保存
    public Task<List<User>> ActiveAsync() => _repo.GetListAsync(x => !x.Deleted);
    public Task<bool> ExistsAsync(string account) => _repo.AnyAsync(x => x.Account == account);
}
```

> `AddAsync/UpdateAsync/DeleteAsync(entity, submit)` 第二参 `submit=false` 时不立即保存，配合工作单元统一提交。完整 API（查询/分页/批量更新/原生 SQL）见 references/repository-and-unitofwork.md。

### 5. 事务（注入 IUnitOfWork）

多写操作原子化用工作单元，**推荐显式作用域**（Dispose 自动回滚未提交事务）：

```csharp
await using var scope = await _unitOfWork.BeginTransactionScopeAsync();
try {
    await _orderRep.AddAsync(order);
    await _itemRep.AddRangeAsync(items);
    await scope.CommitAsync();
} catch { await scope.RollbackAsync(); throw; }
```

三种事务方式对比见 references/repository-and-unitofwork.md。

## 分页与条件查询扩展（常用）

列表查询不要手写 `CountAsync()` + `Skip().Take()`，用框架的分页/条件扩展。扩展分属两个命名空间，按需 `using`。

**条件筛选**（`Azrng.Core.Extension`，`using Azrng.Core.Extension;`）——替代手写 `if (...) query = query.Where(...)`：

| 扩展 | 用途 |
|---|---|
| `.WhereIfNotNullOrWhiteSpace(string? value, predicate)` | 值非空/非空白才 Where（列表筛选最常用） |
| `.WhereIfNotNull<T,F>(F? value, predicate)` | 值非 null 才 Where（值类型/对象筛选） |
| `.WhereIfTrue(bool condition, predicate)` / `.QueryableWhereIf(...)` | 任意布尔条件才 Where |
| `.WhereAny(params predicates)` | 多条件 OR 查询 |

**分页**（`Azrng.EFCore.Extensions`，`using Azrng.EFCore.Extensions;`）——一次完成 Count + Skip/Take：

```csharp
// 推荐：传 GetPageRequest + RefAsync<int> 接收总数，内部一次 Count + 分页
var total = new RefAsync<int>();
var list = await query.ToPageListAsync(request, total);   // request: GetPageRequest

// 也可只取一页、不要总数：
var page  = await query.ToPageListAsync(request);          // 不算 total
var page2 = await query.ToPageListAsync(pageIndex, pageSize);
```

> `ToPageListAsync` 来自 `Common.EFCore`（`Azrng.EFCore.Extensions`）；`PagedBy(GetPageRequest)` 只分页不算总数（来自 `Azrng.Core.Extension`），用于已单独算过总数的场景。

**分页结果模型**（`Azrng.Core.Results`，`using Azrng.Core.Results;`）——`GetQueryPageResult<T>`，含 `Rows`(List<T>) + `PageInfo`(PageIndex/PageSize/Total/TotalPage)：

```csharp
// request 继承 GetPageRequest（自带 PageIndex/PageSize，using Azrng.Core.Requests）
public async Task<GetQueryPageResult<ProductDto>> GetListAsync(ProductListRequest request)
{
    var total = new RefAsync<int>();
    var list = await _repo.EntitiesNoTacking.Where(p => !p.Deleted)
        .WhereIfNotNullOrWhiteSpace(request.Name, p => p.Name.Contains(request.Name!))
        .OrderByDescending(p => p.CreateTime)
        .Select(p => new ProductDto { /* ... */ })
        .ToPageListAsync(request, total);

    return new GetQueryPageResult<ProductDto>(list, new GetQueryPageResult(request, total));
}
```

> `RefAsync<T>`（`using Azrng.Core.CommonDto;`）有到 `T` 的隐式转换，`new GetQueryPageResult(request, total)` 里 `RefAsync<int>` 可直接当 `long totalCount` 用。分页在 AppService 的整体编排（含全局返回包装）见 onion-architecture skill「分页查询最佳实践」。

## SQL 脚本迁移（Azrng.SqlMigration）

数据库 schema 变更用 SQL 脚本版本化管理（不走 EF Core 的 Code-First Migrations）。装 `Azrng.SqlMigration` 包，应用启动时自动按版本顺序执行未应用的脚本，已执行的记在版本日志表、不重复跑。

**安装**（Service 项目）：
```bash
dotnet add package Azrng.SqlMigration
```

**注册**（Program.cs）：`AddSqlMigrationService(名字, 配置)` 链 `.AddAutoMigration()`（启动自动执行）：
```csharp
using Azrng.SqlMigration;
using Npgsql;

var connectionString = builder.Configuration.GetConnectionString("DefaultConnection")!;
var migrationSqlPath = Path.Combine(builder.Environment.ContentRootPath, "MigrationSql");

builder.Services.AddSqlMigrationService("default", config =>
{
    config.Schema = "public";                  // 数据库 schema
    config.VersionPrefix = string.Empty;       // SQL 文件版本前缀（默认 "version"）
    config.SqlRootPath = migrationSqlPath;     // SQL 脚本目录（Service/MigrationSql）
    config.ConnectionBuilder = _ => new NpgsqlConnection(connectionString);
}).AddAutoMigration();                         // ← 启动时自动跑未应用的脚本
```

**SQL 脚本约定**：放 `Service/MigrationSql/`，文件名 = `VersionPrefix + 版本号 + 描述.sql`（如 `1.0.0_init.sql`、`1.1.0_add_user_phone.sql`），按版本号顺序执行。

> 已应用的脚本**不可修改**（版本日志已记录其版本）——改结构就新增一个更高版本的脚本。多库场景调多次 `AddSqlMigrationService(不同名字, ...)`，各自独立版本管理。

## 决策指引（AI 必读）

- **选 provider**：按目标数据库选包，注入方式几乎一致（仅连接串与可选 builder 委托不同）。对照表见 references/providers.md。
- **DbContext 怎么扫描配置类**：继承普通 `DbContext`，在 `OnModelCreating` 里 `modelBuilder.ApplyConfigurationsFromAssembly(Assembly.GetExecutingAssembly())` 扫描本程序集（EntityFramework 层）的 `{Entity}Etc.cs` 配置类；再 `modelBuilder.HasDefaultSchema(...)` 设默认 schema。
- **软删除**：用 `IdentityOperatorStatusEntity`（带 `Deleted`/`Disabled`），查询手动加 `!x.Deleted` 过滤（包不自动全局过滤）。
- **遇到 PostgreSQL 时间报错**：先看 references/postgres-time-pitfall.md —— 这是本系列包最常见的崩溃根因，三层（模型/赋值/DDL）必须一致。

## 关键陷阱（高频）

**PostgreSQL `Cannot write DateTime with Kind=Unspecified to timestamp with time zone`** —— 导致所有 UPDATE（含读回再写）崩溃。根因：Npgsql 默认把 `DateTime` 当 `timestamptz`，而实体时间值是 Unspecified。**三层必须一致**：
1. 模型层：`builder.Property(x => x.CreateTime).IsUnTimeZoneDateTime();`
2. 赋值层：`DateTime.Now.ToUnspecifiedDateTime()`
3. DDL 层：迁移脚本列用 `timestamp without time zone`

诊断与完整修复步骤见 references/postgres-time-pitfall.md。
