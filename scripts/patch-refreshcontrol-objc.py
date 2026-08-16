#!/usr/bin/env python3
"""终极修复：UIRefreshControl Catalyst 崩溃（ObjC +load swizzle，100% 可靠）
Hermes bytecode 让 JS 补丁不可靠（间歇性生效），React.framework 是 prebuilt。
方案：prebuild 后写 ObjC .m 文件，+load 自动 swizzle UIRefreshControl.didMoveToSuperview
为 no-op（Catalyst 下不调 super，避免抛 _UICatalystUnsupportedMacIdiomBehavior）。
+load 在 app 启动时自动执行，不依赖 React.framework。文件加入主 target 编译。
用法: python3 patch-refreshcontrol-objc.py [repo_root]
"""
import os, sys, re, hashlib

repo_root = sys.argv[1] if len(sys.argv) > 1 else "."
ios_dir = f"{repo_root}/ios"
if not os.path.exists(ios_dir):
    print(f"ios 目录不存在: {ios_dir}")
    sys.exit(0)

fix_file = f"{ios_dir}/UIRefreshControlCatalystFix.m"
if not os.path.exists(fix_file):
    objc_code = r'''#import <UIKit/UIKit.h>
#import <objc/runtime.h>

// Hermes catalyst fix: UIRefreshControl crashes on Mac Catalyst
// (_UICatalystUnsupportedMacIdiomBehavior). Swizzle didMoveToSuperview to no-op.

@implementation UIRefreshControl (HermesCatalystFix)

+ (void)load {
  static dispatch_once_t onceToken;
  dispatch_once(&onceToken, ^{
    if (@available(macCatalyst 13.0, *)) {
      Class cls = [UIRefreshControl class];
      SEL origSel = @selector(didMoveToSuperview);
      SEL newSel = @selector(hermes_catalystSafeDidMoveToSuperview);
      Method origMethod = class_getInstanceMethod(cls, origSel);
      Method newMethod = class_getInstanceMethod(cls, newSel);
      if (origMethod && newMethod) {
        method_exchangeImplementations(origMethod, newMethod);
      }
    }
  });
}

- (void)hermes_catalystSafeDidMoveToSuperview {
  // Intentionally empty: UIKit's didMoveToSuperview throws
  // _UICatalystUnsupportedMacIdiomBehavior on Catalyst, crashing the app.
}

@end
'''
    open(fix_file, "w").write(objc_code)
    print(f"ObjC fix 已写入: {fix_file}")
else:
    print(f"ObjC fix 已存在: {fix_file}")

# ---- 加入 Xcode 工程编译 ----
pbxproj = f"{ios_dir}/Clawket.xcodeproj/project.pbxproj"
if not os.path.exists(pbxproj):
    print(f"pbxproj 不存在: {pbxproj}")
    sys.exit(0)

src = open(pbxproj).read()
if "UIRefreshControlCatalystFix.m" in src:
    print("pbxproj 已有 fix 引用")
    sys.exit(0)

def gen_id(seed):
    return hashlib.md5(seed.encode()).hexdigest()[:24].upper()

file_ref_id = gen_id("UIRefreshControlCatalystFix.m fileRef")
build_file_id = gen_id("UIRefreshControlCatalystFix.m buildFile")

# 1. PBXFileReference（插到 AppDelegate.swift 的 fileRef 后）
fr_line = f'\t\t{file_ref_id} /* UIRefreshControlCatalystFix.m */ = {{isa = PBXFileReference; lastKnownFileType = sourcecode.c.objc; path = UIRefreshControlCatalystFix.m; sourceTree = "<group>"; }};'
m = re.search(r'(/\* AppDelegate\.swift \*/ = \{isa = PBXFileReference;[^\n]*\n)', src)
if m:
    src = src.replace(m.group(1), m.group(1) + fr_line + "\n", 1)
    print("PBXFileReference 已添加")
else:
    print("⚠️ 未找到 AppDelegate fileRef，尝试其他锚点")
    # 找任意 PBXFileReference 行
    m2 = re.search(r'(^\t\t[A-F0-9]{24} /\* .*? \*/ = \{isa = PBXFileReference;[^\n]*\n)', src, re.M)
    if m2:
        src = src.replace(m2.group(1), m2.group(1) + fr_line + "\n", 1)
        print("PBXFileReference 已添加（备用锚点）")

# 2. PBXBuildFile
bf_line = f'\t\t{build_file_id} /* UIRefreshControlCatalystFix.m in Sources */ = {{isa = PBXBuildFile; fileRef = {file_ref_id} /* UIRefreshControlCatalystFix.m */; }};'
m = re.search(r'(/\* AppDelegate\.swift in Sources \*/ = \{isa = PBXBuildFile;[^\n]*\n)', src)
if m:
    src = src.replace(m.group(1), m.group(1) + bf_line + "\n", 1)
    print("PBXBuildFile 已添加")

# 3. Compile Sources phase（找 AppDelegate.swift in Sources 的行）
m = re.search(r'^(\t\t\t[A-F0-9]{24} /\* AppDelegate\.swift in Sources \*/.*)$', src, re.M)
if m:
    src = src.replace(m.group(1), m.group(1) + "\n\t\t\t" + build_file_id + " /* UIRefreshControlCatalystFix.m in Sources */,", 1)
    print("Compile Sources 已添加")

open(pbxproj, "w").write(src)
print("pbxproj 更新完成")
