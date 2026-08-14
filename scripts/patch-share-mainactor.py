#!/usr/bin/env python3
"""精确修复 expo-sharing-extension 的 Swift 6 并发错误（基于真实模板源码）
错误1: loadItem @Sendable 回调中同步调用 MainActor 方法
  → copyAndProcessFile / saveDataToAppGroup 加 @MainActor + 调用点 assumeIsolated
错误2: 类级 @MainActor 会与 nonisolated processInputItems 冲突（sending provider data race）
  → 不加类级 @MainActor，只标注两个方法
"""
import re, sys

path = "ios/expo-sharing-extension/ShareIntoViewController.swift"
src = open(path).read()
orig = src

# 0. 移除可能已加的类级 @MainActor（安全起见）
src = re.sub(r'^@MainActor\s*\n(?=class ShareIntoViewController)', '', src, flags=re.M)
print("0. 移除类级 @MainActor（如存在）")

# 1. 给 copyAndProcessFile 加 @MainActor
if not re.search(r'@MainActor\s*\n\s*private func copyAndProcessFile', src):
    src = re.sub(
        r'^(\s*private func copyAndProcessFile\()',
        r'@MainActor\n\1',
        src, count=1, flags=re.M,
    )
    print("1. copyAndProcessFile 添加 @MainActor")
else:
    print("1. copyAndProcessFile 已有 @MainActor")

# 2. 给 saveDataToAppGroup 加 @MainActor
if not re.search(r'@MainActor\s*\n\s*private func saveDataToAppGroup', src):
    src = re.sub(
        r'^(\s*private func saveDataToAppGroup\()',
        r'@MainActor\n\1',
        src, count=1, flags=re.M,
    )
    print("2. saveDataToAppGroup 添加 @MainActor")
else:
    print("2. saveDataToAppGroup 已有 @MainActor")

# 3. 包装 copyAndProcessFile 调用（单行）
pat_copy = re.compile(r'(let result = )self\.copyAndProcessFile\(url: url, type: type\)')
src, n_copy = pat_copy.subn(
    r'\g<1>MainActor.assumeIsolated { self.copyAndProcessFile(url: url, type: type) }',
    src,
)
print(f"3. copyAndProcessFile 调用包装: {n_copy} 处")

# 4. 包装 saveDataToAppGroup 调用（含多行，配对括号扫描）
def wrap_save_calls(text):
    out = []
    i = 0
    n = 0
    while i < len(text):
        m = re.compile(r'(let result = |return )self\.saveDataToAppGroup\(').search(text, i)
        if not m:
            out.append(text[i:])
            break
        start = m.start()
        out.append(text[i:start])
        prefix = m.group(1)
        open_paren = m.end() - 1
        depth = 0
        j = open_paren
        while j < len(text):
            if text[j] == '(':
                depth += 1
            elif text[j] == ')':
                depth -= 1
                if depth == 0:
                    break
            j += 1
        call_expr = text[open_paren:j+1]
        out.append(prefix + f'MainActor.assumeIsolated {{ self.saveDataToAppGroup{call_expr} }}')
        n += 1
        i = j + 1
    return ''.join(out), n

src, n_save = wrap_save_calls(src)
print(f"4. saveDataToAppGroup 调用包装: {n_save} 处")

open(path, "w").write(src)
print("补丁完成, 变更:", "是" if src != orig else "否")
