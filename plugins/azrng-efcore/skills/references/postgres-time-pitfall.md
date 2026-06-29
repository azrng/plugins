# PostgreSQL 时间类型陷阱（核心）

本系列包最常见的崩溃根因。**所有 UPDATE（含"读回再整行写"）都会 500**。

## 症状

写库时抛异常：
```
System.ArgumentException: Cannot write DateTime with Kind=Unspecified to PostgreSQL type
'timestamp with time zone', only UTC is supported.
   at Npgsql... (写入 DateTime 时)
   at Azrng.EFCore.BaseRepository`1.UpdateAsync(...)
```
表现：**新增正常，编辑/更新必崩**，凡是 `UpdateAsync(entity, submit)` 的接口全坏。

## 根因

Npgsql **默认把 `DateTime` 映射为 `timestamptz`（带时区）**。带时区列只接受 `Kind=Utc` 或 `Local` 的值，**拒绝 `Kind=Unspecified`**。而：
- `INSERT`：实体用 `DateTime.UtcNow`（Kind=Utc）→ 能写 → 新增成功。
- `UPDATE`：实体从库读回，Npgsql 把 `timestamptz` 读成 `Kind=Unspecified`，再整行写回 → 触发拒绝 → 崩溃。

包的设计意图是**无时区时间**（`timestamp without time zone` + `DateTime.Now.ToUnspecifiedDateTime()`），三层必须一致，缺一即崩。

## 三层一致性要求

| 层 | 要求 | 怎么做 |
|---|---|---|
| 模型层 | 列类型声明为无时区 | `builder.Property(x => x.X).IsUnTimeZoneDateTime();` |
| 赋值层 | 值 Kind=Unspecified | `DateTime.Now.ToUnspecifiedDateTime()`（`Azrng.Core.Extension`） |
| DDL 层 | 实际列类型无时区 | 迁移脚本/建表用 `timestamp without time zone` |

> **关键**：EF Core 按模型推断列类型，不是按实际 DDL。只改 DDL 不改模型，参数仍按 `timestamptz` 发送 → 依旧崩。模型层必须配 `IsUnTimeZoneDateTime()`。

## 诊断步骤

1. 看异常信息是否含 `timestamp with time zone` + `Kind=Unspecified` → 命中。
2. 确认哪一层漏配：
   - 实体继承 `IdentityOperatorEntity`/`StatusEntity` 并用了对应配置基类 → 模型层已自动配（审计字段）。
   - 实体自声明时间字段（如 `ShowTime`）→ 检查是否 `.IsUnTimeZoneDateTime()`。
   - 实体用空 `IEntity` + 手写 `CreatedAt` → 模型层**未**配，需在 `OnModelCreating` 批量配或每属性配。
3. 查实际列类型：`SELECT column_name, data_type FROM information_schema.columns WHERE table_name='x';` 看是否 `timestamp without time zone`。

## 修复（按场景）

### 场景 1：用了包基类 + 配置类
基类已处理审计字段，只需保证业务时间字段无时区化：
```csharp
public override void Configure(EntityTypeBuilder<Scene> builder)
{
    base.Configure(builder);
    builder.Property(x => x.ShowTime).IsUnTimeZoneDateTime();   // 业务时间手动配
}
```
赋值：`ShowTime = request.ShowTime.ToUnspecifiedDateTime();`

### 场景 2：实体继承空 IEntity + 手写字段（如 CreatedAt）
模型层无人配，需在 DbContext 批量声明。在自定义 DbContext 重写 `OnModelCreating`：
```csharp
protected override void OnModelCreating(ModelBuilder modelBuilder)
{
    base.OnModelCreating(modelBuilder);
    const string t = "timestamp without time zone";
    foreach (var et in modelBuilder.Model.GetEntityTypes())
        foreach (var p in et.GetProperties().Where(p => p.ClrType == typeof(DateTime)))
            p.SetColumnType(t);   // 等价 IsUnTimeZoneDateTime（该扩展只接受 PropertyBuilder<T>）
}
```
赋值改无时区：`CreatedAt = DateTime.UtcNow.ToUnspecifiedDateTime();`
DDL 改列：迁移脚本 `created_at timestamp without time zone ...`

### 场景 3：已有库是 timestamptz
EF 模型配了无时区后，与现有库列类型不一致仍会冲突。需重建库让列变无时区：
- 用 SQL 迁移脚本包（`Azrng.SqlMigration`）：改脚本为 `timestamp without time zone`，删 `app_version_log`（版本记录表，默认名）+ 表让其重跑，或换新库名。
- 或手动 `ALTER TABLE x ALTER COLUMN c TYPE timestamp without time zone;`

## 真实案例（电影管理系统）

电影管理系统的类别/电影/影厅/员工**所有编辑都 500**。根因：实体继承空 `IEntity`、时间用 `DateTime.UtcNow`、列实际是 `timestamptz`。修复 = 场景 2 + 场景 3：
1. DbContext `OnModelCreating` 把所有 DateTime 列 `SetColumnType("timestamp without time zone")`。
2. 实体时间赋值改 `DateTime.UtcNow.ToUnspecifiedDateTime()`。
3. SceneController 业务时间 `ShowTime = request.ShowTime.ToUnspecifiedDateTime()`。
4. 迁移脚本 `timestamp` → `timestamp without time zone`，删表 + 版本记录表重跑迁移。
验证：4 个编辑接口（category/movie/room/employee）PUT 全部 `isSuccess`。

## 反模式 / 别踩

- ❌ 用 `AppContext.SetSwitch("Npgsql.EnableLegacyTimestampBehavior", true)`：legacy 兼容开关，官方不建议长期用，治标。
- ❌ 只改 DDL 不改模型：EF 按模型发参数，依旧 timestamptz。
- ❌ 实体时间混用 `DateTime.UtcNow`（Utc）与 `DateTime.Now`（Local）：列类型单一，混用易错。统一无时区。
- ❌ 给无时区列传 `Kind=Utc` 值：无时区列虽不校验 Kind，但语义乱；坚持 `ToUnspecifiedDateTime()`。
