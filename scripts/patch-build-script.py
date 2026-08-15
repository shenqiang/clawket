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
# expo-camera VisionKit 补丁（单独脚本，含复杂条件编译逻辑）
inject2 = 'python3 "$GITHUB_WORKSPACE/scripts/patch-expo-camera-visionkit.py" "$ROOT_DIR/../.."\n'
if "patch-expo-camera-visionkit" not in src:
    src = src.replace("ensure_pods\n", inject2 + "ensure_pods\n", 1)
    print("expo-camera VisionKit 补丁调用已注入")
else:
    print("expo-camera VisionKit 补丁调用已存在")
# RN RefreshControl Catalyst 补丁（UIRefreshControl 在 Catalyst 崩溃）
inject3 = 'python3 "$GITHUB_WORKSPACE/scripts/patch-rn-refreshcontrol.py" "$ROOT_DIR/../.."\n'
if "patch-rn-refreshcontrol" not in src:
    src = src.replace("ensure_pods\n", inject3 + "ensure_pods\n", 1)
    print("RefreshControl Catalyst 补丁调用已注入")
else:
    print("RefreshControl Catalyst 补丁调用已存在")
# RN RefreshControl 原生层补丁（Fabric _attach 也要禁）
inject4 = 'python3 "$GITHUB_WORKSPACE/scripts/patch-rn-refreshcontrol-native.py" "$ROOT_DIR/../.."\n'
if "patch-rn-refreshcontrol-native" not in src:
    src = src.replace("ensure_pods\n", inject4 + "ensure_pods\n", 1)
    print("RefreshControl 原生层补丁调用已注入")
else:
    print("RefreshControl 原生层补丁调用已存在")

# 3. 修复 resolve_destination：workspace 可能尚未生成（pod install 顺序问题），
# 且 scheme 不支持 Catalyst 时 fallback 会选错 destination。
# 简化：直接强制 Catalyst destination（SUPPORTS_MACCATALYST 已 patch 生效）。
src = src.replace(
    'DESTINATION="${MACOS_DESTINATION:-platform=macOS,variant=Mac Catalyst}"',
    'DESTINATION="${MACOS_DESTINATION:-platform=macOS,variant=Mac Catalyst}"',
)
# 让 resolve_destination 在 workspace 不存在时直接用 DESTINATION（不跑 showdestinations）
src = src.replace(
    'if [[ -n "${MACOS_DESTINATION:-}" ]]; then\n    echo "$MACOS_DESTINATION"\n    return\n  fi',
    'if [[ -n "${MACOS_DESTINATION:-}" ]]; then\n    echo "$MACOS_DESTINATION"\n    return\n  fi\n\n  if [[ ! -f "$WORKSPACE_PATH/contents.xcworkspacedata" ]]; then\n    echo "$DESTINATION"\n    return\n  fi',
)
# 同时让 resolve_destination 不再 fallback 到 id=...（iOS destination）
src = src.replace(
    'if [[ -n "$mac_id" ]]; then\n    echo "id=${mac_id}"\n    return\n  fi',
    'if [[ -n "$mac_id" ]]; then\n    echo "$DESTINATION"\n    return\n  fi',
)
print("resolve_destination 已修复（workspace 缺失时用默认 Catalyst）")

# 4. 抑制 C++11 narrowing 警告（react-native-enriched-markdown 在 Catalyst 下
# BOOL→bool 收窄错误，C++17 严格模式报错）。加 -Wno-c++11-narrowing。
# 注意：XCODE_ARGS 是 bash 数组，$(inherited) 会被命令替换，必须转义 \$(inherited)
if 'Wno-c++11-narrowing' not in src:
    src = src.replace(
        'CODE_SIGNING_ALLOWED=NO\n    CODE_SIGNING_REQUIRED=NO',
        'CODE_SIGNING_ALLOWED=NO\n    CODE_SIGNING_REQUIRED=NO\n    GCC_WARN_INHIBIT_ALL_WARNINGS=YES\n    OTHER_CFLAGS="\\$(inherited) -Wno-c++11-narrowing"',
    )
    print("已加 -Wno-c++11-narrowing（转义 \\$(inherited)）")

open(path, "w").write(src)
print("build-macos.sh 补丁完成")
