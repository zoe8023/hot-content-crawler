#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""零风险爆款文案抓取 - GitHub Actions 版"""

import json
import os
import re
import time
from datetime import datetime
from typing import List, Dict
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
os.makedirs(DATA_DIR, exist_ok=True)

DINGTALK_APP_KEY = os.getenv("DINGTALK_APP_KEY", "")
DINGTALK_APP_SECRET = os.getenv("DINGTALK_APP_SECRET", "")
DINGTALK_SHEET_ID = os.getenv("DINGTALK_SHEET_ID", "")
DINGTALK_SHEET_NAME = os.getenv("DINGTALK_SHEET_NAME", "Sheet1")

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

class TopHubCrawler:
    BASE_URL = "https://tophub.today"
    NODES = {
        "小红书": {"node": "xhs", "category": "社区"},
        "抖音": {"node": "douyin", "category": "视频"},
        "知乎": {"node": "zhihu", "category": "问答"},
        "微博": {"node": "weibo", "category": "社交"},
        "B站": {"node": "bilibili", "category": "视频"},
        "微信": {"node": "weixin", "category": "公众号"},
        "百度": {"node": "baidu", "category": "搜索"},
        "36氪": {"node": "36kr", "category": "科技"},
        "虎嗅": {"node": "huxiu", "category": "科技"},
    }

    def fetch_node(self, node_name, limit=15):
        node_info = self.NODES.get(node_name)
        if not node_info:
            return []
        url = f"{self.BASE_URL}/n/{node_info['node']}"
        print(f"  🔍 {node_name}...", end=" ")
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.encoding = 'utf-8'
            soup = BeautifulSoup(resp.text, 'html.parser')
            results = []
            table = soup.find('table', class_='table') or soup.find('table')
            items = table.find_all('tr')[1:] if table else soup.find_all('tr')[1:]
            for row in items[:limit]:
                try:
                    cols = row.find_all('td')
                    if len(cols) < 3:
                        continue
                    rank = cols[0].get_text(strip=True)
                    title_link = cols[1].find('a')
                    if title_link:
                        title = title_link.get_text(strip=True)
                        link = title_link.get('href', '')
                        if link and not link.startswith('http'):
                            link = self.BASE_URL + link
                    else:
                        title = cols[1].get_text(strip=True)
                        link = ''
                    hot_text = cols[2].get_text(strip=True) if len(cols) > 2 else '0'
                    title = self._clean_title(title)
                    if title and len(title) >= 5:
                        results.append({
                            "platform": node_name,
                            "topic": "热榜",
                            "content": title,
                            "likes": hot_text,
                            "author": "",
                            "link": link,
                            "fetch_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "tags": node_info["category"],
                            "hooks": self._extract_hooks(title),
                            "structure": "热榜标题",
                            "rank": rank
                        })
                except:
                    continue
            print(f"✅ {len(results)}条")
            return results
        except Exception as e:
            print(f"❌ 失败({e})")
            return []

    def _clean_title(self, title):
        title = re.sub(r"\s+", " ", title)
        title = title.replace("\n", " ").replace("\t", " ")
        title = re.sub(r"(^\s*[\d#]+\.?\s*)", "", title)
        return title.strip()[:200]

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

class ZhihuCrawler:
    def fetch(self, limit=15):
        print(f"  🔍 知乎...", end=" ")
        try:
            url = "https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total"
            headers = {**HEADERS, "x-api-version": "3.0.76"}
            resp = requests.get(url, headers=headers, timeout=15)
            data = resp.json()
            results = []
            for item in data.get('data', [])[:limit]:
                try:
                    card = item.get('target', {})
                    title = card.get('title', '')
                    link = card.get('url', '')
                    if link and not link.startswith('http'):
                        link = 'https://www.zhihu.com' + link
                    detail = card.get('detail_text', '0')
                    if title:
                        results.append({
                            "platform": "知乎",
                            "topic": "热榜问答",
                            "content": title,
                            "likes": detail,
                            "author": "",
                            "link": link,
                            "fetch_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "tags": "问答",
                            "hooks": "疑问式" if "?" in title else "讨论型",
                            "structure": "问题式钩子"
                        })
                except:
                    continue
            print(f"✅ {len(results)}条")
            return results
        except Exception as e:
            print(f"❌ 失败({e})")
            return []

class WeiboCrawler:
    def fetch(self, limit=15):
        print(f"  🔍 微博...", end=" ")
        try:
            url = "https://weibo.com/ajax/side/hotSearch"
            resp = requests.get(url, headers=HEADERS, timeout=15)
            data = resp.json()
            results = []
            for item in data.get('data', {}).get('realtime', [])[:limit]:
                try:
                    title = item.get('note', '')
                    rank = item.get('rank', 0)
                    hot = item.get('raw_hot', 0)
                    flag = item.get('flag', '')
                    link = f"https://s.weibo.com/weibo?q={quote(title)}"
                    tag = '热搜'
                    if flag == '爆':
                        tag = '爆'
                    elif flag == '热':
                        tag = '热'
                    elif flag == '新':
                        tag = '新'
                    if title:
                        results.append({
                            "platform": "微博",
                            "topic": tag,
                            "content": title,
                            "likes": str(hot),
                            "author": "",
                            "link": link,
                            "fetch_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "tags": f"微博{tag}",
                            "hooks": "热点型",
                            "structure": "热搜标题",
                            "rank": rank
                        })
                except:
                    continue
            print(f"✅ {len(results)}条")
            return results
        except Exception as e:
            print(f"❌ 失败({e})")
            return []

class DingTalkAPI:
    def __init__(self, app_key, app_secret):
        self.app_key = app_key
        self.app_secret = app_secret
        self.access_token = self._get_token()
    def _get_token(self):
        url = "https://oapi.dingtalk.com/gettoken"
        params = {"appkey": self.app_key, "appsecret": self.app_secret}
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        if data.get("errcode") != 0:
            raise Exception(f"Token失败: {data}")
        return data["access_token"]
    def append_sheet(self, sheet_id, sheet_name, rows):
        if not rows:
            return True
        url = f"https://oapi.dingtalk.com/v1.0/doc/workbooks/{sheet_id}/sheets/{sheet_name}/appendData"
        headers = {"x-acs-dingtalk-access-token": self.access_token, "Content-Type": "application/json"}
        payload = {"values": rows, "valueRenderOption": "FORMATTED_VALUE"}
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=15)
            result = resp.json()
            success = result.get("success") or "rowCount" in str(result)
            if success:
                print(f"✅ 钉钉写入 {len(rows)} 行")
            return success
        except Exception as e:
            print(f"❌ 钉钉失败: {e}")
            return False

class SafePipeline:
    def __init__(self):
        self.dingtalk = None
        if DINGTALK_APP_KEY and DINGTALK_APP_SECRET and DINGTALK_SHEET_ID:
            try:
                self.dingtalk = DingTalkAPI(DINGTALK_APP_KEY, DINGTALK_APP_SECRET)
                print("✅ 钉钉已连接")
            except Exception as e:
                print(f"⚠️ 钉钉未连接: {e}")
        else:
            print("ℹ️ 仅本地模式（未配置钉钉）")
    def run(self, platforms=None):
        all_data = []
        tophub = TopHubCrawler()
        nodes = platforms if platforms else list(TopHubCrawler.NODES.keys())
        for node in nodes:
            if node in TopHubCrawler.NODES:
                all_data.extend(tophub.fetch_node(node, 15))
                time.sleep(2)
        if not platforms or "知乎" in platforms:
            all_data.extend(ZhihuCrawler().fetch(15))
            time.sleep(1)
        if not platforms or "微博" in platforms:
            all_data.extend(WeiboCrawler().fetch(15))
            time.sleep(1)
        print(f"\n📦 总计: {len(all_data)} 条")
        filename = f"{DATA_DIR}/safe_hot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        print(f"💾 本地备份: {filename}")
        latest_file = f"{DATA_DIR}/latest.json"
        with open(latest_file, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        print(f"💾 最新汇总: {latest_file}")
        if all_data and self.dingtalk:
            rows = [[d['platform'], d['topic'], d['content'], str(d['likes']),
                     d['author'], d['link'], d['fetch_time'], d['tags'],
                     d['hooks'], d['structure']] for d in all_data]
            self.dingtalk.append_sheet(DINGTALK_SHEET_ID, DINGTALK_SHEET_NAME, rows)
        return all_data

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 零风险爆款文案抓取系统 - GitHub Actions")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    pipeline = SafePipeline()
    results = pipeline.run()
    print(f"\n✅ 完成！共 {len(results)} 条已入库")
