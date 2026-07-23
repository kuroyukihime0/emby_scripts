import os
import sys
from opencc import OpenCC

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from common.config import Config
from common.logger import setup_logger
from common.emby_client import EmbyClient
from common.tmdb_client import fetch_tmdb_detail

cc = OpenCC('t2s')
log = setup_logger('alt_renamer')

config = {
    'EMBY_SERVER': 'http://xxx:8096',
    'API_KEY': '',
    'USER_ID': '',
    'TMDB_KEY': '',
    'LIB_NAME': '',
    'DRY_RUN': True,
    'ADD_HANT_TITLE': True,
}

arr_invalid_char = ['ā', 'á', 'ǎ', 'à', 'ē', 'é', 'ě', 'è', 'ī', 'í', 'ǐ', 'ì',
                    'ō', 'ó', 'ǒ', 'ò', 'ū', 'ú', 'ǔ', 'ù', 'ǖ', 'ǘ', 'ǚ', 'ǜ',
                    'デ', 'ô', 'â', 'Ś', 'ü', 'É']

def invalid_char_in_str(name):
    return any(invalid_char in name for invalid_char in arr_invalid_char)

def run_renamer(sys_config: Config = None):
    cfg = sys_config or Config()
    cfg.load_script_config(config)

    client = EmbyClient(cfg)
    process_count = 0

    if not cfg.LIB_NAME:
        log.error("LIB_NAME is not configured.")
        return

    libs = cfg.LIB_NAME.split(',')
    for lib_name in libs:
        lib_name = lib_name.strip()
        parent_id = client.get_library_id(lib_name)
        if not parent_id:
            continue

        items = client.get_lib_items(parent_id)
        log.info(f'**库 {lib_name} 中共有 {len(items)} 个 Item, 开始处理')

        for item in items:
            item_id = item['Id']
            item_name = item['Name']
            is_movie = item.get('Type') == 'Movie'

            if 'ProviderIds' in item and 'Tmdb' in item['ProviderIds']:
                tmdb_id = item['ProviderIds']['Tmdb']
                tmdb_data, is_cache = fetch_tmdb_detail(client.session, cfg.TMDB_KEY, tmdb_id, is_movie=is_movie)
                from_cache = ' (fromcache)' if is_cache else ''

                if not tmdb_data:
                    continue

                titles = tmdb_data.get("alternative_titles", {})
                raw_alt_names = titles.get("titles" if is_movie else "results", []) or []
                tmdb_alt_name = [x['title'] for x in raw_alt_names if x.get("iso_3166_1") == "CN"]

                if cfg.ADD_HANT_TITLE and tmdb_data.get('hant_trans'):
                    tmdb_alt_name.extend(tmdb_data['hant_trans'])

                if not tmdb_alt_name:
                    if not cfg.IS_DOCKER:
                        log.info(f'   {item_name}{from_cache} 没有别名 跳过')
                    continue

                emby_item = client.get_item(item_id)
                if not emby_item:
                    continue

                name_spliter = ' / '
                series_name = emby_item.get('Name', item_name)

                old_names = emby_item.get('SortName', '').split(name_spliter) if emby_item.get('SortName') else []
                res = [n for n in old_names if n]
                for new_name in tmdb_alt_name:
                    if new_name not in res and not invalid_char_in_str(new_name):
                        res.append(new_name)

                sort_name_all = name_spliter.join(res)
                if old_names == res:
                    if not cfg.IS_DOCKER:
                        log.info(f'   {series_name}{from_cache} 别名没有增删 跳过')
                    continue
                else:
                    log.info(f'   {series_name}{from_cache} 增加别名 [{sort_name_all}]')

                emby_item['SortName'] = sort_name_all
                emby_item['ForcedSortName'] = sort_name_all
                if 'LockedFields' not in emby_item:
                    emby_item['LockedFields'] = []
                if 'SortName' not in emby_item['LockedFields']:
                    emby_item['LockedFields'].append('SortName')

                if client.update_item(item_id, emby_item):
                    process_count += 1
            else:
                log.info(f'error:{item_name} has no tmdb id, skip')

    log.info(f'**更新成功 {process_count} 条')

run_renameer = run_renamer

if __name__ == '__main__':
    run_renamer()
