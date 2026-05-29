#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""零风险爆款文案抓取 - API稳定版 v3"""

import json
import os
import re
import time
from datetime import datetime
from typing import List, Dict
from urllib.parse import quote

import requests

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
os.makedirs(DATA_DIR, exist_ok=True)

DINGTALK_APP_KEY = os.getenv("DINGTALK_APP_KEY", "")
DINGTALK_APP_SECRET = os.getenv("DINGTALK_APP_SECRET", "")
DINGTALK_BASE_ID = os.getenv("DINGTALK_BASE_ID", "")
DINGTALK_SHEET_ID = os.getenv("DINGTALK_SHEET_ID", "")
DINGTALK_OPERATOR_ID = os.getenv("DINGTALK_OPERATOR_ID", "")

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

class VvhanCrawler:
    """使用 api.vvhan.com 稳定API获取热榜数据"""
    BASE_URL = "https://api.vvhan.com/api/hotlist"

    PLATFORMS = {
        "知乎": "zhihu",
        "微博": "weibo",
        "抖音": "douyin",
        "B站": "bilihot",
        "百度": "baidu",
        "36氪": "36kr",
        "虎嗅": "huxiu",
        "微信": "weixin",
        "小红书": "xiaohongshu",
    }

    def fetch(self, platform_name, limit=15):
        platform_code = self.PLATFORMS.get(platform_name)
        if not platform_code:
            return []
        print(f"  🔍 {platform_name}...", end=" ")
        try:
            url = f"{self.BASE_URL}/{platform_code}"
            resp = requests.get(url, headers=HEADERS, timeout=15)
            data = resp.json()
            
            if data.get('success') != True:
                msg = data.get("message", "未知错误")
                print(f"❌ API返回失败: {msg}")
                return []
            
            results = []
            items = data.get('data', [])[:limit]
            
            for idx, item in enumerate(items):
                try:
                    title = item.get('title', '')
                    hot = item.get('hot', '0')
                    link = item.get('url', '') or item.get('mobilUrl', '')
                    
                    if title and len(title) >= 5:
                        results.append({
                            "平台": platform_name,
                            "主题": "热榜",
                            "文案内容": title,
                            "热度": str(hot),
                            "作者": "",
                            "链接": link,
                            "抓取时间": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "标签": "热榜",
                            "钩子模板": self._extract_hooks(title),
                            "结构类型": "热榜标题",
                            "排名": str(idx + 1)
                        })
                except:
                    continue
            
            print(f"✅ {len(results)}条")
            return results
            
        except Exception as e:
            print(f"❌ 失败({e})")
            return []

    def _extract_hooks(self, title):
        hooks = []
        if re.search(r"\d+", title):
            hooks.append("数字锚定")
        emotions = ["震惊", "救命", "求求", "终于", "原来", "竟然", "居然", "才发现"]
        for e in emotions:
            if e in title:
                hooks.append(f"情绪:{e}")
        if "?" in title or "？" in title:
            hooks.append("疑问钩子")
        if "如何" in title or "怎么" in title:
            hooks.append("教程型")
        return ", ".join(hooks) if hooks else "常规"

class DingTalkAISheetAPI:
    def __init__(self, app_key, app_secret, base_id, operator_id):
        self.app_key = app_key
        self.app_secret = app_secret
        self.base_id = base_id
        self.operator_id = operator_id
        self.access_token = self._get_token()
    def _get_token(self):
        url = "https://oapi.dingtalk.com/gettoken"
        params = {"appkey": self.app_key, "appsecret": self.app_secret}
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        if data.get("errcode") != 0:
            raise Exception(f"Token失败: {data}")
        return data["access_token"]
    def batch_add_records(self, sheet_id_or_name, records):
        if not records:
            return True
        url = f"https://oapi.dingtalk.com/smartwork/sheet/v2/tables/records/batch_add?access_token={self.access_token}"
        formatted_records = []
        for record in records:
            fields = []
            for column_key, value in record.items():
                fields.append({
                    "columnKey": column_key,
                    "value": str(value) if value is not None else ""
                })
            formatted_records.append({"fields": fields})
        payload = {
            "sheetId": self.base_id,
            "tableId": sheet_id_or_name,
            "records": formatted_records
        }
        try:
            resp = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=60
            )
            result = resp.json()
            if result.get("errcode") == 0:
                print(f"✅ 钉钉AI表格写入 {len(records)} 条成功")
                return True
            else:
                errmsg = result.get("errmsg", "未知错误")
                print(f"⚠️ 钉钉AI表格写入异常: {errmsg}")
                return False
        except Exception as e:
            print(f"❌ 钉钉AI表格API调用失败: {e}")
            return False

class SafePipeline:
    def __init__(self):
        self.dingtalk = None
        if DINGTALK_APP_KEY and DINGTALK_APP_SECRET and DINGTALK_BASE_ID and DINGTALK_OPERATOR_ID:
            try:
                self.dingtalk = DingTalkAISheetAPI(
                    DINGTALK_APP_KEY,
                    DINGTALK_APP_SECRET,
                    DINGTALK_BASE_ID,
                    DINGTALK_OPERATOR_ID
                )
                print("✅ 钉钉AI表格已连接")
            except Exception as e:
                print(f"⚠️ 钉钉AI表格未连接: {e}")
        else:
            print("ℹ️ 仅本地模式（未配置钉钉AI表格）")
            print("   如需接入，请配置 Secrets")
    def run(self, platforms=None):
        all_data = []
        crawler = VvhanCrawler()
        target_platforms = platforms if platforms else list(VvhanCrawler.PLATFORMS.keys())
        for platform in target_platforms:
            if platform in VvhanCrawler.PLATFORMS:
                all_data.extend(crawler.fetch(platform, 15))
                time.sleep(1)
        print(f"\n📦 总计: {len(all_data)} 条")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{DATA_DIR}/safe_hot_{ts}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        print(f"💾 本地备份: {filename}")
        latest_file = f"{DATA_DIR}/latest.json"
        with open(latest_file, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        print(f"💾 最新汇总: {latest_file}")
        if all_data and self.dingtalk and DINGTALK_SHEET_ID:
            self.dingtalk.batch_add_records(DINGTALK_SHEET_ID, all_data)
        return all_data

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 零风险爆款文案抓取系统")
    print("   支持钉钉AI表格（智能表格/多维表格）")
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"⏰ {ts}")
    print("=" * 50)
    pipeline = SafePipeline()
    results = pipeline.run()
    print(f"\n✅ 完成！共 {len(results)} 条已入库")
