#!/usr/bin/env python3
"""精确修复 expo-sharing-extension 的 Swift 6 并发错误（最终版 v4）
根因（完整分析）：
- 类继承 SLComposeServiceViewController → MainActor 隔离
- processInputItems 显式 nonisolated，但它调用 parseProvider（继承 MainActor）
  → nonisolated 向 MainActor 传 non-Sendable provider → data race
- 处理链上的方法全是纯数据操作（loadItem 回调 + FileManager + Bundle），不需要 MainActor

修复：把整个数据处理链标 nonisolated：
  parseProvider, handleText, handleWebURL, handleFile,
  copyAndProcessFile, saveDataToAppGroup, saveToUserDefaults,
  以及属性 appGroupId, hostAppScheme
保留 MainActor：UIKit 生命周期 (didSelectPost/viewWillAppear/handleShare) 和 openParentApp
"""
import re, sys

path = "ios/expo-sharing-extension/ShareIntoViewController.swift"
src = open(path).read()
orig = src

# 0. 清理之前可能加的 @MainActor（方法级）
src = re.sub(r'@MainActor\s*\n(?=\s*private func (?:copyAndProcessFile|saveDataToAppGroup)\()', '', src)

funcs = [
    'saveToUserDefaults', 'parseProvider', 'handleText', 'handleWebURL',
    'handleFile', 'copyAndProcessFile', 'saveDataToAppGroup',
]
for f in funcs:
    if not re.search(r'nonisolated\s+private func ' + f, src):
        src = re.sub(
            r'^(\s*)private func ' + re.escape(f) + r'\(',
            r'\1nonisolated private func ' + f + '(',
            src, count=1, flags=re.M,
        )
        print(f"{f} → nonisolated")
    else:
        print(f"{f} 已是 nonisolated")

# 属性
for prop in ['appGroupId', 'hostAppScheme']:
    if not re.search(r'nonisolated\s+private var ' + prop, src):
        src = re.sub(
            r'^(\s*)private var ' + re.escape(prop) + r': String \{',
            r'\1nonisolated private var ' + prop + r': String {',
            src, count=1, flags=re.M,
        )
        print(f"{prop} → nonisolated")

# 移除 assumeIsolated 包装
src = re.sub(r'MainActor\.assumeIsolated \{\s*self\.([^}]+)\s*\}', r'self.\1', src)
src = re.sub(r'MainActor\.assumeIsolated \{\s*self\.', 'self.', src)

open(path, "w").write(src)
print("补丁完成, 变更:", "是" if src != orig else "否")
