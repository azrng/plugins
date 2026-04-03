# Claude Skill 定义规范

本文档说明如何在此插件市场中定义和创建 Claude Skills。

## Skill 基本结构

每个插件 (plugin) 下的 `skills/` 目录包含 SKILL.md 文件：

```
plugin-name/
├── .claude-plugin/
│   └── plugin.json         # 插件元数据
├── skills/
│   └── SKILL.md            # Skill 定义文件（必需）
├── scripts/                # 可选：辅助脚本
├── data/                   # 可选：数据文件
└── references/             # 可选：参考文档
```

## SKILL.md 文件格式

### Frontmatter（必需）

SKILL.md 文件开头必须包含 YAML frontmatter：

```markdown
---
name: skill-name
description: 简洁描述，说明何时触发此 skill
license: LICENSE.txt（可选）
---

Skill 的详细说明内容...
```

#### Frontmatter 字段说明

| 字段 | 必需 | 说明 |
|------|------|------|
| `name` | ✅ | Skill 唯一标识符，使用小写字母和连字符 |
| `description` | ✅ | 简洁描述（1-2句话），说明 skill 的用途和触发场景 |
| `license` | ❌ | 许可证文件名（如 `LICENSE.txt`） |

### 内容结构

SKILL.md 正文应包含以下部分：

#### 1. 概述（Overview）
简要说明 skill 的功能和用途。

#### 2. 适用范围（Scope）
明确：
- **适用场景**：何时使用此 skill
- **不适用场景**：何时不使用

#### 3. 触发关键词（Trigger Keywords）
列出会触发此 skill 的关键词列表。

```markdown
**触发关键词**: 关键词1, 关键词2, keyword1, keyword2
```

#### 4. 前置条件（Prerequisites）
列出使用前需要安装的依赖：

```markdown
## 前置条件

```bash
pip install requests
npm install package-name
```
```

#### 5. 核心能力（Capabilities）
列出 skill 提供的主要功能：

```markdown
## 核心能力

### 能力1：能力名称
简短描述

### 能力2：能力名称
简短描述
```

#### 6. 命令列表（Commands）
如果 skill 包含可执行脚本，列出命令：

```markdown
## 命令列表

| 命令 | 说明 | 用法 |
|------|------|------|
| `command` | 描述 | `python script.py command [参数]` |
```

#### 7. 处理步骤（Steps）
详细说明工作流程：

```markdown
## 处理步骤

### Step 1：步骤名称

**目标**：描述目标

**为什么这一步重要**：说明原因

**执行**：
\```bash
命令
\```

**检查点**：如何验证步骤成功
```

#### 8. 验证清单（Validation）
提供自检清单：

```markdown
## 验证清单

- [ ] 依赖已安装
- [ ] Step 1 执行无报错
- [ ] 最终输出符合预期
```

#### 9. 输出格式（Output Format）
定义标准输出格式：

```markdown
## 输出格式

\```markdown
# 报告标题

**生成时间**: YYYY-MM-DD HH:MM

## 核心发现
1. 发现1
2. 发现2
\```
```

#### 10. 参考资料（References）
列出相关资源链接。

## Skill 命名规范

- 使用小写字母
- 多个单词用连字符分隔
- 保持简洁但具描述性
- 示例：`frontend-design`, `weather-advisor`, `code-review`

## 描述编写规范

### 好的描述
```
创建高质量的前端界面设计。生成独特、精致的前端代码和UI设计，
避免通用的AI美学。适用于构建网站、落地页、仪表盘等。
```

### 不好的描述
```
这是一个前端设计的技能。
```

## 完整示例

见 [frontend-design/skills/SKILL.md](plugins/frontend-design/skills/SKILL.md) 和 [weather-advisor/skills/SKILL.md](plugins/weather-advisor/skills/SKILL.md)。

## 最佳实践

1. **保持简洁**：description 应在 1-2 句话内说明核心用途
2. **明确边界**：清楚说明适用和不适用场景
3. **可验证性**：每个步骤应有明确的检查点
4. **示例驱动**：提供具体的使用示例
5. **错误处理**：说明常见错误和解决方案
