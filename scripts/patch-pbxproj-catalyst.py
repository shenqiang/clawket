#!/usr/bin/env python3
"""给 Clawket target 的 pbxproj 做 Catalyst 修复：
1. 加 SUPPORTS_MACCATALYST=YES（启用 Mac Catalyst）
2. 移除主 app 对 expo-sharing-extension 的嵌入引用（Catalyst 下 extension 不编译，
   主 app 的 Embed Foundation Extensions phase 拷贝会失败）
"""
import re, sys

path = "ios/Clawket.xcodeproj/project.pbxproj"
src = open(path).read()
orig = src

# 1. 定位 Clawket target 的 buildConfigurationList
m = re.search(r'/\* Clawket \*/ = \{\n[^}]*?buildConfigurationList = ([A-F0-9]{24})[^;]*;', src)
if m:
    cfg_list = m.group(1)
    list_pat = re.compile(re.escape(cfg_list) + r'[^=]*=\s*\{')
    lm = list_pat.search(src)
    if lm:
        brace = lm.end() - 1
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
                bs_marker = cfg_block.find('buildSettings = {')
                if bs_marker >= 0:
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
                    print(f"已注入 SUPPORTS_MACCATALYST 到 {cfg}")

# 2. 找到 Embed Foundation Extensions build phase（Clawket target 的 buildPhases 里）
# 移除对 expo-sharing-extension 的引用
# 先找 Clawket target 块
target_m = re.search(r'/\* Clawket \*/ = \{\n(.*?)\n\};', src, re.S)
if target_m:
    tblock = target_m.group(1)
    # 找 buildPhases 列表
    bp_m = re.search(r'buildPhases = \(\n(.*?)\n\s*\);', tblock, re.S)
    if bp_m:
        phases = bp_m.group(1)
        phase_ids = re.findall(r'([A-F0-9]{24}) /\* ([^*]+) \*/', phases)
        for pid, pname in phase_ids:
            if 'CopyFiles' in pname or 'Embed' in pname:
                # 找该 phase 的块
                pm = re.search(re.escape(pid) + r'[^=]*=\s*\{', src)
                if pm:
                    brace = src.find('{', pm.end()-1)
                    depth = 0
                    k = brace
                    while k < len(src):
                        if src[k] == '{': depth += 1
                        elif src[k] == '}':
                            depth -= 1
                            if depth == 0: break
                        k += 1
                    phase_block = src[brace:k+1]
                    if 'expo-sharing-extension' in phase_block:
                        # 移除 extension 的 file 引用行
                        new_block = re.sub(
                            r'\s*[A-F0-9]{24} /\* expo-sharing-extension\.appex \*/.*?\n',
                            '',
                            phase_block,
                        )
                        if new_block != phase_block:
                            src = src.replace(phase_block, new_block)
                            print(f"已从 {pname} 移除 expo-sharing-extension 引用")
                        # 同时移除 files 列表里的引用（在 phase 块外）
                        # 主 app target 的 dependencies 里 extension 引用也移除
                    else:
                        print(f"{pname} 不含 extension 引用")

# 3. 移除主 app target 对 extension target 的 dependency
src = re.sub(r'\s*[A-F0-9]{24} /\* expo-sharing-extension \*/,\n', '', src)
# 移除 files 列表中对 extension 的引用
src = re.sub(r'\s*[A-F0-9]{24} /\* expo-sharing-extension\.appex in (?:Embed|CopyFiles)[^*]*\*/,\n', '', src)

open(path, "w").write(src)
if 'SUPPORTS_MACCATALYST = YES' in src:
    print("OK: SUPPORTS_MACCATALYST=YES 已确认")
else:
    print("WARN: SUPPORTS_MACCATALYST 未确认")
print("pbxproj Catalyst 补丁完成")
