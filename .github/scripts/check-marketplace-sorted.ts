#!/usr/bin/env bun
/**
 * ============================================
 * 插件排序检查脚本
 * ============================================
 * 功能：检查 marketplace.json 中的插件是否按名称字母顺序排序
 *
 * 使用方法：
 *   bun check-marketplace-sorted.ts           # 检查，如果未排序则退出码为 1
 *   bun check-marketplace-sorted.ts --fix     # 自动排序并保存
 */

import { readFileSync, writeFileSync } from "fs";
import { join } from "path";

// marketplace.json 文件路径
const MARKETPLACE = join(import.meta.dir, "../../.claude-plugin/marketplace.json");

type Plugin = { name: string; [k: string]: unknown };
type Marketplace = { plugins: Plugin[]; [k: string]: unknown };

const raw = readFileSync(MARKETPLACE, "utf8");
const mp: Marketplace = JSON.parse(raw);

// 按名称（不区分大小写）比较
const cmp = (a: Plugin, b: Plugin) =>
  a.name.toLowerCase().localeCompare(b.name.toLowerCase());

// --fix 模式：自动排序并保存
if (process.argv.includes("--fix")) {
  mp.plugins.sort(cmp);
  writeFileSync(MARKETPLACE, JSON.stringify(mp, null, 2) + "\n");
  console.log(`sorted ${mp.plugins.length} plugins`);
  process.exit(0);
}

// 检查模式：验证是否已排序
for (let i = 1; i < mp.plugins.length; i++) {
  if (cmp(mp.plugins[i - 1], mp.plugins[i]) > 0) {
    console.error(
      `marketplace.json plugins are not sorted: ` +
        `'${mp.plugins[i - 1].name}' should come after '${mp.plugins[i].name}' (index ${i})`,
    );
    console.error(`  run: bun .github/scripts/check-marketplace-sorted.ts --fix`);
    process.exit(1);
  }
}

console.log(`ok: ${mp.plugins.length} plugins sorted`);
