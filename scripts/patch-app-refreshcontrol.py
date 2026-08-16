#!/usr/bin/env python3
"""预案 B：patch Clawket app 源码，Catalyst 下禁用所有 RefreshControl
原理：app 自己的源码被 Metro 强制追踪，改动必然进 bundle（不像 node_modules
有 hoisting/缓存问题）。这是最可靠的 JS 层方案。
做法：
1. 扫描 apps/mobile/src 所有含 refreshControl= 的 .tsx 文件
2. 在每个 refreshControl={ 后插入 "__CATALYST__ ? null : "（三元表达式，合法 JSX）
3. 在入口文件注入全局 __CATALYST__ = Platform.isMacCatalyst
用法: python3 patch-app-refreshcontrol.py [repo_root]
"""
import os, sys, re

repo_root = sys.argv[1] if len(sys.argv) > 1 else "."
src_dir = f"{repo_root}/apps/mobile/src"
if not os.path.exists(src_dir):
    print(f"src 目录不存在: {src_dir}")
    sys.exit(0)

MARKER = "__CATALYST__"
changed = 0

# 1. 替换所有 refreshControl={ 开头
for root, dirs, files in os.walk(src_dir):
    for f in files:
        if not f.endswith((".tsx", ".ts", ".jsx", ".js")):
            continue
        path = os.path.join(root, f)
        src = open(path).read()
        orig = src
        # 匹配 refreshControl={ 后跟 <RefreshControl 或 ( 换行等
        # 统一在 { 后插入 __CATALYST__ ? null : 
        src = re.sub(
            r'(refreshControl=\{)(?=\s*[<(])',
            r'\g<1>__CATALYST__ ? null : ',
            src,
        )
        if src != orig:
            open(path, "w").write(src)
            n = orig.count("refreshControl={") 
            changed += 1
            print(f"patched: {path} ({n} 处)")

# 2. 在入口文件注入全局 __CATALYST__
# 找入口：index.ts / App.tsx / 或 package.json main
entry = None
for cand in ["index.ts", "index.tsx", "App.tsx", "index.js"]:
    p = f"{repo_root}/apps/mobile/{cand}"
    if os.path.exists(p):
        entry = p
        break
if not entry:
    # 找 src 下可能的入口
    for cand in ["index.ts", "index.tsx"]:
        p = f"{src_dir}/{cand}"
        if os.path.exists(p):
            entry = p
            break
if entry:
    src = open(entry).read()
    if "__CATALYST__" not in src:
        inject = (
            "import { Platform } from 'react-native';\n"
            "// Hermes catalyst fix: disable RefreshControl on Mac Catalyst\n"
            "globalThis.__CATALYST__ = Platform.isMacCatalyst;\n"
            "\n"
        )
        # 注入到文件最顶部（所有 import 之前），确保任何模块加载时都已定义
        src = inject + src
        open(entry, "w").write(src)
        print(f"入口已注入 __CATALYST__: {entry}")
    else:
        print(f"入口已有 __CATALYST__: {entry}")
else:
    print("⚠️ 未找到入口文件，__CATALYST__ 未注入（运行时若缺会 TypeError）")

print(f"完成：{changed} 个文件被 patch")
