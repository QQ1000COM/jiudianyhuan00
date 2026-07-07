import asyncio
import aiohttp
import requests
import time
from urllib.parse import urljoin

from channel_config import RESULTS_PER_CHANNEL
from utils import normalize_channel_name, is_valid_stream, write_channel_output

URL_FILE = "https://raw.githubusercontent.com/kakaxi-1/zubo/main/ip_urls.txt"


def load_urls():
    try:
        resp = requests.get(URL_FILE, timeout=5)
        resp.raise_for_status()
        urls = [line.strip() for line in resp.text.splitlines() if line.strip()]
        print(f"📡 已加载 {len(urls)} 个基础 URL")
        return urls
    except Exception as e:
        print(f"❌ 下载 {URL_FILE} 失败: {e}")
        exit()

async def generate_urls(url):
    modified_urls = []

    ip_start = url.find("//") + 2
    ip_end = url.find(":", ip_start)

    base = url[:ip_start]
    ip_prefix = url[ip_start:ip_end].rsplit('.', 1)[0]
    port = url[ip_end:]

    json_paths = [
    "/iptv/live/1000.json?key=txiptv",
    "/iptv/live/1001.json?key=txiptv",
]

    for i in range(1, 256):
        ip = f"{base}{ip_prefix}.{i}{port}"
        for path in json_paths:
            modified_urls.append(f"{ip}{path}")

    return modified_urls

async def check_url(session, url, semaphore):
    async with semaphore:
        try:
            async with session.get(url, timeout=1) as resp:#===========================JSON访问时间
                if resp.status == 200:
                    return url
        except:
            return None

async def fetch_json(session, url, semaphore):
    async with semaphore:
        try:
            async with session.get(url, timeout=2) as resp:
                data = await resp.json()
                results = []
                for item in data.get('data', []):
                    name = item.get('name')
                    urlx = item.get('url')
                    if not name or not urlx or ',' in urlx:
                        continue

                    if not urlx.startswith("http"):
                        urlx = urljoin(url, urlx)

                    name = normalize_channel_name(name)

                    results.append((name, urlx))
                return results
        except:
            return []

async def measure_speed(session, url, semaphore):
    async with semaphore:
        start = time.time()
        try:
            async with session.head(url, timeout=2) as resp:  # =======================频道测速用时
                if resp.status == 200:
                    return int((time.time() - start) * 1000)
                else:
                    return 999999
        except:
            return 999999

async def main():
    print("🚀 开始运行 ITVlist 脚本")
    semaphore = asyncio.Semaphore(150)  # ==============================================并发限制

    urls = load_urls()
    
    async with aiohttp.ClientSession() as session:
        all_urls = []
        for url in urls:
            modified_urls = await generate_urls(url)
            all_urls.extend(modified_urls)
        print(f"🔍 生成待扫描 URL 共: {len(all_urls)} 个")

        print("⏳ 开始检测可用 JSON API...")
        tasks = [check_url(session, u, semaphore) for u in all_urls]
        valid_urls = [r for r in await asyncio.gather(*tasks) if r]
        print(f"✅ 可用 JSON 地址: {len(valid_urls)} 个")
        for u in valid_urls:
            print(f"  - {u}")

        print("📥 开始抓取节目单 JSON...")
        tasks = [fetch_json(session, u, semaphore) for u in valid_urls]
        results = []
        fetched = await asyncio.gather(*tasks)
        for sublist in fetched:
            results.extend(sublist)
        print(f"📺 抓到频道总数: {len(results)} 条")

        final_results = [(name, url, 0) for name, url in results]

        final_results = [
            (name, url, speed)
            for name, url, speed in final_results
            if is_valid_stream(url)
        ]

        print("🚀 开始测速频道源...")
        speed_tasks = [measure_speed(session, url, semaphore) for (_, url, _) in final_results]
        speeds = await asyncio.gather(*speed_tasks)
        final_results = [
            (name, url, speed)
            for (name, url, _), speed in zip(final_results, speeds)
        ]

        final_results.sort(key=lambda x: x[2])

        channel_entries = [(name, url) for name, url, speed in final_results]

        write_channel_output(
            "itvlist.txt",
            channel_entries,
            results_per_channel=RESULTS_PER_CHANNEL,
        )

        print("🎉 itvlist.txt 已生成完成！")

if __name__ == "__main__":
    asyncio.run(main())
