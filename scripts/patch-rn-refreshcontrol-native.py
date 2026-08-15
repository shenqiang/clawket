#!/usr/bin/env python3
"""修复 UIRefreshControl 在 Mac Catalyst 崩溃（原生层）
JS 层 patch（RefreshControl render 返回 null）不够——Fabric 原生组件
RCTPullToRefreshViewComponentView 的 _attach 仍会创建 UIRefreshControl 并赋给
scrollView.refreshControl，Catalyst 下触发 _UICatalystUnsupportedMacIdiomBehavior。
修复: 在 _attach 的赋值逻辑外包 #if !targetEnvironment(macCatalyst)，Catalyst 下跳过。
用法: python3 patch-rn-refreshcontrol-native.py [repo_root]
"""
import os, sys

repo_root = sys.argv[1] if len(sys.argv) > 1 else "."
path = f"{repo_root}/node_modules/react-native/React/Fabric/Mounting/ComponentViews/ScrollView/RCTPullToRefreshViewComponentView.mm"

if not os.path.exists(path):
    print(f"文件不存在: {path}")
    sys.exit(0)

src = open(path).read()
orig = src

MARKER = "Hermes catalyst patch"
if MARKER in src:
    print("RCTPullToRefreshViewComponentView 已有 Catalyst 补丁，跳过")
    sys.exit(0)

# 包住 _attach 里的 @available(macCatalyst) 赋值块
old = """  if (@available(macCatalyst 13.1, *)) {
    _scrollViewComponentView.scrollView.refreshControl = _refreshControl;

    // This ensures that layoutSubviews is called. Without this, recycled instances won't refresh on mount
    [self setNeedsLayout];
  }"""
new = """#if !targetEnvironment(macCatalyst)
  // Hermes catalyst patch: UIRefreshControl unsupported on Mac Catalyst
  if (@available(macCatalyst 13.1, *)) {
    _scrollViewComponentView.scrollView.refreshControl = _refreshControl;

    // This ensures that layoutSubviews is called. Without this, recycled instances won't refresh on mount
    [self setNeedsLayout];
  }
#endif"""

if old not in src:
    print("未找到 _attach 锚点（RN 版本可能不同）")
    sys.exit(0)

src = src.replace(old, new, 1)
open(path, "w").write(src)
print(f"RCTPullToRefreshViewComponentView Catalyst 补丁已应用: {path}")
