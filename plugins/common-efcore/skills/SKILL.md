---
name: common-efcore
description: "Common.EFCore 库开发指南。.NET 项目中使用 Common.EFCore 封装 EF Core 的最佳实践与代码模板，涵盖 Repository、UnitOfWork、实体基类、多数据库提供者配置。Keywords: Common.EFCore, EFCore, Repository, UnitOfWork, MySQL, PostgreSQL, SQLite, SQLServer, InMemory, Azrng.EFCore."
---

## 概述

Common.EFCore 是对 EF Core 的二次封装库，提供 Repository 模式、UnitOfWork、实体基类、自动配置扫描和多数据库提供者支持（MySQL/PostgreSQL/SQLite/SQLServer/InMemory）。命名空间：`Azrng.EFCore`。多目标框架：net6.0 ~ net10.0。

**触发关键词**: Common.EFCore, EFCore, Repository, UnitOfWork, BaseRepository, IBaseRepository, IdentityOperatorEntity, BaseDbContext, AddEntityFramework, EfCoreConnectOption, Azrng.EFCore

**适用场景**：
- 使用 Common.EFCore 系列 NuGet 包进行 .NET 数据访问层开发
- 配置数据库连接（MySQL/PostgreSQL/SQLite/SQLServer/InMemory）
- 定义实体、仓库、工作单元模式
- 原生 SQL 查询、分页、事务处理

**不适用场景**：
- 直接使用原生 EF Core（不使用 Common.EFCore 封装）
- 非 .NET 项目
- Dapper 或其他 ORM 框架

## 前置条件

```bash
# 核心包（必须）
dotnet add package Common.EFCore

# 按需选择数据库提供者包（选一个）
dotnet add package Common.EFCore.MySQL          # MySQL (Pomelo)
dotnet add package Common.EFCore.PostgresSql    # PostgreSQL (Npgsql)
dotnet add package Common.EFCore.SQLite         # SQLite
dotnet add package Common.EFCore.SQLServer      # SQL Server
dotnet add package Common.EFCore.InMemory       # 内存数据库（测试用）
```

## 核心概念

### 一、实体基类（选择继承）

```csharp
using Azrng.EFCore.Entities;

// 仅主键（long 类型雪花 ID）
public class Category : IdentityBaseEntity
{
    public string Name { get; set; }
}

// 主键 + 操作人信息（Creator, CreateTime, Updater, UpdateTime）
public class User : IdentityOperatorEntity
{
    public string UserName { get; set; }
    // SetCreator(name), SetUpdater(name) 设置操作人和时间
}

// 主键 + 操作人 + 状态（Deleted, Disabled）
public class Order : IdentityOperatorStatusEntity
{
    public string OrderNo { get; set; }
    // SetDeleted(name), SetDisabled(true, name) 设置状态
}
```

**关键点**：
- `IdentityBaseEntity` 构造函数自动通过 `IdHelper.GetLongId()` 生成雪花 ID
- 所有泛型版本 `IdentityBaseEntity<TKey>` 支持 `long` 以外的主键类型
- `SetCreator(name, dateTime?, setUpdater?)` 中 `setUpdater` 默认 true（同时设置 Updater）

### 二、实体类型配置（Fluent API）

```csharp
using Azrng.EFCore.EntityTypeConfigurations;
using Microsoft.EntityFrameworkCore.Metadata.Builders;

// 根据实体基类选择对应配置基类
public class UserTypeConfiguration : EntityTypeConfigurationIdentityOperator<User>
{
    public override void Configure(EntityTypeBuilder<User> builder)
    {
        base.Configure(builder); // 必须调用，配置表名(小写)、主键、操作人字段
        builder.Property(x => x.UserName).HasMaxLength(50).HasComment("用户名");
    }
}

// 状态实体用 EntityTypeConfigurationIdentityOperatorStatus
public class OrderConfiguration : EntityTypeConfigurationIdentityOperatorStatus<Order>
{
    public override void Configure(EntityTypeBuilder<Order> builder)
    {
        base.Configure(builder); // 配置主键、操作人字段、Deleted/Disabled字段
        builder.Property(x => x.OrderNo).HasMaxLength(32).HasComment("订单号");
    }
}
```

**配置基类选择**：

| 实体基类 | 配置基类 | 自动配置内容 |
|---------|---------|------------|
| `IdentityBaseEntity` | `EntityTypeConfigurationIdentity<T>` | 表名(小写)、主键(Id, maxlength=36) |
| `IdentityOperatorEntity` | `EntityTypeConfigurationIdentityOperator<T>` | 上述 + Creator/Updater/CreateTime/UpdateTime |
| `IdentityOperatorStatusEntity` | `EntityTypeConfigurationIdentityOperatorStatus<T>` | 上述 + Deleted/Disabled |

**PostgreSQL 特殊行为**：
- 自动配置 Schema（通过 `EfCoreGlobalConfig.Schema`）
- 支持 snake_case 命名（`EFCore.NamingConventions`）
- DateTime 列默认使用 `timestamp without time zone`（`IsUnTimeZoneDateTime` 扩展）

### 三、DbContext 定义

```csharp
using Azrng.EFCore.PostgresSql; // 按提供者选择命名空间

public class AppDbContext : BaseDbContext
{
    public AppDbContext(DbContextOptions options) : base(options) { }
}
```

**BaseDbContext 自动行为**（所有提供者）：
- 扫描非 Microsoft/System 程序集中所有 `IEntity` 实现类
- 自动应用所有 `IEntityTypeConfiguration<T>` 配置
- 无需手动 `DbSet<T>` 属性（通过 Repository 访问）

**SQLServer 特殊**：扫描 `IdentityBaseEntity` 而非 `IEntity`。

### 四、DI 注册（按数据库选择）

#### PostgreSQL

```csharp
using Microsoft.Extensions.DependencyInjection; // 扩展方法所在命名空间

// 使用默认 BaseDbContext
services.AddEntityFramework(option =>
{
    option.ConnectionString = "Host=localhost;Port=5432;Database=mydb;Username=postgres;Password=xxx";
    option.WorkId = 1;
    option.IsSnakeCaseNaming = true; // 默认 true，启用 snake_case 命名
    option.Schema = "public";         // 可选，PostgreSQL schema
});

// 使用自定义 DbContext
services.AddEntityFramework<AppDbContext>(option =>
{
    option.ConnectionString = "...";
    option.WorkId = 1;
});

// 工厂模式（多租户等场景）
services.AddEntityFrameworkFactory<AppDbContext>(option =>
{
    option.ConnectionString = "...";
});
```

#### MySQL

```csharp
services.AddEntityFramework<AppDbContext>(option =>
{
    option.ConnectionString = "Server=localhost;Database=mydb;User=root;Password=xxx;";
    option.WorkId = 1;
});

// 可选：额外 MySQL 配置
services.AddEntityFramework<AppDbContext>(option => { option.ConnectionString = "..."; },
    builder => { /* MySqlDbContextOptionsBuilder 配置 */ },
    (provider, options) => { /* 额外 DbContextOptions 配置 */ });
```

#### SQLite

```csharp
services.AddEntityFramework<AppDbContext>(option =>
{
    option.ConnectionString = "Data Source=mydb.db";
    option.WorkId = 1;
});
```

#### SQL Server

```csharp
services.AddEntityFramework<AppDbContext>(option =>
{
    option.ConnectionString = "Server=localhost;Database=mydb;User Id=sa;Password=xxx;";
    option.WorkId = 1;
});
```

#### InMemory（测试）

```csharp
services.AddEntityFramework<AppDbContext>("TestDb", workId: 1);
// 或
services.AddEntityFramework("TestDb"); // 使用默认 BaseDbContext
```

#### 单独注册 UnitOfWork

```csharp
services.AddUnitOfWork<AppDbContext>(); // 注册 IUnitOfWork<AppDbContext>
```

### 五、EfCoreConnectOption 配置项

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `ConnectionString` | string | - | 数据库连接字符串（必填） |
| `WorkId` | int | 随机 1-1024 | 雪花 ID WorkerId |
| `IsSnakeCaseNaming` | bool | true | PostgreSQL snake_case 命名 |
| `UseOldUpdateColumn` | bool | false | 兼容旧列名（creater/modifyer/modify_time） |
| `Schema` | string | null | PostgreSQL schema |

## 使用模式

### Repository CRUD

```csharp
public class UserService
{
    private readonly IBaseRepository<User> _repo;
    private readonly IUnitOfWork<AppDbContext> _uow;

    public UserService(IBaseRepository<User> repo, IUnitOfWork<AppDbContext> uow)
    {
        _repo = repo;
        _uow = uow;
    }

    // 查询
    public async Task<User> GetByIdAsync(long id) => await _repo.GetByIdAsync(id);
    public async Task<User> GetByNameAsync(string name) =>
        await _repo.GetAsync(x => x.UserName == name);
    public async Task<List<User>> GetActiveListAsync() =>
        await _repo.GetListAsync(x => !x.Disabled);
    public async Task<bool> ExistsAsync(string name) =>
        await _repo.AnyAsync(x => x.UserName == name);
    public async Task<int> CountAsync() => await _repo.CountAsync();

    // 分页
    public async Task<GetQueryPageResult<User>> GetPageAsync(GetPageSortRequest request) =>
        await _repo.GetPageListAsync(_repo.EntitiesNoTacking.Where(x => !x.Disabled), request);

    // 新增
    public async Task<int> AddAsync(User user)
    {
        user.SetCreator("admin"); // 设置创建人和时间
        await _repo.AddAsync(user, submit: true); // submit: true 自动 SaveChanges
    }

    // 修改
    public async Task<int> UpdateAsync(User user)
    {
        user.SetUpdater("admin");
        return await _repo.UpdateAsync(user, submit: true);
    }

    // 条件更新（NET7-9）
    public async Task<int> BatchUpdateAsync(string newName)
    {
        return await _repo.UpdateAsync(
            x => x.UserName == "old",
            x => x.SetProperty(x => x.UserName, newName));
    }

    // 条件更新（NET10+）
    public async Task<int> BatchUpdateNet10Async(string? newName, string? newEmail)
    {
        return await _repo.UpdateAsync(
            x => x.UserName == "old",
            s => s.SetPropertyIfNotNullOrWhiteSpace(x => x.UserName, newName)
                  .SetPropertyIfNotNull(x => x.Email, newEmail));
    }

    // 删除
    public async Task<int> DeleteAsync(long id)
    {
        var user = await _repo.GetByIdAsync(id);
        return await _repo.DeleteAsync(user, submit: true);
    }
    public async Task<int> DeleteByExpressionAsync() =>
        await _repo.DeleteAsync(x => x.Disabled);
}
```

**`submit` 参数**：`true` = 自动调用 `SaveChangesAsync()`，`false` = 仅标记变更（配合 UnitOfWork 使用）。

### UnitOfWork 事务

```csharp
// 方式一：自动事务（推荐）
await _uow.CommitTransactionAsync(async () =>
{
    await _repo.AddAsync(entity1);
    await _repo.AddAsync(entity2);
    await _uow.SaveChangesAsync();
});

// 方式二：手动事务 Scope
await using var scope = await _uow.BeginTransactionScopeAsync();
try
{
    await _repo.AddAsync(entity);
    await _uow.SaveChangesAsync();
    await scope.CommitAsync();
}
catch
{
    await scope.RollbackAsync();
    throw;
}

// 方式三：通过 GetRepository 动态获取
var orderRepo = _uow.GetRepository<Order>();
await orderRepo.AddAsync(order);
await _uow.SaveChangesAsync();
```

### 原生 SQL 查询

```csharp
// 通过 UnitOfWork
var dataTable = await _uow.SqlQueryDataTableAsync("SELECT * FROM users WHERE id = @p0", id);
var users = await _uow.SqlQueryListAsync<UserDto>("SELECT id, user_name FROM users");
var count = await _uow.ExecuteSqlCommandAsync("UPDATE users SET disabled = true WHERE id = @p0", id);
var scalar = await _uow.ExecuteScalarAsync("SELECT COUNT(*) FROM users");

// NET7+ 强类型 SQL 查询
var results = _uow.SqlQuery<UserDto>($"SELECT * FROM users WHERE user_name = {userName}");

// 通过 DatabaseFacade 扩展
var dt = dbContext.Database.SqlQueryDataTable("SELECT * FROM users");
```

### IQueryable 分页扩展

```csharp
using Azrng.EFCore.Extensions;

// 带总数
var total = new RefAsync<int>();
var list = await _repo.EntitiesNoTacking
    .Where(x => !x.Disabled)
    .ToPageListAsync(1, 10, total);
// total.Value 为总记录数

// 使用 GetPageRequest
var request = new GetPageRequest { PageIndex = 1, PageSize = 10 };
var list2 = await query.ToPageListAsync(request, total);
```

### 条件更新扩展（NET10+）

```csharp
using Azrng.EFCore.Extensions;

await _repo.UpdateAsync(x => x.Id == id, s => s
    .SetPropertyIfTrue(string.IsNullOrEmpty(name) == false,
        x => x.UserName, name)
    .SetPropertyIfNotNullOrWhiteSpace(x => x.Email, email)
    .SetPropertyIfNotNull(x => x.Avatar, avatar)
    .SetPropertyIf(v => v > 0, x => x.Age, age));
```

## API 速查

### IBaseRepository<TEntity> 方法

| 方法 | 说明 |
|------|------|
| `Entities` | IQueryable（跟踪） |
| `EntitiesNoTacking` | IQueryable（不跟踪） |
| `GetByIdAsync(id)` | 按主键查询 |
| `GetAsync(expr, isTracking)` | 条件查单条 |
| `GetListAsync(expr, isTracking)` | 条件查列表 |
| `GetPageListAsync<T>(query, pageReq)` | 分页查询 |
| `AnyAsync(expr?)` | 是否存在 |
| `CountAsync(expr?)` | 计数(int) |
| `CountLongAsync(expr?)` | 计数(long) |
| `AddAsync(entity, submit)` | 新增 |
| `AddAsync(entities, submit)` | 批量新增 |
| `UpdateAsync(entity, submit)` | 修改 |
| `UpdateAsync(expr, setProperty)` | 条件批量修改 |
| `DeleteAsync(entity, submit)` | 删除 |
| `DeleteAsync(expr)` | 条件删除 |
| `DeleteAsync(entities, submit)` | 批量删除 |

### IUnitOfWork 方法

| 方法 | 说明 |
|------|------|
| `GetRepository<TEntity>()` | 获取仓库实例 |
| `SaveChanges()` / `SaveChangesAsync()` | 保存变更 |
| `CommitTransaction(action)` / `CommitTransactionAsync(func)` | 自动事务 |
| `BeginTransactionScope()` / `BeginTransactionScopeAsync()` | 手动事务 |
| `ExecuteSqlCommand(sql, params)` / Async | 执行 SQL |
| `ExecuteScalar(sql, params)` / Async | 执行标量查询 |
| `SqlQueryDataTable(sql, params)` / Async | 查询 DataTable |
| `SqlQueryList<T>(sql, params)` / Async | 查询 List<T> |
| `SqlQuery<T>(sql)` (NET7+) | 强类型 SQL 查询 |

## 完整页面开发步骤

### Step 1：定义实体

```csharp
public class Product : IdentityOperatorStatusEntity
{
    public string Name { get; set; }
    public decimal Price { get; set; }
}
```

### Step 2：定义配置

```csharp
public class ProductConfiguration : EntityTypeConfigurationIdentityOperatorStatus<Product>
{
    public override void Configure(EntityTypeBuilder<Product> builder)
    {
        base.Configure(builder);
        builder.Property(x => x.Name).HasMaxLength(100).HasComment("产品名称");
        builder.Property(x => x.Price).HasPrecision(18, 2).HasComment("价格");
    }
}
```

### Step 3：定义 DbContext

```csharp
public class AppDbContext : BaseDbContext // 用对应提供者的 BaseDbContext
{
    public AppDbContext(DbContextOptions options) : base(options) { }
}
```

### Step 4：DI 注册

```csharp
// Program.cs / Startup.cs
services.AddEntityFramework<AppDbContext>(option =>
{
    option.ConnectionString = Configuration.GetConnectionString("Default");
    option.WorkId = 1;
});
```

### Step 5：使用

```csharp
public class ProductService
{
    private readonly IBaseRepository<Product> _repo;
    private readonly IUnitOfWork<AppDbContext> _uow;

    public ProductService(IBaseRepository<Product> repo, IUnitOfWork<AppDbContext> uow)
    {
        _repo = repo;
        _uow = uow;
    }

    public async Task<int> CreateAsync(string name, decimal price)
    {
        var product = new Product { Name = name, Price = price };
        product.SetCreator("system");
        await _repo.AddAsync(product);
        return await _uow.SaveChangesAsync();
    }
}
```

## 验证清单

- [ ] 选择正确的实体基类（Identity / IdentityOperator / IdentityOperatorStatus）
- [ ] 实体类型配置类继承对应基类并调用 `base.Configure(builder)`
- [ ] DbContext 继承对应提供者的 `BaseDbContext`
- [ ] DI 注册使用正确的 `AddEntityFramework` 扩展方法
- [ ] `EfCoreConnectOption.ConnectionString` 不为空（会抛异常）
- [ ] PostgreSQL 场景按需配置 `Schema` 和 `IsSnakeCaseNaming`
- [ ] 使用 `SetCreator`/`SetUpdater` 设置操作人信息
- [ ] 注意 `submit` 参数：`true` 自动保存，`false` 需手动 `SaveChanges`
- [ ] NET 版本差异：条件更新 API 在 NET7-9 和 NET10 不同

## 参考资源

- [Common.EFCore NuGet](https://www.nuget.org/packages/Common.EFCore)
- [GitHub 源码](https://github.com/azrng/nuget-packages)
- [EF Core 官方文档](https://learn.microsoft.com/ef/core/)
