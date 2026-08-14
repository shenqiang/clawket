#!/usr/bin/env python3
"""给 expo-sharing-extension target 注入 SWIFT_STRICT_CONCURRENCY=minimal"""
import re, sys

path = "ios/Clawket.xcodeproj/project.pbxproj"
src = open(path).read()

# 定位 expo-sharing-extension target 块，拿到 buildConfigurationList
m = re.search(r'/\* expo-sharing-extension \*/ = \{\n(\s+)isa = PBXNativeTarget;[^}]*?buildConfigurationList = ([A-F0-9]{24})[^;]*;', src)
if not m:
    print("未找到 expo-sharing-extension target")
    sys.exit(1)
cfg_list = m.group(2)
print("buildConfigurationList:", cfg_list)

# 找到该 config list 引用的 buildConfigurations
m2 = re.search(r'/\* %s \*/ = \{\n(\s+)isa = XCConfigurationList;[^}]*?buildConfigurations = \((\n\s*[^)]*?)\)' % cfg_list, src)
if not m2:
    print("未找到 configuration list")
    sys.exit(1)
cfgs = re.findall(r'([A-F0-9]{24}) /\*', m2.group(2))
print("configs:", cfgs)

for cfg in cfgs:
    pat = re.compile(r'/\* %s \*/ = \{\n(\s+)isa = XCBuildConfiguration;[^}]*?buildSettings = \{(.*?)\n(\s+)\};' % cfg, re.S)
    mm = pat.search(src)
    if mm:
        indent = mm.group(1)
        settings = mm.group(2)
        if "SWIFT_STRICT_CONCURRENCY" not in settings:
            new_settings = settings + "\n" + indent + "SWIFT_STRICT_CONCURRENCY = minimal;"
            src = src[:mm.start()] + pat.sub(lambda x: x.group(0).replace(settings, new_settings), src, count=1)
            print("已注入 SWIFT_STRICT_CONCURRENCY 到", cfg)

open(path, "w").write(src)
print("pbxproj 补丁完成")
