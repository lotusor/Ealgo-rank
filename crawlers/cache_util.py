#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
爬虫原始数据落盘缓存（与 standalone run() 同源目录 crawlers/data/<platform>/）。

用途：生产路径重跑同一场比赛时直接命中本地文件，跳过对平台接口的全量榜单下载，
既省带宽也省流量（尤其牛客整场 standings 动辄数十 MB）。
- cache_dir 为 None 时关闭缓存（每次都重新下载）。
- TTL 过期（按文件 mtime 判断）自动失效重新下载。
- 解析结构改版时用 `require_schema` 拦截：已结束满 CRAWLER_IMMUTABLE_AFTER_DAYS
  天的场次 TTL=None（缓存永不过期），旧版解析产物里没有新字段，命中后会
  静默按「没有这类记录」入库（2026-10-11 牛客打星适配时发现的回填陷阱）。
  版本号只由**改动过解析结构**的平台传入，其余平台保持无版本、缓存继续复用。
"""
import json
import time
from pathlib import Path


def cache_path(cache_dir, contest_id):
    return Path(cache_dir) / f"contest_{contest_id}.json"


def load_cached_detail(cache_dir, contest_id, ttl_hours, require_schema=None):
    if not cache_dir:
        return None
    p = cache_path(cache_dir, contest_id)
    if not p.exists():
        return None
    if ttl_hours and (time.time() - p.stat().st_mtime) > ttl_hours * 3600:
        return None
    try:
        detail = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
    if require_schema is not None and detail.get("schema") != require_schema:
        return None
    return detail


def save_cached_detail(cache_dir, contest_id, detail):
    if not cache_dir:
        return
    p = cache_path(cache_dir, contest_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(detail, ensure_ascii=False), encoding="utf-8")
