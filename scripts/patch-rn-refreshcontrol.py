#!/usr/bin/env python3
"""修复 UIRefreshControl 在 Mac Catalyst 崩溃
根因: RN 的 RefreshControl 在 iOS 分支渲染 PullToRefreshViewNativeComponent，
Catalyst 下 UIRefreshControl 不受支持 → 抛 _UICatalystUnsupportedMacIdiomBehavior 崩溃。
修复: render() 开头加 Catalyst 判断，Platform.OS === 'macos' 时返回 null（禁用下拉刷新）。
用法: python3 patch-rn-refreshcontrol.py [repo_root]
"""
import os, sys

repo_root = sys.argv[1] if len(sys.argv) > 1 else "."
path = f"{repo_root}/node_modules/react-native/Libraries/Components/RefreshControl/RefreshControl.js"

if not os.path.exists(path):
    print(f"文件不存在: {path}")
    sys.exit(0)  # no-op 必须 exit 0

src = open(path).read()
orig = src

MARKER = "// Hermes catalyst patch: UIRefreshControl unsupported"
if MARKER in src:
    print("RefreshControl 已有 Catalyst 补丁，跳过")
    sys.exit(0)

# 在 render() 开头注入 Catalyst 判断
old = "  render(): React.Node {\n    if (Platform.OS === 'ios') {"
new = (
    "  render(): React.Node {\n"
    "    // Hermes catalyst patch: UIRefreshControl unsupported on Mac Catalyst\n"
    "    if (Platform.OS === 'macos') {\n"
    "      return null;\n"
    "    }\n"
    "    if (Platform.OS === 'ios') {"
)
if old not in src:
    print(f"未找到 render 锚点（RN 版本可能不同）")
    sys.exit(0)

src = src.replace(old, new, 1)
open(path, "w").write(src)
print(f"RefreshControl Catalyst 补丁已应用: {path}")
