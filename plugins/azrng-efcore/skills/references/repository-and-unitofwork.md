# Repository 与 UnitOfWork API

## 目录
1. IBaseRepository 查询方法
2. IBaseRepository 操作方法
3. 批量条件更新（.NET 10+）
4. UnitOfWork 事务（三种方式）
5. 原生 SQL
6. 分页

---

## 1. IBaseRepository 查询方法

命名空间 `Azrng.EFCore`。注入 `IBaseRepository<TEntity> where TEntity : IEntity`。

| 方法 | 说明 |
|---|---|
| `Entities` | 可追踪 IQueryable |
| `EntitiesNoTacking` | 不追踪 IQueryable（只读性能优） |
| `GetByIdAsync(object id)` | 按主键查 |
| `GetAsync(predicate, isTracking=false)` | 条件查单个（默认不追踪） |
| `GetListAsync(predicate, isTracking=false)` | 条件查列表 |
| `GetPageListAsync<T>(IQueryable<T> query, GetPageSortRequest vm)` | IQueryable 分页 |
| `AnyAsync(predicate?)` | 是否存在 |
| `CountAsync(predicate?)` / `CountLongAsync(predicate?)` | 计数 |

```csharp
var user = await _repo.GetAsync(x => x.Account == "admin");
var actives = await _repo.GetListAsync(x => !x.Deleted);
var exists = await _repo.AnyAsync(x => x.Email == email);
// 自定义 LINQ（追踪/排序/连接）
var q = _repo.Entities.Where(x => x.IsValid).OrderByDescending(x => x.CreateTime);
```

## 2. IBaseRepository 操作方法

| 方法 | 说明 |
|---|---|
| `AddAsync(entity, submit=false)` | 添加；`submit=true` 立即保存 |
| `AddAsync(entities, submit=false)` | 批量添加 |
| `UpdateAsync(entity, submit=false)` | 更新整实体 |
| `UpdateAsync(entities, submit=false)` | 批量更新 |
| `UpdateAsync(predicate, setter)` | 条件批量更新（见 §3） |
| `DeleteAsync(entity, submit=false)` | 删除 |
| `DeleteAsync(entities, submit=false)` | 批量删除 |
| `DeleteAsync(predicate)` | 按条件删除（查后删，自动保存） |

> `submit` 默认 false：不立即保存，用于工作单元内多操作后统一提交。独立操作记得传 `submit: true`。

```csharp
await _repo.AddAsync(user, submit: true);              // 立即落库
await _repo.UpdateAsync(user, submit: true);
await _repo.DeleteAsync(x => x.Id == id);              // 条件删除自带保存
```

## 3. 批量条件更新（.NET 10+）

`UpdateAsync(predicate, Action<UpdateSettersBuilder<T>>)`，链式 `SetProperty*`：

```csharp
// 仅当值不为 null 才更新
await _repo.UpdateAsync(
    x => x.Id == id,
    x => x.SetPropertyIfNotNull(u => u.Email, email)
         .SetPropertyIfNotNull(u => u.Phone, phone));

// 字符串非空白才更新 + 无条件更新
await _repo.UpdateAsync(
    x => x.Id == id,
    x => x.SetPropertyIfNotNullOrWhiteSpace(u => u.UserName, name)
         .SetProperty(u => u.UpdateTime, DateTime.Now.ToUnspecifiedDateTime()));
```

| 方法 | 条件 |
|---|---|
| `SetProperty(prop, value)` | 无条件 |
| `SetPropertyIfTrue(cond, prop, value)` | cond 为 true |
| `SetPropertyIfNotNull(prop, value)` | value 非 null（引用类型） |
| `SetPropertyIfNotNullOrWhiteSpace(prop, value)` | 字符串非空白 |
| `SetPropertyIf(Func<object,bool>, prop, value)` | 自定义条件 |

## 4. UnitOfWork 事务（三种方式）

注入 `IUnitOfWork`（或 `IUnitOfWork<TDbContext>`，需 `AddUnitOfWork<T>()`）。

### 方式 1：Lambda（简单场景）
```csharp
await _unitOfWork.CommitTransactionAsync(async () =>
{
    await _orderRep.AddAsync(order);
    await _itemRep.AddAsync(item);
});   // 异常自动回滚并抛出
```

### 方式 2：显式作用域（推荐）
```csharp
await using var scope = await _unitOfWork.BeginTransactionScopeAsync();
try
{
    await _orderRep.AddAsync(order);
    await _itemRep.AddAsync(item);
    await scope.CommitAsync();
}
catch { await scope.RollbackAsync(); throw; }
// 未提交即 Dispose 会自动回滚
```

### 方式 3：手动事务
```csharp
await using var tran = await _unitOfWork.GetDatabase().BeginTransactionAsync();
try {
    await _orderRep.AddAsync(order);
    await _unitOfWork.SaveChangesAsync();
    await tran.CommitAsync();
} catch { await tran.RollbackAsync(); throw; }
```

> 方式 1/2 内部不自动 SaveChanges，业务侧要 `AddAsync(..., submit:false)` 后调 `_unitOfWork.SaveChangesAsync()`，或各 Add 传 `submit:true`。

## 5. 原生 SQL（IUnitOfWork）

| 方法 | 说明 |
|---|---|
| `ExecuteSqlCommandAsync(sql, params)` | 执行非查询，返回影响行数 |
| `ExecuteScalarAsync(sql, params)` | 首行首列 |
| `SqlQuery<T>(FormattableString)` | 标量查询（.NET 7+） |
| `SqlQueryDataTableAsync(sql, params)` | 返回 DataTable |
| `SqlQueryListAsync<T>(sql, params)` | 映射到 List<T>（按属性名） |

```csharp
await _unitOfWork.ExecuteSqlCommandAsync("UPDATE users SET disabled=true WHERE id={0}", id);
var dt = await _unitOfWork.SqlQueryDataTableAsync("SELECT account, create_time FROM users");
```

## 6. 分页

通过 `GetPageSortRequest`/`GetPageRequest`（`Azrng.Core.Requests`）+ `GetPageListAsync`，或对 IQueryable 用 `ToPageListAsync` 扩展：

```csharp
// GetPageRequest 只有 PageIndex/PageSize/Keyword；需要排序用子类 GetPageSortRequest.SortContents
var req = new GetPageSortRequest
{
    PageIndex = 1,
    PageSize = 20,
    SortContents = new[] { new SortContent("CreateTime", SortEnum.Desc) }
};
var page = await _repo.GetPageListAsync(_repo.Entities.Where(x => !x.Deleted), req);
// page.List / page.Total
```
