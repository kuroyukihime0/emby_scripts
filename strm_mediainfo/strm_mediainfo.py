import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from common.config import Config
from common.logger import setup_logger
from common.emby_client import EmbyClient

log = setup_logger('strm_mediainfo')

config = {
    'EMBY_SERVER': 'http://xxx:8096',
    'API_KEY': '',
    'USER_ID': '',
    'LIB_NAME': '',
    'DRY_RUN': True,
    'DELAY': 10,
}

def playbackinfo(client: EmbyClient, item_id: str, name: str, delay: int = 10):
    url = f"{client.config.EMBY_SERVER.rstrip('/')}/Items/{item_id}/PlaybackInfo?AutoOpenLiveStream=true&IsPlayback=true&api_key={client.config.API_KEY}&UserId={client.config.USER_ID}"
    try:
        resp = client.session.post(url, headers=client.headers)
        if resp.status_code == 200:
            log.info(f'  {name} success')
            time.sleep(delay)
            return True
        else:
            log.error(f'  {name} error: {resp.status_code}')
            time.sleep(delay)
            return False
    except Exception as e:
        log.error(f'  {name} exception: {e}')
        time.sleep(delay)
        return False

def process_item(client: EmbyClient, item_id: str, name: str, delay: int = 10):
    item = client.get_item(item_id)
    if not item:
        return False

    if 'MediaStreams' in item:
        if item.get('LocationType') == 'Virtual':
            return False
        if len(item['MediaStreams']) == 0:
            log.info(f"** 开始处理 {name}")
            if not client.config.DRY_RUN:
                return playbackinfo(client, item_id, name, delay=delay)
    return False

def process_series(client: EmbyClient, parent_id: str, delay: int = 10):
    processed = 0
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
            ep_id = ep.get('Id')
            ep_name = ep.get('Name')
            if process_item(client, ep_id, f'{series_name} {season_name} {ep_name}', delay=delay):
                processed += 1
    return processed

def run_strm_mediainfo(sys_config: Config = None):
    cfg = sys_config or Config()
    cfg.load_script_config(config)

    client = EmbyClient(cfg)
    delay = config.get('DELAY', 10)
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
        log.info(f'**库 {lib_name} 中共有 {len(items)} 个 item，开始处理')
        for item in items:
            item_id = item['Id']
            name = item['Name']
            item_type = item.get('Type')
            if item_type == 'Movie':
                if process_item(client, item_id, name, delay=delay):
                    process_count += 1
            elif item_type == 'Series':
                process_count += process_series(client, item_id, delay=delay)

    log.info(f'**更新成功 {process_count} 条')

if __name__ == '__main__':
    run_strm_mediainfo()
