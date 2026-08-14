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

# 2. 注入 expo 兼容补丁调用（在 ensure_pods 之前，npm install 之后）
inject = 'python3 "$GITHUB_WORKSPACE/scripts/patch-expo-compat.py" "$ROOT_DIR/../.."\n'
if "patch-expo-compat" not in src:
    src = src.replace("ensure_pods\n", inject + "ensure_pods\n", 1)
    print("expo 兼容补丁调用已注入")
else:
    print("expo 兼容补丁调用已存在")

# 3. 修复 resolve_destination：该 scheme 不支持 Mac Catalyst，唯一 Mac destination
# 是 "Designed for [iPad,iPhone]"（iOS app on Mac，Apple Silicon 直接运行）。
# 用其 id 作为默认 destination；fallback 不再用 iOS 模拟器 id。
src = src.replace(
    'DESTINATION="${MACOS_DESTINATION:-platform=macOS,variant=Mac Catalyst}"',
    'DESTINATION="${MACOS_DESTINATION:-id=00a6f2c536c1c41032523d3d9814197c3c82bc50}"',
)
# 同时让 resolve_destination 不再 fallback 到 id=...（iOS destination）
src = src.replace(
    'if [[ -n "$mac_id" ]]; then\n    echo "id=${mac_id}"\n    return\n  fi',
    'if [[ -n "$mac_id" ]]; then\n    echo "$DESTINATION"\n    return\n  fi',
)
print("resolve_destination 已修复（iOS app on Mac destination）")

open(path, "w").write(src)
print("build-macos.sh 补丁完成")
