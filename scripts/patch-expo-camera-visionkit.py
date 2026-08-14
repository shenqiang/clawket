#!/usr/bin/env python3
"""修复 expo-camera 的 VisionKit DataScanner API 在 Mac Catalyst 不可用
Catalyst 编译时 targetEnvironment(macCatalyst)=true，DataScannerViewController/
RecognizedItem 标记 unavailable。只排除 VisionKit 专属声明，保留通用代码：
- VisionScannerDelegate.swift：只包 VisionScannerDelegate 类（保留 ScannerResultHandler 协议）
- BarcodeScannerUtils.swift：只包 visionDataScannerObjectToDictionary 方法（保留通用方法）
- CameraViewModule.swift：ScannerContext + launchScanner/dismissScanner + onItemScanned
用法: python3 patch-expo-camera-visionkit.py [repo_root]
"""
import os, sys

repo_root = sys.argv[1] if len(sys.argv) > 1 else "."
base = f"{repo_root}/node_modules/expo-camera/ios"
changed = False
GUARD = "#if !targetEnvironment(macCatalyst)"
END = "#endif"

def wrap_block(src, anchor, include_anchor=True):
    """找到 anchor 所在块（从 anchor 到匹配 }），返回包裹后的 src
    若 anchor 前一行是 @available，则从 @available 开始包（属性不能跨 #if）"""
    i = src.find(anchor)
    if i < 0:
        return src, False
    start = i if include_anchor else i + len(anchor)
    # 检查 anchor 前是否有 @available 标注（往前找最近的非空行）
    prev_newline = src.rfind("\n", 0, i)
    prev_line = src[prev_newline+1:i].strip()
    while prev_line == "" and prev_newline > 0:
        prev_newline = src.rfind("\n", 0, prev_newline)
        prev_line = src[prev_newline+1:i].strip()
    if prev_line.startswith("@available") or prev_line.startswith("@MainActor"):
        start = prev_newline + 1
        # 可能还有连续属性行（@available 前还有 @MainActor 等），继续往前
        while True:
            prev_newline2 = src.rfind("\n", 0, start - 1)
            if prev_newline2 < 0:
                break
            prev_line2 = src[prev_newline2+1:start].strip()
            if prev_line2.startswith("@"):
                start = prev_newline2 + 1
            else:
                break
    # 数大括号找块结束
    depth = 0
    k = i
    while k < len(src):
        if src[k] == '{': depth += 1
        elif src[k] == '}':
            depth -= 1
            if depth == 0:
                break
        k += 1
    if k >= len(src):
        return src, False
    block = src[start:k+1]
    if GUARD in block:
        return src, False
    return src[:start] + GUARD + "\n" + block + "\n" + END + src[k+1:], True

# 1. VisionScannerDelegate.swift：只包 VisionScannerDelegate 类（保留 ScannerResultHandler 协议）
p = f"{base}/Current/VisionScannerDelegate.swift"
if os.path.exists(p):
    src = open(p).read()
    orig = src
    # 撤销之前的整文件包裹（如果有）
    if src.startswith(GUARD + "\n") and src.rstrip().endswith(END):
        src = src[len(GUARD)+1:].rsplit(END, 1)[0].rstrip("\n") + "\n"
    src, ok = wrap_block(src, "class VisionScannerDelegate: NSObject, DataScannerViewControllerDelegate {")
    if ok:
        open(p, "w").write(src)
        changed = True
        print(f"VisionScannerDelegate 类已条件编译: {p}")
        # 验证协议保留
        if "protocol ScannerResultHandler" in src:
            print("  ScannerResultHandler 协议已保留")
    else:
        open(p, "w").write(src)
        print(f"VisionScannerDelegate 无需修改或已处理: {p}")
# 2. BarcodeScannerUtils.swift：只包 visionDataScannerObjectToDictionary
p = f"{base}/Current/BarcodeScannerUtils.swift"
if os.path.exists(p):
    src = open(p).read()
    orig = src
    if src.startswith(GUARD + "\n") and src.rstrip().endswith(END):
        src = src[len(GUARD)+1:].rsplit(END, 1)[0].rstrip("\n") + "\n"
    src, ok = wrap_block(src, "  static func visionDataScannerObjectToDictionary(item: RecognizedItem.Barcode) -> [String: Any] {")
    if ok:
        open(p, "w").write(src)
        changed = True
        print(f"visionDataScannerObjectToDictionary 已条件编译: {p}")
    else:
        open(p, "w").write(src)
        print(f"BarcodeScannerUtils 无需修改或已处理: {p}")

# 3. CameraViewModule.swift：VisionKit 声明
p = f"{base}/CameraViewModule.swift"
if os.path.exists(p):
    src = open(p).read()
    orig = src
    # 撤销之前的包裹（恢复原状再重新精确包）——简单起见只检查是否已包
    if GUARD in src:
        print(f"CameraViewModule 已有条件编译: {p}")
    else:
        # a) ScannerContext struct
        src, ok = wrap_block(src, "struct ScannerContext {")
        # b) scannerContext 属性
        i = src.find("  private var scannerContext: ScannerContext?")
        if i >= 0 and GUARD not in src[i-50:i+60]:
            src = src[:i] + GUARD + "\n" + src[i:src.find("\n", i)+1] + END + "\n" + src[src.find("\n", i)+1:]
            ok = True
        # c) launchScanner AsyncFunction 到 dismissScanner 结束
        i_start = src.find('    AsyncFunction("launchScanner")')
        if i_start >= 0:
            i_end = src.find('    AsyncFunction("dismissScanner")', i_start)
            if i_end >= 0:
                depth = 0
                k = i_end
                while k < len(src):
                    if src[k] == '{': depth += 1
                    elif src[k] == '}':
                        depth -= 1
                        if depth == 0:
                            break
                    k += 1
                if k > i_end:
                    block = src[i_start:k+1]
                    if GUARD not in block:
                        src = src[:i_start] + GUARD + "\n" + block + "\n" + END + src[k+1:]
                        ok = True
        # d) 私有方法 launchScanner/dismissScanner
        for fn in ['  private func launchScanner(with options: VisionScannerOptions?) {',
                   '  private func dismissScanner() {']:
            i = src.find(fn)
            if i >= 0:
                seg_start = src.rfind("@available", max(0, i-200), i)
                if seg_start < 0:
                    seg_start = src.rfind("@MainActor", max(0, i-200), i)
                    if seg_start < 0:
                        seg_start = i
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
                        ok = True
        # e) onItemScanned —— 保留！它是 ScannerResultHandler 协议要求的实现，
        #    且实现只调 sendEvent（不引用 VisionKit 类型），必须始终编译。
        #    不包条件编译。
        if src != orig:
            open(p, "w").write(src)
            changed = True
            print(f"CameraViewModule 条件编译完成: {p}")
            print(f"  #if: {src.count(GUARD)}  #endif: {src.count(END)}")
        else:
            print(f"CameraViewModule 无变化: {p}")

if not changed:
    print("警告: 没有文件被修改")
print("expo-camera VisionKit 补丁完成")
