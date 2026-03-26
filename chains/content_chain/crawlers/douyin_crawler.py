"""
抖音热搜数据采集器 - 直接API调用
复制自原爬虫，改造用于信息帝国
"""

import requests
import logging
import sys
import io
from datetime import datetime
from typing import List, Dict
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DouyinHotSearchCrawler:
    """抖音热搜采集器 - 无需签名"""

    API_URL = "https://www.douyin.com/aweme/v1/web/hot/search/list/"
    API_PARAMS = {
        "aid": 6383,
        "version_code": 170400
    }

    def __init__(self, use_proxy: bool = False):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0',
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Referer': 'https://www.douyin.com',
        }
        self.use_proxy = use_proxy

    def get_hot_search(self) -> List[Dict]:
        """
        获取热搜榜

        Returns:
            热搜列表
        """
        try:
            response = requests.get(
                self.API_URL,
                params=self.API_PARAMS,
                headers=self.headers,
                timeout=15
            )

            if response.status_code == 200:
                data = response.json()
                word_list = data.get('data', {}).get('word_list', [])

                results = []
                for item in word_list:
                    results.append({
                        'word': item.get('word', ''),
                        'hot_value': item.get('hot_value', 0),
                        'view_count': item.get('view_count', 0),
                        'event_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'platform': 'douyin'
                    })

                logger.info(f"抖音: 获取到 {len(results)} 条热搜")
                return results
            else:
                logger.error(f"抖音: 请求失败: {response.status_code}")

        except Exception as e:
            logger.error(f"抖音: 获取热搜失败: {e}")

        return []
