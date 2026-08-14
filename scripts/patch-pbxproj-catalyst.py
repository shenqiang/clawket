#!/usr/bin/env python3
"""给 Clawket target 的 pbxproj 加 SUPPORTS_MACCATALYST=YES（启用 Mac Catalyst）
Expo 的 supportsMac 字段在 SDK 55 可能不生效，直接改 pbxproj 最可靠。
"""
import re, sys

path = "ios/Clawket.xcodeproj/project.pbxproj"
src = open(path).read()
orig = src

# 1. 定位 Clawket target 的 buildConfigurationList
m = re.search(r'/\* Clawket \*/ = \{\n[^}]*?buildConfigurationList = ([A-F0-9]{24})[^;]*;', src)
if not m:
    print("FAIL: 未找到 Clawket target")
    sys.exit(1)
cfg_list = m.group(1)
print("buildConfigurationList:", cfg_list)

# 2. 找到该 config list 引用的 buildConfigurations
list_pat = re.compile(re.escape(cfg_list) + r'[^=]*=\s*\{')
lm = list_pat.search(src)
if lm:
    brace = lm.end() - 1
    # 提取配对块
    depth = 0
    i = brace
    while i < len(src):
        if src[i] == '{': depth += 1
        elif src[i] == '}':
            depth -= 1
            if depth == 0: break
        i += 1
    block = src[brace:i+1]
    cfgs = re.findall(r'([A-F0-9]{24}) /\* (?:Release|Debug) \*/', block)
    print("configs:", cfgs)
else:
    print("FAIL: 未找到 configuration list")
    sys.exit(1)

# 3. 在每个 XCBuildConfiguration 里注入 SUPPORTS_MACCATALYST
added = 0
for cfg in cfgs:
    cfg_marker = src.find(cfg)
    if cfg_marker < 0: continue
    cfg_brace = src.find('{', cfg_marker)
    depth = 0
    i = cfg_brace
    while i < len(src):
        if src[i] == '{': depth += 1
        elif src[i] == '}':
            depth -= 1
            if depth == 0: break
        i += 1
    cfg_block = src[cfg_brace:i+1]
    if 'SUPPORTS_MACCATALYST' not in cfg_block:
        # 在 buildSettings 块内追加
        bs_marker = cfg_block.find('buildSettings = {')
        if bs_marker < 0: continue
        bs_brace = cfg_block.find('{', bs_marker)
        depth = 0
        j = bs_brace
        while j < len(cfg_block):
            if cfg_block[j] == '{': depth += 1
            elif cfg_block[j] == '}':
                depth -= 1
                if depth == 0: break
            j += 1
        bs_block = cfg_block[bs_brace:j+1]
        new_bs = bs_block[:-1] + '\n\t\t\t\tSUPPORTS_MACCATALYST = YES;\n\t\t\t}'
        src = src.replace(cfg_block, cfg_block.replace(bs_block, new_bs), 1)
        added += 1
        print(f"已注入 SUPPORTS_MACCATALYST 到 {cfg}")

if added == 0:
    print("未注入任何配置（可能已存在）")

open(path, "w").write(src)
if 'SUPPORTS_MACCATALYST = YES' in src:
    print("OK: SUPPORTS_MACCATALYST=YES 已写入")
else:
    print("WARN: 未确认写入")
