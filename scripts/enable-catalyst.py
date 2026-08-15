#!/usr/bin/env python3
"""给 app.json 加 supportsMac: true（生成 Catalyst 支持的 iOS 工程）"""
import json, sys

path = "app.json"
d = json.load(open(path))
expo = d.setdefault("expo", {})
ios = expo.setdefault("ios", {})
ios["supportsMac"] = True
# 禁用 Hermes：JS 层补丁（RefreshControl 等）在 Hermes bytecode 里不可靠，
# 且 Catalyst 兼容性更好。用 JS 文本 bundle，patch 必然生效。
expo["hermes"] = False
json.dump(d, open(path, "w"), indent=2, ensure_ascii=False)
print("supportsMac 已添加, hermes 已禁用")
