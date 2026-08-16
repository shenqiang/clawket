#!/usr/bin/env python3
"""终极修复 v3：UIRefreshControl Catalyst 崩溃（patch AppDelegate.swift）
pbxproj 注入 .m 文件不可靠（锚点不匹配）。
方案：直接 patch prebuild 生成的 AppDelegate.swift，在 didFinishLaunchingWithOptions
里注入 UIRefreshControl didMoveToSuperview 的 swizzle（Catalyst 下 no-op）。
AppDelegate 是主 target 必然编译的文件，100% 可靠。
用法: python3 patch-refreshcontrol-appdelegate.py [repo_root]
"""
import os, sys

repo_root = sys.argv[1] if len(sys.argv) > 1 else "."
# AppDelegate 路径：ios/<AppName>/AppDelegate.swift（找 Clawket）
candidates = [
    f"{repo_root}/ios/Clawket/AppDelegate.swift",
    f"{repo_root}/ios/clawket/AppDelegate.swift",
]
app_delegate = next((p for p in candidates if os.path.exists(p)), None)
if not app_delegate:
    # 搜索 ios 目录
    ios_dir = f"{repo_root}/ios"
    if os.path.exists(ios_dir):
        for root, dirs, files in os.walk(ios_dir):
            if "AppDelegate.swift" in files and "Pods" not in root:
                app_delegate = os.path.join(root, "AppDelegate.swift")
                break
if not app_delegate:
    print(f"未找到 AppDelegate.swift（ios 目录: {ios_dir if 'ios_dir' in dir() else '?'}）")
    sys.exit(0)

print(f"AppDelegate: {app_delegate}")
src = open(app_delegate).read()

MARKER = "HermesCatalystRefreshFix"
if MARKER in src:
    print("AppDelegate 已有 swizzle 补丁，跳过")
    sys.exit(0)

# 在文件头部加 swizzle 工具类（Swift 全局类，自动注册）
swizzle_code = '''
// === HermesCatalystRefreshFix: UIRefreshControl crashes on Mac Catalyst ===
// (_UICatalystUnsupportedMacIdiomBehavior). Swizzle UIRefreshControl's own
// didMoveToSuperview to no-op on Catalyst.
import ObjectiveC.runtime
import UIKit

private var hermesCatalystFixInstalled = false

extension UIRefreshControl {
  @objc func hermes_safeDidMoveToSuperview() {
    // Intentionally empty: UIKit's UIRefreshControl.didMoveToSuperview throws
    // _UICatalystUnsupportedMacIdiomBehavior on Catalyst, crashing the app.
  }

  static func hermesInstallCatalystRefreshFix() {
    guard #available(macCatalyst 13.0, *), !hermesCatalystFixInstalled else { return }
    hermesCatalystFixInstalled = true
    let cls = UIRefreshControl.self
    let orig = #selector(UIRefreshControl.didMoveToSuperview)
    guard let origMethod = class_getInstanceMethod(cls, orig) else { return }
    let newMethod = class_getInstanceMethod(cls, #selector(UIRefreshControl.hermes_safeDidMoveToSuperview))
    guard let newMethod = newMethod else { return }
    method_exchangeImplementations(origMethod, newMethod)
  }
}
'''

# 1. 在 import 区后插入 swizzle 定义
# 找第一个 import 后的位置（在 @main / class AppDelegate 之前）
main_idx = src.find("@main")
if main_idx < 0:
    main_idx = src.find("class AppDelegate")
if main_idx < 0:
    print("未找到 @main / class AppDelegate")
    sys.exit(0)

# 在 @main 前插入
src = src[:main_idx] + swizzle_code + "\n" + src[main_idx:]

# 2. 在 didFinishLaunchingWithOptions 方法体开头注入触发
marker = "didFinishLaunchingWithOptions"
idx = src.find(marker)
if idx > 0:
    brace = src.find("{", idx)
    if brace > 0:
        inject = "\n        UIRefreshControl.hermesInstallCatalystRefreshFix()\n"
        src = src[:brace+1] + inject + src[brace+1:]
        print("swizzle 触发已注入 didFinishLaunchingWithOptions")
    else:
        print("⚠️ 未找到方法体 {")
else:
    # 找 applicationDidFinishLaunching
    marker2 = "applicationDidFinishLaunching"
    idx2 = src.find(marker2)
    if idx2 > 0:
        brace = src.find("{", idx2)
        if brace > 0:
            inject = "\n        UIRefreshControl.hermesInstallCatalystRefreshFix()\n"
            src = src[:brace+1] + inject + src[brace+1:]
            print("swizzle 触发已注入 applicationDidFinishLaunching")
        else:
            print("⚠️ 未找到 applicationDidFinishLaunching 方法体")
    else:
        print("⚠️ 未找到启动方法，swizzle 定义已加但未触发（+load 不可用于 Swift 枚举）")

open(app_delegate, "w").write(src)
print(f"AppDelegate 已 patch: {app_delegate}")
