#!/usr/bin/env python3
"""精确修复 expo-sharing-extension 的 Swift 6 并发错误（基于真实模板源码）
1. 类加 @MainActor 标注
2. loadItem 完成回调是 nonisolated @Sendable 闭包，内部调用 MainActor 方法需
   MainActor.assumeIsolated 包装（返回 SharePayload? 与 continuation.resume 类型匹配）
只做精确字符串替换，不依赖行号。"""
import re, sys

path = "ios/expo-sharing-extension/ShareIntoViewController.swift"
src = open(path).read()
orig = src

# 1. 类加 @MainActor
if not re.search(r'@MainActor\s*\nclass ShareIntoViewController', src):
    src = re.sub(
        r'^(class ShareIntoViewController: SLComposeServiceViewController)',
        r'@MainActor\n\1',
        src,
        count=1,
        flags=re.M,
    )
    print("1. 类添加 @MainActor")
else:
    print("1. 类已有 @MainActor")

# 2. 包装 copyAndProcessFile 调用（单行形式: let result = self.copyAndProcessFile(url: url, type: type)）
pat_copy = re.compile(r'let result = self\.copyAndProcessFile\(url: url, type: type\)')
src, n_copy = pat_copy.subn(
    'let result = MainActor.assumeIsolated { self.copyAndProcessFile(url: url, type: type) }',
    src,
)
print(f"2. copyAndProcessFile 调用包装: {n_copy} 处")

# 3. 包装 saveDataToAppGroup 调用（含多行调用，从 "let result = self.saveDataToAppGroup(" 到匹配的 ")"）
# 用逐字符扫描找配对括号
def wrap_save_calls(text):
    out = []
    i = 0
    n = 0
    while i < len(text):
        # 找 "let result = self.saveDataToAppGroup(" 或 "return self.saveDataToAppGroup("
        m = re.compile(r'(let result = |return )self\.saveDataToAppGroup\(').search(text, i)
        if not m:
            out.append(text[i:])
            break
        start = m.start()
        out.append(text[i:start])
        prefix = m.group(1)  # "let result = " 或 "return "
        # 找到调用开头的 "("
        open_paren = m.end() - 1
        # 配对括号
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
        call_expr = text[open_paren:j+1]  # 完整 "(...)"
        out.append(prefix + f'MainActor.assumeIsolated {{ self.saveDataToAppGroup{call_expr} }}')
        n += 1
        i = j + 1
    return ''.join(out), n

src, n_save = wrap_save_calls(src)
print(f"3. saveDataToAppGroup 调用包装: {n_save} 处")

open(path, "w").write(src)
print("补丁完成, 变更:", "是" if src != orig else "否")

# 验证
for line in src.split('\n'):
    if 'assumeIsolated' in line or '@MainActor' in line:
        print("  >", line.strip()[:100])
