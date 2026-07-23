import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from common.config import Config
from common.logger import setup_logger
from common.emby_client import EmbyClient
from common.tmdb_client import fetch_tmdb_detail

log = setup_logger('season_renamer')

config = {
    'EMBY_SERVER': 'http://xxx:8096',
    'API_KEY': '',
    'USER_ID': '',
    'TMDB_KEY': '',
    'LIB_NAME': '',
    'DRY_RUN': True,
}

def rename_seasons(client: EmbyClient, parent_id: str, tmdb_id: str, series_name: str, is_movie: bool):
    process_count = 0
    url = f"{client.config.EMBY_SERVER.rstrip('/')}/emby/Items"
    params = {'ParentId': parent_id}

    try:
        response = client.session.get(url, headers=client.headers, params=params)
        seasons = response.json().get('Items', [])
    except Exception as e:
        log.error(f"❌ 获取 《{series_name}》 季节点失败: {e}")
        return 0

    tmdb_data, is_cache = fetch_tmdb_detail(client.session, client.config.TMDB_KEY, tmdb_id, is_movie=is_movie)
    from_cache = ' ⚡(Cache)' if is_cache else ''

    if not tmdb_data or 'seasons' not in tmdb_data:
        log.error(f'⚠️  [季名跳过] TMDB 未查找到季数据: {tmdb_id} 《{series_name}》')
        return 0

    tmdb_seasons = tmdb_data.get('seasons', [])

    for season in seasons:
        season_id = season['Id']
        season_name = season['Name']
        if 'IndexNumber' not in season:
            log.info(f'⏭️  [季名跳过] 《{series_name}》 {season_name} 无 IndexNumber 编号')
            continue

        season_index = season['IndexNumber']
        tmdb_season = next((s for s in tmdb_seasons if s.get('season_number') == season_index), None)
        if tmdb_season:
            tmdb_season_name = tmdb_season.get('name', '').strip()
            single_season = client.get_item(season_id)
            if not single_season:
                continue

            if 'Name' in single_season:
                current_name = single_season['Name'].strip()
                if current_name == tmdb_season_name:
                    if not client.config.IS_DOCKER:
                        log.info(f'⏭️  [季名跳过] 《{series_name}》 第{season_index}季{from_cache} - 季名一致 [{season_name}]')
                    continue
                else:
                    log.info(f'📺 [季名更新] 《{series_name}》 第{season_index}季{from_cache} ➔ [{current_name}] 更名为 [{tmdb_season_name}]')

                single_season['Name'] = tmdb_season_name
                if 'LockedFields' not in single_season:
                    single_season['LockedFields'] = []
                if 'Name' not in single_season['LockedFields']:
                    single_season['LockedFields'].append('Name')

                if client.update_item(season_id, single_season):
                    process_count += 1

    return process_count

def run_renamer(sys_config: Config = None):
    cfg = sys_config or Config()
    cfg.load_script_config(config)

    client = EmbyClient(cfg)
    total_processed = 0

    if not cfg.LIB_NAME:
        log.error("❌ LIB_NAME 未配置，无法处理。")
        return

    libs = cfg.LIB_NAME.split(',')
    for lib_name in libs:
        lib_name = lib_name.strip()
        parent_id = client.get_library_id(lib_name)
        if not parent_id:
            continue

        series_list = client.get_lib_items(parent_id)
        log.info(f'📁 ════════ [季名重命名: {lib_name}] 共有 {len(series_list)} 个剧集，开始处理 ════════')

        for serie in series_list:
            serie_id = serie['Id']
            serie_name = serie['Name']
            is_movie = serie.get('Type') == 'Movie'
            if is_movie:
                continue
            if 'ProviderIds' in serie and 'Tmdb' in serie['ProviderIds']:
                tmdb_id = serie['ProviderIds']['Tmdb']
                total_processed += rename_seasons(client, serie_id, tmdb_id, serie_name, is_movie)
            else:
                log.error(f'⚠️  [季名跳过] 《{serie_name}》 未匹配到 TMDB ID')

    log.info(f'✅ [季名刮削完成] 成功更新 {total_processed} 条条目')

if __name__ == '__main__':
    run_renamer()
