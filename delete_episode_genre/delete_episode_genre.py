import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from common.config import Config
from common.logger import setup_logger
from common.emby_client import EmbyClient

log = setup_logger('delete_episode_genre')

# 本地配置兼容
config = {
    'EMBY_SERVER': 'http://xxx:8096',
    'API_KEY': '',
    'USER_ID': '',
    'LIB_NAME': '',
    'DRY_RUN': True,
}

def remove_genre_for_episodes(client: EmbyClient, parent_id: str):
    process_count = 0
    url = f"{client.config.EMBY_SERVER.rstrip('/')}/emby/Items"
    params = {'ParentId': parent_id}

    try:
        response = client.session.get(url, headers=client.headers, params=params)
        seasons = response.json().get('Items', [])
    except Exception as e:
        log.error(f"Failed to get seasons for parent {parent_id}: {e}")
        return 0

    for season in seasons:
        season_id = season.get('Id')
        season_name = season.get('Name')
        series_name = season.get('SeriesName')

        params = {
            'ParentId': season_id,
            'Fields': 'Genres,Overview',
            'IncludeItemTypes': 'Episode',
            'Recursive': 'true',
            'SortBy': 'SortName',
            'SortOrder': 'Ascending'
        }
        try:
            ep_resp = client.session.get(url, headers=client.headers, params=params)
            episodes = ep_resp.json().get('Items', [])
        except Exception as e:
            log.error(f"Failed to get episodes for season {season_id}: {e}")
            continue

        for ep in episodes:
            episode_id = ep.get('Id')
            episode_name = ep.get('Name')

            ep_item = client.get_item(episode_id)
            if not ep_item:
                continue

            if ep_item.get('Genres'):
                genre = ep_item['Genres']
                log.info(f'   {series_name} {season_name} {episode_name} 清除 genre {genre}')
                ep_item['Genres'] = []
                ep_item['GenreItems'] = []

                if client.update_item(episode_id, ep_item):
                    process_count += 1

    return process_count

def run_deleter(sys_config: Config = None):
    cfg = sys_config or Config()
    cfg.load_script_config(config)

    client = EmbyClient(cfg)
    total_processed = 0

    if not cfg.LIB_NAME:
        log.error("LIB_NAME is not configured.")
        return

    libs = cfg.LIB_NAME.split(',')
    for lib_name in libs:
        lib_name = lib_name.strip()
        parent_id = client.get_library_id(lib_name)
        if not parent_id:
            continue

        series = client.get_lib_items(parent_id)
        log.info(f'**库 {lib_name} 中共有 {len(series)} 个剧集，开始处理')
        for serie in series:
            serie_id = serie['Id']
            total_processed += remove_genre_for_episodes(client, serie_id)

    log.info(f'**更新成功 {total_processed} 条')

run_delete_genre = run_deleter

if __name__ == '__main__':
    run_deleter()
