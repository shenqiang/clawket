#!/usr/bin/env python3
"""修复 expo 包的 Swift 6.1+ / iOS 26 SDK 不兼容问题（Swift 5 兼容 + Catalyst）
1. expo-modules-core SE-0449 语法：`extension X: @MainActor P` → 去掉 @MainActor
2. expo-notifications: `isRepeatedDay` 是 iOS 26 SDK 新 API，Catalyst 编译（iPhoneOS
   18.5 SDK）下 #available(iOS 26) 检查不到该成员 → 删除该行（运行时 iOS 26 分支
   在旧系统不触发，功能无影响）
用法: python3 patch-expo-compat.py [仓库根路径]
"""
import re, sys, os

repo_root = sys.argv[1] if len(sys.argv) > 1 else "."
changed = False

# 1. expo-modules-core SE-0449
emc_base = f"{repo_root}/node_modules/expo-modules-core/ios"
se0449_targets = [
    f"{emc_base}/Core/Views/SwiftUI/SwiftUIHostingView.swift",
    f"{emc_base}/Core/Views/SwiftUI/SwiftUIVirtualView.swift",
    f"{emc_base}/Core/Views/ViewDefinition.swift",
]
for path in se0449_targets:
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
        print(f"SE-0449 已修复: {path}")

# 2. expo-notifications isRepeatedDay（iOS 26 SDK API，Catalyst 18.5 SDK 没有）
notif_path = f"{repo_root}/node_modules/expo-notifications/ios/ExpoNotifications/Notifications/DateComponentsSerializer.swift"
if os.path.exists(notif_path):
    src = open(notif_path).read()
    orig = src
    # 删除 isRepeatedDay 行（含前后空白）
    src = re.sub(r'^\s*serializedComponents\["isRepeatedDay"\] = dateComponents\.isRepeatedDay \?\? false\s*\n', '', src, flags=re.M)
    # 如果 #available(iOS 26.0, *) 块现在空了，也清理
    src = re.sub(r'if #available\(iOS 26\.0, \*\) \{\n\s*\}\n', '', src)
    if src != orig:
        open(path := notif_path, "w").write(src)
        changed = True
        print(f"expo-notifications isRepeatedDay 已移除: {notif_path}")
    else:
        print("expo-notifications: isRepeatedDay 未找到或已移除")
else:
    print(f"跳过（不存在）: {notif_path}")

if not changed:
    print("警告: 没有任何文件被修改，请检查路径")
    sys.exit(0)
print("expo 兼容补丁完成")
