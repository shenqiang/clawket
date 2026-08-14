#!/usr/bin/env python3
"""精确修复 expo-sharing-extension 的 Swift 6 并发错误（最终版 v3）
根因：
- SLComposeServiceViewController 子类 MainActor 隔离
- copyAndProcessFile / saveDataToAppGroup 是纯 FileManager 操作 → nonisolated
- 但它们引用 appGroupId / hostAppScheme 属性（也继承 MainActor 隔离）
  → nonisolated 方法访问 MainActor 属性报错
修复：
1. 两个方法 → nonisolated
2. appGroupId / hostAppScheme 两个计算属性 → nonisolated（纯 Bundle 读取）
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

# 3. appGroupId 计算属性 → nonisolated
if not re.search(r'nonisolated\s*private var appGroupId', src):
    src = re.sub(
        r'^(\s*)private var appGroupId: String \{',
        r'\1nonisolated private var appGroupId: String {',
        src, count=1, flags=re.M,
    )
    print("3. appGroupId → nonisolated")
else:
    print("3. appGroupId 已是 nonisolated")

# 4. hostAppScheme 计算属性 → nonisolated（保险，可能其他方法用）
if not re.search(r'nonisolated\s*private var hostAppScheme', src):
    src = re.sub(
        r'^(\s*)private var hostAppScheme: String \{',
        r'\1nonisolated private var hostAppScheme: String {',
        src, count=1, flags=re.M,
    )
    print("4. hostAppScheme → nonisolated")
else:
    print("4. hostAppScheme 已是 nonisolated")

# 5. 移除之前加的 MainActor.assumeIsolated 包装（不再需要）
src = re.sub(r'MainActor\.assumeIsolated \{\s*self\.([^}]+)\s*\}', r'self.\1', src)
src = re.sub(r'MainActor\.assumeIsolated \{\s*self\.', 'self.', src)

open(path, "w").write(src)
print("补丁完成, 变更:", "是" if src != orig else "否")

# 验证
for line in src.split('\n'):
    if 'nonisolated' in line:
        print("  >", line.strip()[:100])
