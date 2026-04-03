#!/usr/bin/env bun
/**
 * ============================================
 * Marketplace JSON 验证脚本
 * ============================================
 * 功能：验证 marketplace.json 文件
 *   - JSON 格式是否正确
 *   - plugins 数组是否存在
 *   - 每个插件条目是否有必填字段
 *   - 是否有重复的插件名
 *
 * 使用方法：
 *   bun validate-marketplace.ts <path-to-marketplace.json>
 */

import { readFile } from "fs/promises";

async function main() {
  const filePath = process.argv[2];
  if (!filePath) {
    console.error("Usage: validate-marketplace.ts <path-to-marketplace.json>");
    process.exit(2);
  }

  const content = await readFile(filePath, "utf-8");

  // 解析 JSON
  let parsed: unknown;
  try {
    parsed = JSON.parse(content);
  } catch (err) {
    console.error(
      `ERROR: ${filePath} is not valid JSON: ${err instanceof Error ? err.message : err}`
    );
    process.exit(1);
  }

  // 验证 JSON 是一个对象
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    console.error(`ERROR: ${filePath} must be a JSON object`);
    process.exit(1);
  }

  const marketplace = parsed as Record<string, unknown>;

  // 验证 plugins 数组存在
  if (!Array.isArray(marketplace.plugins)) {
    console.error(`ERROR: ${filePath} missing "plugins" array`);
    process.exit(1);
  }

  // 验证每个插件条目
  const errors: string[] = [];
  const seen = new Set<string>();
  const required = ["name", "description", "source"] as const;

  marketplace.plugins.forEach((p, i) => {
    if (!p || typeof p !== "object") {
      errors.push(`plugins[${i}]: must be an object`);
      return;
    }
    const entry = p as Record<string, unknown>;
    // 检查必填字段
    for (const field of required) {
      if (!entry[field]) {
        errors.push(`plugins[${i}] (${entry.name ?? "?"}): missing required field "${field}"`);
      }
    }
    // 检查重复的插件名
    if (typeof entry.name === "string") {
      if (seen.has(entry.name)) {
        errors.push(`plugins[${i}]: duplicate plugin name "${entry.name}"`);
      }
      seen.add(entry.name);
    }
  });

  // 输出错误
  if (errors.length) {
    console.error(`ERROR: ${filePath} has ${errors.length} validation error(s):`);
    for (const e of errors) console.error(`  - ${e}`);
    process.exit(1);
  }

  console.log(`OK: ${marketplace.plugins.length} plugins, no duplicates, all required fields present`);
}

main().catch((err) => {
  console.error("Fatal error:", err);
  process.exit(2);
});
