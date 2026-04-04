---
name: bootstrap-blazor
description: "BootstrapBlazor 组件库开发指南。.NET Blazor 项目中使用 BootstrapBlazor 的最佳实践与代码模板。Keywords: BootstrapBlazor, Blazor, .NET, Table, Modal, TreeView, Form, Toast, CQRS, RBAC."
---

## 概述

BootstrapBlazor 企业级开发指南，提供在 .NET Blazor Server 项目中使用 BootstrapBlazor 组件库的最佳实践、代码模板和常见模式。涵盖数据表格、模态框、表单验证、树形控件、通知提示等核心组件的完整用法。

**适用场景**：
- 使用 BootstrapBlazor 构建 Blazor Server 应用
- 企业级 RBAC/后台管理系统开发
- CQRS 架构模式下的 CRUD 页面开发
- BootstrapBlazor 组件使用问题排查

**不适用场景**：
- Blazor WebAssembly 客户端独立应用（部分模式不适用）
- 非 BootstrapBlazor 的 Blazor UI 框架
- 纯前端 React/Vue 项目

## 前置条件

```bash
# 安装 BootstrapBlazor NuGet 包
dotnet add package BootstrapBlazor
dotnet add package BootstrapBlazor.FontAwesome

# 可选：PDF 导出支持
dotnet add package BootstrapBlazor.TableExport
dotnet add package BootstrapBlazor.Html2Pdf
```

## 项目配置

### 1. 服务注册（Startup.cs）

```csharp
// 基础注册
services.AddBootstrapBlazor();

// 可选：表格导出和 PDF 服务
services.AddBootstrapBlazorTableExportService();
services.AddBootstrapBlazorHtml2PdfService();
```

### 2. 静态资源引用（App.razor 或 _Host.cshtml）

```html
<!-- CSS -->
<link href="_content/BootstrapBlazor.FontAwesome/css/font-awesome.min.css" rel="stylesheet"/>
<link href="_content/BootstrapBlazor/css/bootstrap.blazor.bundle.min.css" rel="stylesheet"/>
<!-- 主题：Motronic 风格 -->
<link href="_content/BootstrapBlazor/css/motronic.min.css" rel="stylesheet"/>

<!-- JS -->
<script src="_content/BootstrapBlazor/js/bootstrap.blazor.bundle.min.js"></script>
```

### 3. 全局导入（_Imports.razor）

```razor
@using BootstrapBlazor.Components
```

### 4. 根组件配置（Routes.razor）

```razor
<BootstrapBlazorRoot>
    <CascadingAuthenticationState>
        <Router AppAssembly="@typeof(Program).Assembly">
            <Found Context="routeData">
                <AuthorizeView>
                    <Authorized>
                        <CascadingValue Value="routeData">
                            <RouteView RouteData="@routeData" DefaultLayout="@typeof(MainLayout)"/>
                        </CascadingValue>
                        <FocusOnNavigate RouteData="@routeData" Selector="h1"/>
                    </Authorized>
                    <NotAuthorized>
                        <LayoutView Layout="@typeof(LoginLayout)">
                            <Login />
                        </LayoutView>
                    </NotAuthorized>
                </AuthorizeView>
            </Found>
            <NotFound>
                <LayoutView Layout="@typeof(LoginLayout)">
                    <p>页面未找到</p>
                </LayoutView>
            </NotFound>
        </Router>
    </CascadingAuthenticationState>
</BootstrapBlazorRoot>
```

---

## 核心组件模式

### 一、Table 组件（数据表格）

#### 1.1 分页表格 + 搜索（标准 CRUD 页面）

**.razor 文件**：
```razor
<Table @ref="UserTable" TItem="GetUserListResult"
       IsPagination="true" PageItemsSource="new[] {10, 20, 50, 100}"
       IsStriped="true" IsBordered="true"
       ShowToolbar="false" ShowSearch="true" IsMultipleSelect="true"
       ShowExtendButtons="true"
       ShowExtendEditButton="false" ShowExtendDeleteButton="false"
       CustomerSearchModel="@CustomerSearchModel" SearchMode="SearchMode.Top"
       ShowEmpty="true"
       OnQueryAsync="@OnSearchModelQueryAsync"
       OnResetSearchAsync="@OnResetSearchAsync"
       OnDeleteAsync="@OnDeleteAsync">

    <!-- 自定义搜索模板 -->
    <CustomerSearchTemplate>
        @if (context is GetUserPageListVm model)
        {
            <GroupBox Title="搜索条件">
                <div class="row g-3 form-inline">
                    <div class="col-12 col-sm-6">
                        <BootstrapInput @bind-Value="@model.RealName" DisplayText="真实姓名"
                                        PlaceHolder="请输入真实姓名" ShowLabel="true"/>
                    </div>
                    <div class="col-12 col-sm-6">
                        <Select @bind-Value="@model.Disabled" DisplayText="状态" ShowLabel="true">
                            <Options>
                                <SelectOption Text="全部" Value="" />
                                <SelectOption Text="启用" Value="false" />
                                <SelectOption Text="禁用" Value="true" />
                            </Options>
                        </Select>
                    </div>
                </div>
            </GroupBox>
        }
    </CustomerSearchTemplate>

    <!-- 表格列 -->
    <TableColumn @bind-Field="@context.UserName" Text="用户名" Width="120"/>
    <TableColumn @bind-Field="@context.RealName" Text="真实姓名" Width="120"/>
    <TableColumn @bind-Field="@context.CreateTime" Text="创建时间" Width="180"
                 FormatString="yyyy-MM-dd HH:mm:ss"/>

    <!-- 状态列（Badge 模板） -->
    <TableColumn @bind-Field="@context.Disabled" Text="状态" Width="80">
        <Template Context="value">
            <Badge Color="@(value.Value ? Color.Danger : Color.Success)">
                @(value.Value ? "禁用" : "启用")
            </Badge>
        </Template>
    </TableColumn>

    <!-- 行操作按钮 -->
    <RowButtonTemplate>
        <TableCellButton Size="Size.ExtraSmall" Color="Color.Success" Icon="fas fa-edit"
                         Text="编辑" OnClick="() => OnShowEditModal(context)" />
        <TableCellPopConfirmButton Size="Size.ExtraSmall" Color="Color.Danger"
                                   Icon="fa-solid fa-trash" Text="删除"
                                   Content="确定要删除吗？"
                                   OnConfirm="@(() => OnDeleteAsync(new[] { context }))"/>
    </RowButtonTemplate>
</Table>
```

**.razor.cs 代码隐藏文件**：
```csharp
public partial class Index
{
    [Inject] private IUserQuery UserQuery { get; set; } = null!;
    [Inject] private ToastService ToastService { get; set; } = null!;

    private Table<GetUserListResult>? UserTable { get; set; }
    private GetUserPageListVm CustomerSearchModel { get; set; } = new();

    private async Task<QueryData<GetUserListResult>> OnSearchModelQueryAsync(QueryPageOptions options)
    {
        CustomerSearchModel.PageSize = options.PageItems;
        CustomerSearchModel.PageIndex = options.PageIndex;

        var result = await UserQuery.GetPageListAsync(CustomerSearchModel);
        if (result.IsSuccess && result.Data != null)
        {
            return new QueryData<GetUserListResult>()
            {
                Items = result.Data.Rows,
                TotalCount = Convert.ToInt32(result.Data.PageInfo.Total),
                IsFiltered = options.Filters.Any(),
                IsSorted = options.SortOrder != SortOrder.Unset,
                IsAdvanceSearch = options.AdvanceSearches.Any(),
                IsSearch = options.Searches.Any()
            };
        }
        return new QueryData<GetUserListResult>();
    }

    private Task<GetUserPageListVm> OnResetSearchAsync()
    {
        CustomerSearchModel = new GetUserPageListVm();
        return Task.FromResult(CustomerSearchModel);
    }

    private async Task<bool> OnDeleteAsync(IEnumerable<GetUserListResult> items)
    {
        var ids = items.Select(x => x.Id).ToArray();
        var result = await UserService.DeleteAsync(ids);
        if (result.IsSuccess)
        {
            await ToastService.Success("消息通知", "删除成功");
            return true;
        }
        await ToastService.Error("消息通知", result.Message);
        return false;
    }
}
```

**要点**：
- `ShowExtendButtons="true"` 启用扩展按钮区域
- `ShowExtendEditButton="false"` `ShowExtendDeleteButton="false"` 隐藏内置编辑/删除按钮，改用自定义行按钮
- `SearchMode="SearchMode.Top"` 搜索框在表格上方
- `OnQueryAsync` 返回 `QueryData<T>` 包含分页信息
- 批量删除通过 `IsMultipleSelect="true"` + `OnDeleteAsync` 处理

#### 1.2 树形表格（菜单/部门管理）

```razor
<Table @ref="TableRef" TItem="GetMenuListResult"
       OnQueryAsync="@OnQueryAsync"
       IsTree="true"
       TreeNodeConverter="@TreeNodeConverter"
       ShowToolbar="false" ShowSearch="false"
       IsStriped="true" IsBordered="true"
       ShowExtendButtons="true">
```

```csharp
private static Task<IEnumerable<TableTreeNode<GetMenuListResult>>> TreeNodeConverter(
    IEnumerable<GetMenuListResult> items)
{
    var itemList = items?.ToList() ?? [];
    var lookup = itemList.ToLookup(x => x.ParentId);

    IEnumerable<TableTreeNode<GetMenuListResult>> BuildTree(string parentId)
    {
        return lookup[parentId].Select(item => new TableTreeNode<GetMenuListResult>(item)
        {
            HasChildren = lookup[item.Id].Any(),
            IsExpand = false,
            Items = BuildTree(item.Id)
        });
    }
    return Task.FromResult(BuildTree(string.Empty));
}
```

#### 1.3 内联编辑表格（简单字典数据）

```razor
<Table TItem="GetDictDataResult"
       AddModalTitle="增加字典数据" EditModalTitle="编辑字典数据"
       OnAddAsync="@OnAddAsync" OnSaveAsync="@OnSaveAsync"
       OnDeleteAsync="@OnDeleteAsync"
       ShowExtendButtons="true"
       IsStriped="true" IsBordered="true">
```

```csharp
private static Task<GetDictDataResult> OnAddAsync() =>
    Task.FromResult(new GetDictDataResult { IsEnabled = true });

private async Task<bool> OnSaveAsync(GetDictDataResult item, ItemChangedType changedType)
{
    var result = changedType == ItemChangedType.Add
        ? await Service.AddAsync(item)
        : await Service.EditAsync(item);
    return result.IsSuccess;
}
```

**要点**：适合简单 CRUD，无需自定义 Add/Edit 组件的场景。列定义中通过 `IsVisibleWhenAdd="false"` `IsVisibleWhenEdit="false"` 控制字段可见性。

#### 1.4 刷新表格数据

```csharp
// 查询/刷新表格
if (UserTable != null)
    await UserTable.QueryAsync();

// 获取选中行
var selectedRows = UserTable?.SelectedRows ?? new List<GetUserListResult>();
```

---

### 二、Modal 组件（模态框）

#### 2.1 自定义模态框（Add/Edit 分离模式）

**页面结构**：
```
Components/Pages/[Entity]/
├── Index.razor           # 主页面，包含表格和工具栏
├── Index.razor.cs        # 主页面代码隐藏
├── Add.razor             # 添加模态框组件
├── Add.razor.cs          # 添加组件代码隐藏
├── Edit.razor            # 编辑模态框组件
└── Edit.razor.cs         # 编辑组件代码隐藏
```

**Add.razor（子组件）**：
```razor
<Modal @ref="AddModal" Size="Size.Large">
    <ModalDialog Title="添加用户" IsCentered="true">
        <BodyTemplate>
            <ValidateForm Model="@Model" OnValidSubmit="@OnValidSubmit">
                <div class="row g-3">
                    <div class="col-md-6">
                        <BootstrapInput @bind-Value="@Model.UserName" DisplayText="用户名"
                                        PlaceHolder="请输入用户名" ShowLabel="true"/>
                    </div>
                    <div class="col-md-6">
                        <BootstrapInput @bind-Value="@Model.RealName" DisplayText="真实姓名"
                                        PlaceHolder="请输入真实姓名" ShowLabel="true"/>
                    </div>
                </div>
            </ValidateForm>
        </BodyTemplate>
        <FooterTemplate>
            <Button Color="Color.Primary" OnClick="@OnSave">
                <i class="fas fa-save me-2"></i>提交
            </Button>
        </FooterTemplate>
    </ModalDialog>
</Modal>
```

**Add.razor.cs（代码隐藏）**：
```csharp
public partial class Add
{
    [Inject] private IUserService UserService { get; set; } = null!;
    [Inject] private ToastService ToastService { get; set; } = null!;

    [Parameter] public EventCallback<AddUserVm> OnSaveCallback { get; set; }

    private Modal? AddModal { get; set; }
    private AddUserVm Model { get; set; } = new();

    public async Task Show()
    {
        await InvokeAsync(async () =>
        {
            Model = new AddUserVm();
            StateHasChanged();
            if (AddModal != null)
                await AddModal.Show();
        });
    }

    public async Task Hide()
    {
        if (AddModal != null)
            await AddModal.Close();
    }

    private async Task OnSave()
    {
        var result = await UserService.AddAsync(Model);
        if (result.IsSuccess)
        {
            await ToastService.Success("消息通知", "添加成功");
            if (OnSaveCallback.HasDelegate)
                await OnSaveCallback.InvokeAsync(Model);
            await Hide();
        }
        else
        {
            await ToastService.Error("消息通知", result.Message);
        }
    }
}
```

**Index.razor（父组件）**：
```razor
<Add @ref="AddComponent" OnSaveCallback="@OnAddSave"/>

@code {
    private Add? AddComponent { get; set; }

    private async Task OnShowAddModal()
    {
        if (AddComponent != null)
            await AddComponent.Show();
    }

    private async Task OnAddSave(AddUserVm model)
    {
        if (AddComponent != null)
            await AddComponent.Hide();
        if (UserTable != null)
            await UserTable.QueryAsync();
    }
}
```

**要点**：
- `Modal` 尺寸：`Size.Small`（简单确认）、`Size.Medium`（修改密码）、`Size.Large`（标准 CRUD）、`Size.ExtraLarge`（复杂表单如权限分配）
- `InvokeAsync` 确保在 UI 线程执行，`StateHasChanged()` 强制重新渲染
- `EventCallback<T>` 实现父子组件通信
- 子组件暴露 `Show()`/`Hide()` 方法供父组件调用

#### 2.2 确认对话框（删除确认）

**行内确认（推荐）**：
```razor
<TableCellPopConfirmButton Size="Size.ExtraSmall" Color="Color.Danger"
                           Icon="fa-solid fa-trash" Text="删除"
                           Content="确定要删除吗？此操作不可恢复"
                           OnConfirm="@(() => OnDeleteAsync(new[] { context }))"/>
```

**自定义确认模态框**（复杂场景）：
```razor
<Modal @ref="ConfirmModal" IsCentered="true">
    <ModalDialog Title="确认操作" IsCentered="true">
        <BodyTemplate>
            <div class="text-center">
                <i class="fas fa-exclamation-triangle text-warning" style="font-size: 48px;"></i>
                <p class="text-muted mt-3">确定要执行此操作吗？此操作不可恢复！</p>
            </div>
        </BodyTemplate>
        <FooterTemplate>
            <Button Color="Color.Danger" OnClick="@OnConfirm">确认</Button>
            <Button Color="Color.Secondary" OnClick="@(() => ConfirmModal?.Close())">取消</Button>
        </FooterTemplate>
    </ModalDialog>
</Modal>
```

---

### 三、表单组件

#### 3.1 ValidateForm（表单验证）

```razor
<!-- 自动提交验证 -->
<ValidateForm Model="@Model" OnValidSubmit="@OnValidSubmit">
    <BootstrapInput @bind-Value="@Model.Name" DisplayText="名称"
                    PlaceHolder="请输入名称" ShowLabel="true"/>
</ValidateForm>

<!-- 手动提交验证 -->
<ValidateForm Model="@Model">
    <BootstrapInput @bind-Value="@Model.Name" DisplayText="名称"/>
    <Button OnClick="@OnManualSubmit">提交</Button>
</ValidateForm>
```

**手动验证模式**（需要自定义验证逻辑时）：
```csharp
private async Task OnManualSubmit()
{
    var validationContext = new ValidationContext(Model);
    var validationResults = new List<ValidationResult>();
    bool isValid = Validator.TryValidateObject(Model, validationContext, validationResults, true);
    if (!isValid)
    {
        foreach (var result in validationResults)
            await ToastService.Error("验证错误", result.ErrorMessage ?? "验证失败");
        return;
    }
    // 继续业务逻辑...
}
```

#### 3.2 输入组件一览

**文本输入**：
```razor
<BootstrapInput @bind-Value="@Model.UserName" DisplayText="用户名"
                PlaceHolder="请输入用户名" maxlength="50" ShowLabel="true"/>

<!-- 只读 -->
<BootstrapInput @bind-Value="@Model.UserName" DisplayText="用户账号"
                ReadOnly="true" ShowLabel="true"/>

<!-- 密码 -->
<BootstrapInput @bind-Value="@Model.Password" PlaceHolder="请输入密码"
                type="Password" DisplayText="密码" ShowLabel="true"/>
```

**数字输入**：
```razor
<BootstrapInputNumber @bind-Value="@Model.SortNumber" DisplayText="排序"
                      ShowLabel="true" Min="0"/>
```

**多行文本**：
```razor
<Textarea @bind-Value="@Model.Remark" DisplayText="备注"
          PlaceHolder="请输入备注" maxlength="500" ShowLabel="true" rows="3"/>
```

**开关**：
```razor
<Switch @bind-Value="@Model.Disabled" DisplayText="是否禁用"
        ShowLabel="true" OnLabel="是" OffLabel="否"/>
```

#### 3.3 下拉选择组件

**静态选项**：
```razor
<Select @bind-Value="@Model.Status" DisplayText="状态" ShowLabel="true">
    <Options>
        <SelectOption Text="全部" Value="" />
        <SelectOption Text="启用" Value="false" />
        <SelectOption Text="禁用" Value="true" />
    </Options>
</Select>
```

**动态数据源 + 可搜索 + 可清除**：
```razor
<Select ShowSearch="true" TValue="string" Items="@DepartmentOptions"
        @bind-Value="@Model.DepartmentId" DisplayText="所属部门"
        PlaceHolder="请选择部门" ShowLabel="true" IsClearable="true"/>
```

```csharp
private List<SelectedItem> DepartmentOptions { get; set; } = new();
// 在 OnInitializedAsync 或 OnAfterRenderAsync 中加载：
DepartmentOptions = departments.Select(x => new SelectedItem(x.Id, x.Name)).ToList();
```

**枚举类型选择**：
```razor
<Select TValue="MenuTypeEnum" Items="@MenuTypeOptions"
        @bind-Value="@Model.MenuType" DisplayText="菜单类型"
        PlaceHolder="请选择" ShowLabel="true"/>
```

#### 3.4 复选框列表

```razor
<CheckboxList TValue="string" @bind-Value="@SelectedIdsString"
              Items="@Options" ShowLabel="true" DisplayText="选项"
              IsVertical="true" ShowBorder="true"/>
```

```csharp
private List<SelectedItem> Options { get; set; } = new();
private string SelectedIdsString { get; set; } = string.Empty;
// 解析：SelectedIdsString.Split(',', StringSplitOptions.RemoveEmptyEntries).ToList();
```

---

### 四、TreeView 组件（树形选择）

**使用场景**：角色权限分配、菜单树选择、部门树选择。

```razor
<TreeView Items="@TreeItems"
          OnTreeItemChecked="OnTreeItemChecked"
          IsAccordion="false"
          ShowCheckbox="true"
          ClickToggleNode="true"
          AutoCheckChildren="true"
          AutoCheckParent="true"/>
```

**构建树节点**：
```csharp
private List<TreeViewItem<MenuNode>> BuildTreeItems(List<MenuNode> menus)
{
    return menus.Select(menu =>
    {
        var isChecked = CheckedIds.Contains(menu.Id);
        var item = new TreeViewItem<MenuNode>(menu)
        {
            Text = menu.Name,
            Icon = menu.Icon ?? "fa-solid fa-folder",
            HasChildren = menu.Children?.Count > 0,
            IsExpand = true,
            CheckedState = isChecked ? CheckboxState.Checked : CheckboxState.UnChecked
        };
        if (menu.Children?.Count > 0)
            item.Items = BuildTreeItems(menu.Children);
        return item;
    }).ToList();
}
```

**勾选事件处理**：
```csharp
private Task OnTreeItemChecked(List<TreeViewItem<MenuNode>> items)
{
    SelectedItems = new List<TreeViewItem<MenuNode>>(items);
    return Task.CompletedTask;
}
```

**CRITICAL - 强制重建 TreeView 防止状态污染**：
```csharp
private string TreeViewKey = Guid.NewGuid().ToString();
private List<TreeViewItem<MenuNode>> TreeItems = new();
private HashSet<string> CheckedIds = new();

public async Task ShowAsync(Entity entity)
{
    CurrentEntity = entity;

    // 1. 清除状态
    SelectedItems = new();
    CheckedIds = new();
    TreeItems = new();

    // 2. 触发渲染清除旧 TreeView
    StateHasChanged();

    // 3. 加载数据
    await LoadCheckedIds();
    await LoadTreeData();

    // 4. 加载后更改 Key（强制重建）
    TreeViewKey = Guid.NewGuid().ToString();

    // 5. 触发渲染重建 TreeView
    StateHasChanged();

    // 6. 模态框在渲染周期完成后显示
    await InvokeAsync(async () =>
    {
        if (Modal != null) await Modal.Show();
    });
}
```

```razor
<!-- Key 绑定确保强制重建 -->
<TreeView Key="@TreeViewKey" Items="@TreeItems" .../>
```

**模型要求**：数据模型必须实现 `Equals` 和 `GetHashCode`：
```csharp
public override bool Equals(object? obj) =>
    obj is MenuNode other && Id == other.Id;
public override int GetHashCode() => Id?.GetHashCode() ?? 0;
```

---

### 五、Toast 通知

```csharp
// 简写方法（推荐）
await ToastService.Success("消息通知", "操作成功");
await ToastService.Error("消息通知", "操作失败");
await ToastService.Warning("消息通知", "请注意");
await ToastService.Information("消息通知", "提示信息");

// 完整配置
await ToastService.Show(new ToastOption
{
    PreventDuplicates = true,
    Category = ToastCategory.Success,
    Title = "消息通知",
    Content = "操作成功"
});
```

**自定义位置**：
```csharp
[CascadingParameter] private BootstrapBlazorRoot? Root { get; set; }
private ToastContainer? ToastContainer { get; set; }

protected override void OnInitialized()
{
    ToastContainer = Root.ToastContainer;
}

// 设置位置
ToastContainer?.SetPlacement(Placement.TopCenter);
```

---

### 六、Layout 布局组件

```razor
<Layout ShowGotoTop="true" ShowCollapseBar="true" ShowFooter="true"
        IsPage="true" IsFullSide="true" IsFixedHeader="true" IsFixedFooter="false"
        ShowSplitBar="true" SidebarMinWidth="200" SidebarMaxWidth="350"
        TabStyle="TabStyle.Chrome" ShowToolbar="true" ShowTabContextMenu="true"
        ShowTabInHeader="false" ShowTabExtendButtons="false"
        TabDefaultUrl="/" UseTabSet="true" IsFixedTabHeader="false"
        AdditionalAssemblies="new[] { GetType().Assembly }"
        Menus="@Menus">
    <Header><!-- 头部内容 --></Header>
    <Side><!-- 侧边栏菜单 --></Side>
    <Main>
        <ErrorLogger>
            @Body
        </ErrorLogger>
    </Main>
    <Footer><!-- 页脚 --></Footer>
</Layout>
```

**菜单数据构建**：
```csharp
private List<MenuItem> Menus { get; set; } = new();

// 方式一：从数据源转换
Menus = menuData.Select(m => new MenuItem()
{
    Text = m.Name,
    Icon = m.Icon,
    Url = m.Component,  // 对应 @page 路由（不带前导 /）
    Match = NavLinkMatch.All,
    Items = m.Children?.Select(c => new MenuItem() { ... }).ToList()
}).ToList();

// 方式二：静态定义
Menus = new List<MenuItem>()
{
    new() { Text = "首页", Icon = "fa-solid fa-fw fa-home", Url = "/", Match = NavLinkMatch.All },
    new() { Text = "系统管理", Icon = "fa-solid fa-fw fa-cogs",
        Items = new List<MenuItem>()
        {
            new() { Text = "用户管理", Icon = "fa-solid fa-users", Url = "/users" },
            new() { Text = "角色管理", Icon = "fa-solid fa-user-shield", Url = "/role-management" }
        }
    }
};
```

**Tab 标签页属性**：
```razor
@page "/your-page"
@attribute [TabItemOption(Text = "页面标题", Closable = false)]
@attribute [Authorize]
```

---

### 七、其他常用组件

#### 7.1 Card 卡片
```razor
<Card class="mb-4 shadow-sm border-0">
    <HeaderTemplate>
        <div class="d-flex align-items-center">
            <i class="fas fa-bolt me-2"></i><span>标题</span>
        </div>
    </HeaderTemplate>
    <BodyTemplate>
        <!-- 内容 -->
    </BodyTemplate>
</Card>
```

#### 7.2 Badge 徽章
```razor
<Badge Color="@(enabled ? Color.Success : Color.Danger)">
    @(enabled ? "启用" : "禁用")
</Badge>
```

#### 7.3 Drawer 抽屉
```razor
<Drawer Placement="Placement.Right" @bind-IsOpen="@IsOpen" IsBackdrop="true">
    <!-- 内容 -->
</Drawer>
```

#### 7.4 Alert 警告
```razor
<Alert Color="Color.Info">信息提示</Alert>
<Alert Color="Color.Danger" ShowBorder="true" ShowIcon="true">错误警告</Alert>
```

#### 7.5 Avatar 头像
```razor
<Avatar Url="@userAvatar" IsCircle="true" Size="Size.ExtraLarge"/>
```

#### 7.6 Logout 登出组件
```razor
<Logout ImageUrl="@avatar" DisplayName="@displayName" UserName="@userName">
    <LinkTemplate>
        <a href="/profile"><i class="fa-solid fa-suitcase"></i>个人中心</a>
        <LogoutLink></LogoutLink>
    </LinkTemplate>
</Logout>
```

#### 7.7 GroupBox 分组框
```razor
<GroupBox Title="搜索条件">
    <div class="row g-3 form-inline">
        <!-- 搜索字段 -->
    </div>
</GroupBox>
```

#### 7.8 DropdownWidget 下拉挂件
```razor
<DropdownWidget class="px-3">
    <DropdownWidgetItem Icon="fa-regular fa-envelope" BadgeNumber="5" BadgeColor="Color.Danger">
        <HeaderTemplate><span>您有 5 条未读消息</span></HeaderTemplate>
        <BodyTemplate><!-- 消息列表 --></BodyTemplate>
        <FooterTemplate><a href="#">查看全部</a></FooterTemplate>
    </DropdownWidgetItem>
</DropdownWidget>
```

#### 7.9 Progress 进度条
```razor
<Progress IsAnimated="true" IsStriped="true" Value="75" Color="Color.Primary"/>
```

---

## CSS 隔离

使用 `::deep` 穿透到子组件样式：

```css
/* ComponentName.razor.css */
::deep .form-control {
    border-radius: 8px;
}

::deep .layout .layout-side {
    background-color: var(--bs-dark);
}
```

**CSS 隔离文件命名**：必须为 `{ProjectName}.styles.css`（如 `RbacAuth.Front.styles.css`）。

---

## 完整页面模板

创建新 CRUD 页面时的标准步骤：

### Step 1：创建页面目录和文件

```
Components/Pages/EntityName/
├── Index.razor
├── Index.razor.cs
├── Add.razor
├── Add.razor.cs
├── Edit.razor
└── Edit.razor.cs
```

### Step 2：注册服务（Startup.cs）

```csharp
services.AddScoped<IEntityQuery, EntityQuery>();
services.AddScoped<IEntityService, EntityService>();
```

### Step 3：配置菜单路由

确保页面的 `@page` 路由与菜单的 `Component` 字段一致（不带前导 `/`）。

| 页面路由 | 菜单 Component |
|----------|---------------|
| `@page "/users"` | `users` |
| `@page "/role-management"` | `role-management` |

### Step 4：Index.razor 模板

```razor
@page "/entity-name"
@attribute [TabItemOption(Text = "实体管理")]
@attribute [Authorize]

<PageHeader Title="实体管理" SubTitle="管理系统中的实体数据"/>

<div class="mb-3">
    <Button Color="Color.Primary" OnClick="@OnShowAddModal">
        <i class="fas fa-plus me-2"></i>添加
    </Button>
    <Button Color="Color.Danger" OnClick="@OnBatchDelete" IsAsync="true">
        <i class="fas fa-trash me-2"></i>批量删除
    </Button>
</div>

<Table @ref="EntityTable" TItem="GetEntityListResult"
       IsPagination="true" PageItemsSource="new[] {10, 20, 50}"
       IsStriped="true" IsBordered="true"
       ShowSearch="true" SearchMode="SearchMode.Top"
       ShowExtendButtons="true"
       ShowExtendEditButton="false" ShowExtendDeleteButton="false"
       OnQueryAsync="@OnQueryAsync"
       CustomerSearchModel="@SearchModel">
    <!-- 列定义 -->
    <TableColumn @bind-Field="@context.Name" Text="名称"/>
    <TableColumn @bind-Field="@context.CreateTime" Text="创建时间" FormatString="yyyy-MM-dd HH:mm:ss"/>
    <RowButtonTemplate>
        <TableCellButton Size="Size.ExtraSmall" Color="Color.Success" Icon="fas fa-edit"
                         Text="编辑" OnClick="() => OnShowEditModal(context)"/>
        <TableCellPopConfirmButton Size="Size.ExtraSmall" Color="Color.Danger"
                                   Icon="fa-solid fa-trash" Text="删除"
                                   Content="确定删除？" OnConfirm="@(() => OnDelete(context))"/>
    </RowButtonTemplate>
</Table>

<Add @ref="AddComponent" OnSaveCallback="@OnAddSave"/>
<Edit @ref="EditComponent" OnSaveCallback="@OnEditSave"/>
```

---

## 常见问题

### TreeView 不显示选中状态
确保数据模型实现了 `Equals` 和 `GetHashCode`，并使用 `Key` 属性强制重建。

### 模态框数据不更新
在 `Show()` 方法中使用 `InvokeAsync` + `StateHasChanged()` 确保在 UI 线程执行并强制渲染。

### 表格自定义行按钮不显示
必须设置 `ShowExtendButtons="true"` 且 `ShowExtendEditButton="false"` `ShowExtendDeleteButton="false"`，然后使用 `<RowButtonTemplate>`。

### 菜单点击 404
确保页面 `@page` 路由与菜单 `Component` 字段完全匹配（不带前导 `/`）。

### 表格搜索不生效
`CustomerSearchModel` 必须是组件属性（非局部变量），`OnQueryAsync` 中从 `QueryPageOptions` 获取分页参数。

## 参考资源

- [BootstrapBlazor 官方文档](https://www.blazor.zone/)
- [BootstrapBlazor GitHub](https://github.com/dotnetcore/BootstrapBlazor)
- [BootstrapBlazor 在线演示](https://www.blazor.zone/table)
