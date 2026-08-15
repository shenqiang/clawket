#!/usr/bin/env python3
"""修复 UIRefreshControl 在 Mac Catalyst 崩溃（ScrollView 层）
RefreshControl.js render 返回 null 不够——ScrollView.js 检查 this.props.refreshControl
是否非 null（组件实例非 null），Catalyst 下仍渲染 → Fabric 挂载原生组件 → 崩。
修复: ScrollView.js 里在读取 refreshControl 后，Catalyst 下强制置 null。
用法: python3 patch-rn-scrollview-refreshcontrol.py [repo_root]
"""
import os, sys

repo_root = sys.argv[1] if len(sys.argv) > 1 else "."
path = f"{repo_root}/node_modules/react-native/Libraries/Components/ScrollView/ScrollView.js"

if not os.path.exists(path):
    print(f"文件不存在: {path}")
    sys.exit(0)

src = open(path).read()
orig = src

MARKER = "Hermes catalyst patch"
if MARKER in src:
    print("ScrollView 已有 Catalyst 补丁，跳过")
    sys.exit(0)

# 在 const refreshControl = this.props.refreshControl; 后加 Catalyst 置 null
old = "    const refreshControl = this.props.refreshControl;"
new = (
    "    // Hermes catalyst patch: UIRefreshControl unsupported on Mac Catalyst\n"
    "    let refreshControl = this.props.refreshControl;\n"
    "    if (Platform.isMacCatalyst) {\n"
    "      refreshControl = null;\n"
    "    }"
)
if old not in src:
    print(f"未找到 refreshControl 锚点（RN 版本可能不同）")
    sys.exit(0)

src = src.replace(old, new, 1)
open(path, "w").write(src)
print(f"ScrollView RefreshControl Catalyst 补丁已应用: {path}")
