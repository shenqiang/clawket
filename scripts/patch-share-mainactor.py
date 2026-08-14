#!/usr/bin/env python3
"""精确修复 expo-sharing-extension 的 Swift 6 并发错误（最终方案）
根因分析（基于真实模板源码）：
- SLComposeServiceViewController 是 MainActor 隔离的，其子类方法继承隔离
- copyAndProcessFile / saveDataToAppGroup 是纯 FileManager 操作，不需要 MainActor
- loadItem @Sendable 回调里同步调用它们 → "MainActor 方法在 nonisolated 同步调用"
- processInputItems 显式 nonisolated，调 parseProvider → 若 parseProvider 变 MainActor
  → "sending provider data races"

最终修复：给两个纯函数方法显式 nonisolated（覆盖继承的 MainActor 隔离）
→ loadItem 回调、parseProvider、processInputItems 全部不跨隔离域，所有错误消失。
"""
import re, sys

path = "ios/expo-sharing-extension/ShareIntoViewController.swift"
src = open(path).read()
orig = src

# 0. 移除之前可能加的 @MainActor（方法级）
src = re.sub(r'@MainActor\s*\n(?=\s*private func (?:copyAndProcessFile|saveDataToAppGroup)\()', '', src)
print("0. 移除方法级 @MainActor（如存在）")

# 1. copyAndProcessFile → nonisolated
if not re.search(r'nonisolated\s*private func copyAndProcessFile', src):
    src = re.sub(
        r'^(\s*)private func copyAndProcessFile\(',
        r'\1nonisolated private func copyAndProcessFile(',
        src, count=1, flags=re.M,
    )
    print("1. copyAndProcessFile → nonisolated")
else:
    print("1. copyAndProcessFile 已是 nonisolated")

# 2. saveDataToAppGroup → nonisolated
if not re.search(r'nonisolated\s*private func saveDataToAppGroup', src):
    src = re.sub(
        r'^(\s*)private func saveDataToAppGroup\(',
        r'\1nonisolated private func saveDataToAppGroup(',
        src, count=1, flags=re.M,
    )
    print("2. saveDataToAppGroup → nonisolated")
else:
    print("2. saveDataToAppGroup 已是 nonisolated")

# 3. 移除之前加的 MainActor.assumeIsolated 包装（不再需要，恢复原始调用）
# 单行形式: MainActor.assumeIsolated { self.foo(...) } → self.foo(...)
src = re.sub(r'MainActor\.assumeIsolated \{\s*self\.([^}]+)\s*\}', r'self.\1', src)
# 多行形式: MainActor.assumeIsolated { self.foo(\n ... \n) } → self.foo(\n ... \n)
src = re.sub(r'MainActor\.assumeIsolated \{\s*self\.', 'self.', src)

open(path, "w").write(src)
print("补丁完成, 变更:", "是" if src != orig else "否")

# 验证
for line in src.split('\n'):
    if 'nonisolated private func' in line or 'assumeIsolated' in line or line.strip() == '@MainActor':
        print("  >", line.strip()[:100])
