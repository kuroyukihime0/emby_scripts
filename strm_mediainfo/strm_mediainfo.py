import requests
import json
import time

# 设置 Emby 服务器地址和 API 密钥
EMBY_SERVER = 'http://xxx:8096'  # 根据您的 Emby 服务器地址修改
# API 密钥
API_KEY = ''
USER_ID = ''
# 库名 英文逗号分隔
LIB_NAME = ''
# True 时为测试, False 实际写入
DRY_RUN = True
# 扫描延迟
DELAY = 10


process_count = 0
headers = {
    'X-Emby-Token': API_KEY,
    'Content-Type': 'application/json',
}

session = requests.session()


def playbackinfo(item_id, name):
    global process_count
    resp = session.post(
        f'{EMBY_SERVER}/Items/{item_id}/PlaybackInfo?AutoOpenLiveStream=true&IsPlayback=true&api_key={API_KEY}&UserId={USER_ID}', headers=headers)
    if resp.status_code == 200:
        process_count+1
        print(f'  {name} success')
    else:
        print(f'  {name} error')
    time.sleep(DELAY)


def process_item(item_id, name):
    resp = session.get(
        f'{EMBY_SERVER}/emby/Users/{USER_ID}/Items/{item_id}?Fields=ChannelMappingInfo&api_key={API_KEY}', headers=headers)
    item = resp.json()
    if 'MediaStreams' in item:
        if 'LocationType' in item and item['LocationType'] == 'Virtual':
            return
        if len(item['MediaStreams']) == 0:
            print(f"** 开始处理{name}")
            if not DRY_RUN:
                playbackinfo(item_id, name)


def process_series(parent_id):
    params = {'ParentId': parent_id}
    response = session.get(f'{EMBY_SERVER}/emby/Items',
                           headers=headers, params=params)

    seasons = response.json()['Items']
    for seasons in seasons:
        seaeson_id = seasons['Id']
        season_name = seasons['Name']
        series_name = seasons['SeriesName']
        params = {
            'ParentId': seaeson_id,
            'IncludeItemTypes': 'Episode',
            'Recursive': 'true',
            'SortBy': 'SortName',
            'SortOrder': 'Ascending'
        }
        epoisode_response = session.get(
            f'{EMBY_SERVER}/emby/Items', headers=headers, params=params)
        episodes = epoisode_response.json()['Items']
        for episode in episodes:
            episode_id = episode['Id']
            episode_name = episode['Name']
            process_item(
                episode_id, f'{series_name} {season_name} {episode_name}')


def get_library_id(name):
    if not name:
        return
    res = session.get(
        f'{EMBY_SERVER}/emby/Library/VirtualFolders', headers=headers)
    lib_id = [i['ItemId'] for i in res.json() if i['Name'] == name]
    if not lib_id:
        raise KeyError(f'library: {name} not exists, check it')
    return lib_id[0] if lib_id else None


def get_lib_items(parent_id):
    params = {'ParentId': parent_id,
              #   'HasTmdbId': True,
              'fields': 'ProviderIds'
              }
    response = session.get(f'{EMBY_SERVER}/emby/Items',
                           headers=headers, params=params)
    items = response.json()['Items']
    items_folder = [item for item in items if item["Type"] == "Folder"]
    items = [item for item in items if item["Type"] != "Folder"]
    for folder in items_folder:
        items = items + get_lib_items(folder['Id'])

    return items


if __name__ == '__main__':
    libs = LIB_NAME.split(',')
    for lib_name in libs:
        parent_id = get_library_id(lib_name.strip())
        series = get_lib_items(parent_id)
        print(f'**库 {lib_name} 中共有{len(series)} 个item，开始处理')
        for serie in series:
            serie_id = serie['Id']
            name = serie['Name']
            type = serie['Type']
            if type == 'Movie':
                process_item(serie_id, name)
            elif type == 'Series':
                process_series(serie_id)

    print(f'**更新成功{process_count}条')
