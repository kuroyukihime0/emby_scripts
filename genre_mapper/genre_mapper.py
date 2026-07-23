import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from common.config import Config
from common.logger import setup_logger
from common.emby_client import EmbyClient

log = setup_logger('genre_mapper')

config = {
    'EMBY_SERVER': 'http://xxx:8096',
    'API_KEY': '',
    'USER_ID': '',
    'LIB_NAME': '',
    'DRY_RUN': True,
}

genre_mapping = {
    'Sci-Fi & Fantasy': {'Name': '科幻', 'Id': 16630},
    'War & Politics': {'Name': '战争', 'Id': 16718},
}

genre_remove = ['']

def process_item_genre(client: EmbyClient, parent_id: str):
    series = client.get_item(parent_id)
    if not series:
        return False

    genres = series.get('Genres', [])
    genres_items = series.get('GenreItems', [])

    need_replace = any(genre in genre_mapping or genre in genre_remove for genre in genres) or \
                   any(g_item.get('Name') in genre_mapping for g_item in genres_items)

    if need_replace:
        item_name = series.get("Name", parent_id)
        genres_new = [genre_mapping[genre]['Name'] if genre in genre_mapping else genre for genre in genres]
        genres_new = list(filter(lambda g: g not in genre_remove and g != '', genres_new))

        log.info(f'🎭 [Genre映射] 《{item_name}》 ➔ {genres} ➔ {genres_new}')
        series['Genres'] = genres_new

        new_genre_items = []
        for g_item in genres_items:
            g_name = g_item.get('Name')
            if g_name in genre_mapping:
                new_genre_items.append(genre_mapping[g_name])
            elif g_name not in genre_remove and g_name != '':
                new_genre_items.append(g_item)

        series['GenreItems'] = new_genre_items
        return client.update_item(parent_id, series)

    return False

def run_mapper(sys_config: Config = None):
    cfg = sys_config or Config()
    cfg.load_script_config(config)

    client = EmbyClient(cfg)
    process_count = 0

    if not cfg.LIB_NAME:
        log.error("❌ LIB_NAME 未配置，无法处理。")
        return

    libs = cfg.LIB_NAME.split(',')
    for lib_name in libs:
        lib_name = lib_name.strip()
        parent_id = client.get_library_id(lib_name)
        if not parent_id:
            continue

        items = client.get_lib_items(parent_id)
        log.info(f'📁 ════════ [Genre映射: {lib_name}] 共有 {len(items)} 个条目，开始处理 ════════')
        for item in items:
            item_id = item['Id']
            if process_item_genre(client, item_id):
                process_count += 1

    log.info(f'✅ [Genre映射完成] 成功更新 {process_count} 条条目')

if __name__ == '__main__':
    run_mapper()
