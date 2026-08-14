#!/usr/bin/env python3
"""给 app.json 加 supportsMac: true（生成 Catalyst 支持的 iOS 工程）"""
import json, sys

path = "app.json"
d = json.load(open(path))
expo = d.setdefault("expo", {})
ios = expo.setdefault("ios", {})
ios["supportsMac"] = True
json.dump(d, open(path, "w"), indent=2, ensure_ascii=False)
print("supportsMac 已添加")
