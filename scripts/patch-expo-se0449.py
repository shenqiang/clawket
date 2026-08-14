#!/usr/bin/env python3
"""修复 expo-modules-core 的 SE-0449 语法（Swift 6.1+ 专属）
`extension X: @MainActor Protocol` 语法在 Swift 5 语言模式下不认识。
去掉 @MainActor 标注后变为 nonisolated，运行行为等价（纯协议声明）。
用法: python3 patch-expo-se0449.py [expo-modules-core-ios-path]
默认路径: node_modules/expo-modules-core/ios
"""
import re, sys, os

base = sys.argv[1] if len(sys.argv) > 1 else "node_modules/expo-modules-core/ios"
targets = [
    f"{base}/Core/Views/SwiftUI/SwiftUIHostingView.swift",
    f"{base}/Core/Views/SwiftUI/SwiftUIVirtualView.swift",
    f"{base}/Core/Views/ViewDefinition.swift",
]

changed = False
for path in targets:
    if not os.path.exists(path):
        print(f"跳过（不存在）: {path}")
        continue
    src = open(path).read()
    orig = src
    src = re.sub(r',\s*@MainActor\s+([A-Z]\w+)', r', \1', src)
    src = re.sub(r':\s*@MainActor\s+([A-Z]\w+)', r': \1', src)
    if src != orig:
        open(path, "w").write(src)
        changed = True
        print(f"已修复: {path}")
    else:
        print(f"无需修改: {path}")

if not changed:
    print("警告: 没有任何文件被修改，请检查路径")
    sys.exit(1)
print("SE-0449 补丁完成")
