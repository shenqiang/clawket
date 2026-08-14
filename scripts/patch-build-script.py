#!/usr/bin/env python3
"""给 build-macos.sh 注入 SE-0449 补丁调用 + 全局 Swift 5 设置
build-macos.sh 内部会 npm install（重置 node_modules），所以补丁必须
注入到脚本里，在 npm install 之后、ensure_pods 之前执行。"""
import re, sys

path = "scripts/build-macos.sh"
src = open(path).read()

# 1. 全局 Swift 5（build settings）
src = re.sub(
    r'CODE_SIGNING_REQUIRED=NO',
    'CODE_SIGNING_REQUIRED=NO SWIFT_VERSION=5.0 SWIFT_STRICT_CONCURRENCY=minimal',
    src,
)

# 2. 注入 SE-0449 补丁调用（在 ensure_pods 之前）
inject = 'python3 "$GITHUB_WORKSPACE/scripts/patch-expo-se0449.py" "$ROOT_DIR/../../node_modules/expo-modules-core/ios"\n'
if "patch-expo-se0449" not in src:
    src = src.replace("ensure_pods\n", inject + "ensure_pods\n", 1)
    print("SE-0449 补丁调用已注入")
else:
    print("SE-0449 补丁调用已存在")

open(path, "w").write(src)
print("build-macos.sh 补丁完成")
