#!/usr/bin/env python3
"""修复 UIRefreshControl 在 Mac Catalyst 崩溃（JS 层，v2）
Catalyst 下 Platform.OS === 'ios'（不是 'macos'）——v1 补丁判断错误无效。
正确判断: Platform.isMacCatalyst（RN 提供，Catalyst 下为 true）。
修复: RefreshControl.render() 开头加 Platform.isMacCatalyst 判断返回 null。
用法: python3 patch-rn-refreshcontrol.py [repo_root]
"""
import os, sys

repo_root = sys.argv[1] if len(sys.argv) > 1 else "."
path = f"{repo_root}/node_modules/react-native/Libraries/Components/RefreshControl/RefreshControl.js"

if not os.path.exists(path):
    print(f"文件不存在: {path}")
    sys.exit(0)

src = open(path).read()
orig = src

MARKER = "Hermes catalyst patch"
if MARKER in src:
    print("RefreshControl 已有 Catalyst 补丁，跳过")
    sys.exit(0)

# v1 的 Platform.OS === 'macos' 判断（错误，替换掉）
old_v1 = "    // Hermes catalyst patch: UIRefreshControl unsupported on Mac Catalyst\n    if (Platform.OS === 'macos') {\n      return null;\n    }\n"
if old_v1 in src:
    src = src.replace(old_v1, "", 1)
    print("已移除 v1 错误补丁")

old = "  render(): React.Node {\n    if (Platform.OS === 'ios') {"
new = (
    "  render(): React.Node {\n"
    "    // Hermes catalyst patch v2: UIRefreshControl unsupported on Mac Catalyst\n"
    "    if (Platform.isMacCatalyst === true || Platform.isMacCatalyst) {\n"
    "      return null;\n"
    "    }\n"
    "    if (Platform.OS === 'ios') {"
)
if old not in src:
    print(f"未找到 render 锚点（RN 版本可能不同）")
    sys.exit(0)

src = src.replace(old, new, 1)
open(path, "w").write(src)
print(f"RefreshControl Catalyst 补丁已应用 (v2, Platform.isMacCatalyst): {path}")
