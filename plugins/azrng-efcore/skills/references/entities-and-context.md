# 实体、DbContext 与配置类

## 目录
1. 实体基类继承体系
2. 各基类字段对照
3. 时间字段约定（无时区）
4. DbContext 写法
5. 配置类（EntityTypeConfiguration 基类）
6. ID 生成

---

## 1. 实体基类继承体系

```
IEntity                       （空基类 class，所有实体可继承；非接口）
└─ IdentityBaseEntity         （long 主键，构造时生成雪花 Id）
   └─ IdentityBaseEntity<TKey>
└─ IdentityOperatorEntity     （+ 审计：Creator/CreateTime/Updater/UpdateTime）
   └─ IdentityOperatorEntity<TKey>
└─ IdentityOperatorStatusEntity （+ 状态：Deleted/Disabled）
   └─ IdentityOperatorStatusEntity<TKey>
```

> 命名空间 `Azrng.EFCore.Entities`。`IdentityBaseEntity`/`IdentityOperatorEntity`/`IdentityOperatorStatusEntity`（无泛型）= 其 `<long>` 版本，构造时自动 `Id = IdHelper.GetLongId()`。
> `IdHelper` 来自 `IdHelper` 包（命名空间 `Coldairarrow.Util`），经 `Common.EFCore` 传递引用可达——**实体项目引用 `Common.EFCore` 即可，无需单独装 `IdHelper`**；实体构造一般也不用显式调（基类已设）。同理 `ToUnspecifiedDateTime()`（`Azrng.Core.Extension`）也经 `Common.EFCore → Azrng.Core` 传递可达。

## 2. 各基类字段对照

| 基类 | 主键 | 审计字段 | 状态字段 |
|---|---|---|---|
| `IdentityBaseEntity` | `Id` (long) | — | — |
| `IdentityOperatorEntity` | `Id` | `Creator`, `CreateTime`, `Updater`, `UpdateTime` | — |
| `IdentityOperatorStatusEntity` | `Id` | 同上 | `Deleted` (bool), `Disabled` (bool) |

- `CreateTime` 非空、`UpdateTime` 可空（`DateTime?`）。
- 选型：只需主键→`IdentityBaseEntity`；要追溯创建/修改人→`IdentityOperatorEntity`；要软删除/启禁用→`IdentityOperatorStatusEntity`。

## 3. 时间字段约定（无时区）

包的设计是**无时区时间**：`DateTime.Now.ToUnspecifiedDateTime()`（`Azrng.Core.Extension`），列类型 `timestamp without time zone`（PG）。

赋值辅助方法（实体基类自带，业务直接调）：
```csharp
entity.SetCreator("operator");       // 填 Creator + CreateTime(+Updater/UpdateTime)，时间默认 ToNowDateTime
entity.SetUpdater("operator");       // 仅填 Updater + UpdateTime
entity.SetDeleted("operator");       // Deleted=true + 调 SetUpdater（软删除）
entity.SetDisabled(true, "operator");// Disabled=指定值 + 调 SetUpdater
```

> 自己声明时间字段（非审计字段，如业务 `ShowTime`）也要无时区化：`DateTime.Now.ToUnspecifiedDateTime()`。详见 postgres-time-pitfall.md。

## 4. DbContext 写法

DbContext 放 **EntityFramework 层**，继承普通 `DbContext`，在 `OnModelCreating` 里扫描**本程序集**的 `{Entity}Etc` 配置类（配置类与 DbContext 同在 EntityFramework 程序集，才能被扫到）：
```csharp
using System.Reflection;
using Microsoft.EntityFrameworkCore;

public class AppDbContext : DbContext
{
    public AppDbContext(DbContextOptions<AppDbContext> options) : base(options) { }
    public DbSet<User> Users { get; set; }
    public DbSet<Order> Orders { get; set; }

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.HasDefaultSchema("public");
        modelBuilder.ApplyConfigurationsFromAssembly(Assembly.GetExecutingAssembly());  // 扫描本程序集的 *Etc 配置
        base.OnModelCreating(modelBuilder);
    }
}
```

> 也可继承 `BaseDbContext`（自动应用所有 `IEntityTypeConfiguration`），但本项目约定用上面的显式 `ApplyConfigurationsFromAssembly` + `{Entity}Etc` 配置类放 EntityFramework 层。

## 5. 配置类（EntityTypeConfiguration 基类）

每个实体配一个 `IEntityTypeConfiguration<T>`，继承对应配置基类以复用基类字段配置（主键/审计/列名/时间类型）。

| 配置基类 | 对应实体 | 自动配置 |
|---|---|---|
| `EntityTypeConfigurationIdentity<T>` | `IdentityBaseEntity` | 表名=类名小写、主键、Schema |
| `EntityTypeConfigurationIdentity<T, TKey>` | `IdentityBaseEntity<TKey>` | 同上 |
| `EntityTypeConfigurationIdentityOperator<T, TKey>` | `IdentityOperatorEntity` | + Creator/CreateTime/Updater/UpdateTime（含 `IsUnTimeZoneDateTime`） |
| `EntityTypeConfigurationIdentityOperatorStatus<T, TKey>` | `IdentityOperatorStatusEntity` | + Deleted/Disabled |

命名空间 `Azrng.EFCore.EntityTypeConfigurations`。

配置类命名 `{Entity}Etc.cs`（后缀 **Etc**，不是 `Configuration`），放 **EntityFramework 层**根目录（与 DbContext 同程序集，才能被 `ApplyConfigurationsFromAssembly` 扫到）：
```csharp
using Azrng.EFCore.EntityTypeConfigurations;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using App.IDomain.Entities;

namespace App.EntityFramework;   // ← 放 EntityFramework 层

public class UserEtc : EntityTypeConfigurationIdentityOperatorStatus<User, long>
{
    public override void Configure(EntityTypeBuilder<User> builder)
    {
        base.Configure(builder);   // 必调：主键/审计/列名/时间类型
        builder.ToTable("user");
        builder.HasQueryFilter(x => !x.Deleted);          // 软删除全局过滤
        builder.Property(x => x.Account).IsRequired().HasMaxLength(50).HasComment("账号");
        builder.HasIndex(x => x.Account).IsUnique();
    }
}
```

## 6. ID 生成

- 继承带主键基类时，构造函数自动 `Id = IdHelper.GetLongId()`（雪花 ID，来自 IdHelper 包）。
- `WorkId`（注入时 `config.WorkId` 或 InMemory 的 `workId` 参）是雪花机器号，分布式部署每节点设不同值（默认随机 1-1023）。
- 自增主键：不继承基类、用 `[DatabaseGenerated(DatabaseGeneratedOption.Identity)]` + 自增列。
