#!/usr/bin/env python3
"""私人免费节点订阅收集器（仅自用）。

从网上公开的免费配置来源抓取节点链接，去重、过滤不安全的，
生成 V2Box 可用的订阅文件。只用 Python 标准库，不用装任何依赖。

输出：
  sub.txt        订阅（base64，V2Box 直接导入）
  sub_plain.txt  明文节点列表（一行一个链接，方便检查）
  stats.json     统计（更新时间、各协议数量、各来源新增数、分组列表）
  sub-001.txt …  分组订阅：每 CHUNK_SIZE 条一组，方便一次只导入一小批
"""

import base64
import glob
import json
import os
import re
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timezone

# 来源：照搬俄罗斯 anti-RKN 仓库 aneek0/goida-vpn-configs 的公开来源
# （全是 GitHub 上别人分享的免费配置，定期更新；已去掉 1 个失效的，剩 24 个）
SOURCES = [
    "https://github.com/sakha1370/OpenRay/raw/refs/heads/main/output/all_valid_proxies.txt",
    "https://raw.githubusercontent.com/sevcator/5ubscrpt10n/main/protocols/vl.txt",
    "https://raw.githubusercontent.com/yitong2333/proxy-minging/refs/heads/main/v2ray.txt",
    "https://raw.githubusercontent.com/acymz/AutoVPN/refs/heads/main/data/V2.txt",
    "https://raw.githubusercontent.com/miladtahanian/V2RayCFGDumper/refs/heads/main/sub.txt",
    "https://raw.githubusercontent.com/roosterkid/openproxylist/main/V2RAY_RAW.txt",
    "https://github.com/ShatakVPN/ConfigForge-V2Ray/raw/refs/heads/main/configs/vless.txt",
    "https://raw.githubusercontent.com/mohamadfg-dev/telegram-v2ray-configs-collector/refs/heads/main/category/vless.txt",
    "https://raw.githubusercontent.com/mheidari98/.proxy/refs/heads/main/vless",
    "https://raw.githubusercontent.com/youfoundamin/V2rayCollector/main/mixed_iran.txt",
    "https://github.com/VOID-Anonymity/V.O.I.D-VPN_Bypass/raw/refs/heads/main/url_work.txt",
    "https://github.com/cbusifabcap/daily_free_vpn/raw/refs/heads/main/Z.txt",
    "https://github.com/LalatinaHub/Mineral/raw/refs/heads/master/result/nodes",
    "https://raw.githubusercontent.com/miladtahanian/Config-Collector/refs/heads/main/mixed_iran.txt",
    "https://raw.githubusercontent.com/Pawdroid/Free-servers/refs/heads/main/sub",
    "https://github.com/MhdiTaheri/V2rayCollector_Py/raw/refs/heads/main/sub/Mix/mix.txt",
    "https://raw.githubusercontent.com/free18/v2ray/refs/heads/main/v.txt",
    "https://github.com/MhdiTaheri/V2rayCollector/raw/refs/heads/main/sub/mix",
    "https://github.com/Argh94/Proxy-List/raw/refs/heads/main/All_Config.txt",
    "https://raw.githubusercontent.com/shabane/kamaji/master/hub/merged.txt",
    "https://raw.githubusercontent.com/wuqb2i4f/xray-config-toolkit/main/output/base64/mix-uri",
    "https://github.com/igareck/vpn-configs-for-russia/raw/refs/heads/main/BLACK_VLESS_RUS.txt",
    "https://github.com/Mr-Meshky/vify/raw/refs/heads/main/configs/vless.txt",
    "https://raw.githubusercontent.com/V2RayRoot/V2RayConfig/refs/heads/main/Config/vless.txt",
]

# 最多保留多少条，避免订阅过大导致客户端卡顿
MAX_LINKS = 5000

# 分组：每组多少条，方便一次只导入一小批
CHUNK_SIZE = 50

# 单个来源最多贡献多少条，免得某一个巨型来源把订阅挤满
PER_SOURCE_MAX = 800

# 各协议配额（加起来正好 5000）；配额没用完的空位由 VLESS 补上
QUOTAS = {
    "vless": 2500,
    "trojan": 600,
    "ss": 600,
    "vmess": 500,
    "hysteria2": 300,
    "tuic": 200,
    "hysteria": 100,
    "ssr": 100,
    "socks": 100,
}

URI_RE = re.compile(r"(?:vless|vmess|trojan|ss|ssr|hysteria2|hysteria|tuic|socks)://[^\s\"'<>`]+")
B64_ONLY_RE = re.compile(r"[A-Za-z0-9+/=\s]+")

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; benben-sub/1.0)"}


def fetch(url, timeout=25):
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
    except urllib.error.HTTPError as e:
        if e.code in (429, 503):  # 被限流了，等 5 秒再试一次
            time.sleep(5)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read()
        else:
            raise
    return raw.decode("utf-8", errors="ignore")


def maybe_b64_decode(text):
    """有些来源整个文件就是一段 base64 订阅；是的话先解开再提取。"""
    s = text.strip()
    if len(s) < 100 or not B64_ONLY_RE.fullmatch(s):
        return text
    try:
        pad = (-len("".join(s.split()))) % 4
        dec = base64.b64decode("".join(s.split()) + "=" * pad).decode("utf-8", errors="ignore")
        if dec.count("://") >= 3:
            return dec
    except Exception:
        pass
    return text


def extract(text):
    text = maybe_b64_decode(text)
    out = []
    for m in URI_RE.finditer(text):
        uri = m.group(0).rstrip(".,)")
        if "allowinsecure=1" in uri:  # 不安全的配置不要
            continue
        out.append(uri)
    return out


def proto(uri):
    return uri.split("://", 1)[0]


def main():
    all_links = []
    seen = set()  # 去重：去掉 # 后面的备注名再比，同一服务器不同名字也算重复
    per_source = {}
    for i, url in enumerate(SOURCES, 1):
        try:
            got = extract(fetch(url))
        except Exception as e:
            print(f"[{i}] FAIL {url}: {e}")
            per_source[str(i)] = 0
            continue
        new = 0
        for u in got:
            if new >= PER_SOURCE_MAX:
                break
            key = u.split("#", 1)[0]
            if key in seen:
                continue
            seen.add(key)
            all_links.append(u)
            new += 1
        per_source[str(i)] = new
        print(f"[{i}] {url} -> {len(got)} raw, {new} new")

    # 按协议配额取，免得某一种协议把订阅挤满；同协议内保持抓取顺序
    by_proto = {}
    for u in all_links:
        by_proto.setdefault(proto(u), []).append(u)
    picked = []
    for p, quota in QUOTAS.items():
        picked.extend(by_proto.get(p, [])[:quota])
    if len(picked) < MAX_LINKS:  # 配额没用完的空位由 VLESS 补上
        rest = by_proto.get("vless", [])[QUOTAS.get("vless", 0):]
        picked.extend(rest[:MAX_LINKS - len(picked)])
    all_links = picked

    body = "\n".join(all_links)
    sub_b64 = base64.b64encode(body.encode("utf-8")).decode("ascii")
    with open("sub.txt", "w", encoding="utf-8") as f:
        f.write(sub_b64)
    with open("sub_plain.txt", "w", encoding="utf-8") as f:
        f.write(body + "\n")

    # 分组订阅：每 CHUNK_SIZE 条一组，生成 sub-001.txt……，页面上分页展示
    # 先删掉上次剩下的旧分组，免得总数变少时多出过期文件
    for old in glob.glob("sub-[0-9]*.txt"):
        os.remove(old)
    chunks = []
    for n in range(0, len(all_links), CHUNK_SIZE):
        part = all_links[n:n + CHUNK_SIZE]
        idx = n // CHUNK_SIZE + 1
        fname = f"sub-{idx:03d}.txt"
        with open(fname, "w", encoding="utf-8") as f:
            f.write(base64.b64encode("\n".join(part).encode("utf-8")).decode("ascii"))
        chunks.append({"id": idx, "file": fname, "count": len(part)})

    stats = {
        "updated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "total": len(all_links),
        "by_protocol": dict(Counter(proto(u) for u in all_links)),
        "per_source_new": per_source,
        "chunk_size": CHUNK_SIZE,
        "chunks": chunks,
    }
    with open("stats.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    print("TOTAL:", len(all_links), dict(Counter(proto(u) for u in all_links)), "CHUNKS:", len(chunks), "x", CHUNK_SIZE)


if __name__ == "__main__":
    main()
