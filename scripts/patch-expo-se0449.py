#!/usr/bin/env python3
"""修复 expo-modules-core 的 SE-0449 语法（Swift 6.1+ 专属）
`extension X: @MainActor Protocol` 语法在 Swift 5 语言模式下不认识。
去掉 @MainActor 标注后变为 nonisolated，运行行为等价（纯协议声明）。
这样整个项目可以用 Swift 5 编译（RevenueCat 等所有 pod 都能过）。"""
import re, sys, glob

# expo-modules-core 的 iOS 源码目录
base = "node_modules/expo-modules-core/ios"
targets = [
    f"{base}/Core/Views/SwiftUI/SwiftUIHostingView.swift",
    f"{base}/Core/Views/SwiftUI/SwiftUIVirtualView.swift",
    f"{base}/Core/Views/ViewDefinition.swift",
]

for path in targets:
    try:
        src = open(path).read()
    except FileNotFoundError:
        print(f"跳过（不存在）: {path}")
        continue
    orig = src
    # 去掉 ", @MainActor Xxx"（协议继承位置的隔离标注）
    src = re.sub(r',\s*@MainActor\s+([A-Z]\w+)', r', \1', src)
    # 去掉 ": @MainActor Xxx"（extension 位置）
    src = re.sub(r':\s*@MainActor\s+([A-Z]\w+)', r': \1', src)
    if src != orig:
        open(path, "w").write(src)
        print(f"已修复: {path}")
        # 打印改动
        import difflib
        for line in difflib.unified_diff(orig.split('\n'), src.split('\n'), lineterm=''):
            if line.startswith('+') or line.startswith('-'):
                print(f"  {line[:90]}")
    else:
        print(f"无需修改: {path}")
