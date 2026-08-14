#!/usr/bin/env python3
"""给 Podfile 注入 post_install 钩子：RevenueCat pod 用 Swift 5 模式编译
RevenueCat SDK 旧版本在 Swift 6 语言模式下有 100+ 处 Sendable 错误。
注意：expo prebuild 生成的 Podfile 已有 post_install 块（含
react_native_post_install），需要把 RevenueCat 逻辑追加到该块内部。"""
import sys

path = "ios/Podfile"
src = open(path).read()

# RevenueCat 逻辑（作为 Ruby 代码片段）
rc_logic = '''
  installer.pods_project.targets.each do |target|
    if target.name.include?("RevenueCat")
      target.build_configurations.each do |config|
        config.build_settings["SWIFT_VERSION"] = "5.0"
        config.build_settings["SWIFT_STRICT_CONCURRENCY"] = "minimal"
      end
    end
  end
'''

if "RevenueCat" in src:
    print("RevenueCat 逻辑已存在，跳过")
    sys.exit(0)

if "post_install" in src:
    # 找 "post_install do |installer|" 后的第一个完整块。
    # 策略：找 react_native_post_install(installer) 或块内最后一行，在其后追加
    # 更稳：找 post_install 块的收尾 "  end"（两个空格缩进的 end），在其前插入
    import re
    # 匹配 "  post_install do |installer|" 到第一个 "\n  end"（缩进 2 空格）
    m = re.search(r'(post_install do \|installer\|)(.*?)(\n\s*end)', src, re.S)
    if m:
        old_block = m.group(0)
        new_block = m.group(1) + m.group(2) + rc_logic.rstrip() + m.group(3)
        src = src.replace(old_block, new_block)
        open(path, "w").write(src)
        print("RevenueCat 逻辑已追加到现有 post_install 块内")
    else:
        print("未找到 post_install 块，直接追加")
        src += "\npost_install do |installer|\n" + rc_logic + "end\n"
        open(path, "w").write(src)
else:
    src += "\npost_install do |installer|\n" + rc_logic + "end\n"
    open(path, "w").write(src)
    print("新 post_install 块已追加")
