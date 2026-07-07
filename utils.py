from datetime import datetime, timezone, timedelta

from channel_config import CHANNEL_MAPPING, CHANNEL_CATEGORIES, DISCLAIMER_URL


def get_beijing_time():
    return datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")


def build_alias_map(mapping=None):
    if mapping is None:
        mapping = CHANNEL_MAPPING
    alias_map = {}
    for main_name, aliases in mapping.items():
        for alias in aliases:
            alias_map[alias] = main_name
    return alias_map


def normalize_channel_name(name, mapping=None):
    if mapping is None:
        mapping = CHANNEL_MAPPING
    for std_name, aliases in mapping.items():
        if name in aliases:
            return std_name
    return name


def is_valid_stream(url):
    if url.startswith(("rtp://", "udp://", "rtsp://")):
        return False
    if "239." in url:
        return False
    if url.startswith(("http://16.", "http://10.", "http://192.168.")):
        return False
    if "/paiptv/" in url or "/00/SNM/" in url or "/00/CHANNEL" in url:
        return False
    valid_ext = (".m3u8", ".ts", ".flv", ".mp4", ".mkv")
    return url.startswith("http") and any(ext in url for ext in valid_ext)


def write_channel_output(filepath, channel_entries, categories=None,
                         results_per_channel=None):
    """Write categorized channel list to a file.

    Args:
        filepath: output file path
        channel_entries: list of (channel_name, line_content) tuples;
            each entry is written as "channel_name,line_content"
        categories: dict of category_name -> [channel_names]
        results_per_channel: max entries per channel (None = unlimited)
    """
    if categories is None:
        categories = CHANNEL_CATEGORIES

    beijing_now = get_beijing_time()

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(f"更新时间: {beijing_now}（北京时间）\n\n")
        f.write("更新时间,#genre#\n")
        f.write(f"{beijing_now},{DISCLAIMER_URL}\n\n")

        for category, ch_list in categories.items():
            f.write(f"{category},#genre#\n")
            for ch in ch_list:
                ch_items = [(n, lc) for n, lc in channel_entries if n == ch]
                if results_per_channel is not None:
                    ch_items = ch_items[:results_per_channel]
                for name, line_content in ch_items:
                    f.write(f"{name},{line_content}\n")
            f.write("\n")
