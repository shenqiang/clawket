#!/usr/bin/env python3
"""修复 expo-camera 的 VisionKit DataScanner API 在 Mac Catalyst 不可用
Catalyst 编译时 targetEnvironment(macCatalyst)=true，DataScannerViewController/
RecognizedItem 标记 unavailable。策略：精确字符串替换（不做区域匹配）：
- VisionScannerDelegate.swift / BarcodeScannerUtils.swift：整文件条件编译
- CameraViewModule.swift：把 launchScanner/dismissScanner 的 AsyncFunction 和
  私有方法用 #if 包住（精确字符串锚点）
用法: python3 patch-expo-camera-visionkit.py [repo_root]
"""
import os, sys

repo_root = sys.argv[1] if len(sys.argv) > 1 else "."
base = f"{repo_root}/node_modules/expo-camera/ios"
changed = False
GUARD = "#if !targetEnvironment(macCatalyst)"
END = "#endif"

# 1 & 2: 纯 VisionKit 文件
for rel in ["Current/VisionScannerDelegate.swift", "Current/BarcodeScannerUtils.swift"]:
    p = f"{base}/{rel}"
    if os.path.exists(p):
        src = open(p).read()
        if GUARD not in src:
            open(p, "w").write(GUARD + "\n" + src + "\n" + END + "\n")
            changed = True
            print(f"整文件条件编译: {rel}")
        else:
            print(f"已有条件编译: {rel}")

# 3. CameraViewModule.swift：精确字符串替换
p = f"{base}/CameraViewModule.swift"
if os.path.exists(p):
    src = open(p).read()
    orig = src
    if GUARD in src:
        print("CameraViewModule 已有条件编译")
    else:
        # a) ScannerContext struct（3 行）
        src = src.replace(
            "struct ScannerContext {\n",
            GUARD + "\nstruct ScannerContext {\n",
            1,
        )
        # struct 结束的 "}"（ScannerContext 只有 3 行，找它后面的第一个 "}"）
        marker = "struct ScannerContext {"
        idx = src.find(marker)
        if idx >= 0:
            close = src.find("\n}\n", idx)
            if close >= 0:
                src = src[:close+2] + "\n" + END + src[close+2:]

        # b) scannerContext 属性
        src = src.replace(
            "  private var scannerContext: ScannerContext?\n",
            GUARD + "\n  private var scannerContext: ScannerContext?\n" + END + "\n",
            1,
        )

        # c) launchScanner AsyncFunction 块（精确锚点，包到 dismissScanner 结束）
        anchor_start = '    AsyncFunction("launchScanner")'
        anchor_end = '    AsyncFunction("dismissScanner")'
        i_start = src.find(anchor_start)
        if i_start >= 0:
            # 找 dismissScanner 块结束（下一个 AsyncFunction 或非缩进 }
            j = src.find(anchor_end, i_start)
            if j >= 0:
                # 找 dismissScanner 块结束：从 j 开始数大括号
                depth = 0
                k = j
                while k < len(src):
                    if src[k] == '{': depth += 1
                    elif src[k] == '}':
                        depth -= 1
                        if depth == 0:
                            break
                    k += 1
                if k > j:
                    block = src[i_start:k+1]
                    # 检查 block 是否已被包
                    if GUARD not in block:
                        src = src[:i_start] + GUARD + "\n" + block + "\n" + END + src[k+1:]

        # d) 私有方法 launchScanner/dismissScanner（@available 开始，含 @MainActor）
        for fn_anchor in ['  private func launchScanner(with options: VisionScannerOptions?) {',
                          '  private func dismissScanner() {']:
            i = src.find(fn_anchor)
            if i >= 0:
                # 往前找 @available（第一个属性标注，可能是 @available 或 @MainActor）
                seg_start = src.rfind("@available", max(0, i-200), i)
                if seg_start < 0:
                    # 没有 @available 就找 @MainActor
                    seg_start = src.rfind("@MainActor", max(0, i-200), i)
                    if seg_start < 0:
                        seg_start = i
                # 找方法结束（方法体最后一个 }）
                depth = 0
                k = i
                while k < len(src):
                    if src[k] == '{': depth += 1
                    elif src[k] == '}':
                        depth -= 1
                        if depth == 0:
                            break
                    k += 1
                if k > i:
                    block = src[seg_start:k+1]
                    if GUARD not in block:
                        src = src[:seg_start] + GUARD + "\n" + block + "\n" + END + src[k+1:]

        # e) onItemScanned
        anchor = "  func onItemScanned(result: [String: Any]) {"
        i = src.find(anchor)
        if i >= 0:
            depth = 0
            k = i
            while k < len(src):
                if src[k] == '{': depth += 1
                elif src[k] == '}':
                    depth -= 1
                    if depth == 0:
                        break
                k += 1
            if k > i:
                block = src[i:k+1]
                if GUARD not in block:
                    src = src[:i] + GUARD + "\n" + block + "\n" + END + src[k+1:]

        if src != orig:
            open(p, "w").write(src)
            changed = True
            print("CameraViewModule 条件编译完成")
            # 验证
            print(f"  #if: {src.count(GUARD)}  #endif: {src.count(END)}")
            # 检查未被包住的 DataScanner
            lines = src.split('\n')
            for n, l in enumerate(lines, 1):
                if 'DataScanner' in l or 'RecognizedItem' in l:
                    # 向前找最近 #if/#endif
                    g = max([x for x in range(n-1) if GUARD in lines[x]], default=-1)
                    e = max([x for x in range(n-1) if lines[x].strip() == END], default=-1)
                    st = "OK(已包)" if g > e else "未包!!"
                    print(f"  行{n} {st}: {l.strip()[:60]}")
        else:
            print("CameraViewModule 无变化")

if not changed:
    print("警告: 没有文件被修改")
print("expo-camera VisionKit 补丁完成")
