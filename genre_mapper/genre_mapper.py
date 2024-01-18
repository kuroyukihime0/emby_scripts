import requests
import json
import logging

config = {
    # 设置 Emby 服务器地址
    'EMBY_SERVER' :'http://xxx:8096',
    # 设置 Emby 服务器APIKEY和userid
    'API_KEY' : '',
    'USER_ID' : '',
    # 库名, 多个时英文逗号分隔, 只支持剧集/电影库
    'LIB_NAME' : '',
    # True 时为预览效果, False 实际写入
    'DRY_RUN' : True,
}


# 需要替换的Genre
genre_mapping = {
    'Sci-Fi & Fantasy': {
        'Name': '科幻', 'Id': 16630},
    'War & Politics': {
        'Name': '战争', 'Id': 16718},
}
# 需要移除的Genre
genre_remove = ['']


def emby_headers(): 
    return {
    'X-Emby-Token': config['API_KEY'],
    'Content-Type': 'application/json',
}

session = requests.session()

process_count = 0

log = logging.getLogger('season_renamer')
log.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
fh = logging.FileHandler('logs.log', encoding='utf-8')
fh.setLevel(logging.DEBUG)
fh.setFormatter(formatter)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(formatter)
log.addHandler(ch)
log.addHandler(fh)


def remove_genre_for_episodes(parent_id):
    global process_count
    # 获取剧集列表
    params = {'Ids': parent_id}
    series_detail = session.get(
        f"{config['EMBY_SERVER']}/emby/Users/{config['USER_ID']}/Items/{parent_id}?Fields=ChannelMappingInfo&api_key={config['API_KEY']}", headers=emby_headers(), params=params)
    series = series_detail.json()
    genres = series['Genres']
    genres_items = series['GenreItems']
    need_replace = False
    for genre in genres:
        if genre in genre_mapping or genre in genre_remove:
            need_replace = True
    for genre_item in genres_items:
        if genre_item['Name'] in genre_mapping:
            need_replace = True

    if need_replace:
        log.info(f'{series["Name"]}:')
        genres_new = [genre_mapping[genre]['Name']
                      if genre in genre_mapping else genre for genre in genres]
        genres_new = list(
            filter(lambda genre: genre not in genre_remove, genres_new))
        log.info('   '+str(series['Genres'])+"-->"+str(genres_new))
        series['Genres'] = genres_new

        series['GenreItems'] = [genre_mapping[genre_item['Name']] if genre_item['Name']
                                in genre_mapping else genre_item for genre_item in genres_items]
        series['GenreItems'] = list(
            filter(lambda genre_item: genre_item['Name'] not in genre_remove, series['GenreItems']))
        if not config['DRY_RUN']:
            update_url = f"{config['EMBY_SERVER']}/emby/Items/{parent_id}?api_key={config['API_KEY']}&reqformat=json"
            response = session.post(
                update_url, json=series, headers=emby_headers())
            if response.status_code == 200 or response.status_code == 204:
                process_count += 1
            else:
                log.error(f'      Failed to update series {parent_id}: {response.status_code} {response.content}')


def get_library_id(name):
    if not name:
        return
    res = session.get(
        f"{config['EMBY_SERVER']}/emby/Library/VirtualFolders", headers=emby_headers())
    lib_id = [i['ItemId'] for i in res.json() if i['Name'] == name]
    if not lib_id:
        raise KeyError(f'library: {name} not exists, check it')
    return lib_id[0] if lib_id else None


def get_lib_items(parent_id):
    params = {'ParentId': parent_id,
              #   'HasTmdbId': True,
              'fields': 'ProviderIds'
              }
    response = session.get(f"{config['EMBY_SERVER']}/emby/Items",
                           headers=emby_headers(), params=params)
    items = response.json()['Items']
    items_folder = [item for item in items if item["Type"] == "Folder"]
    items = [item for item in items if item["Type"] != "Folder"]
    for folder in items_folder:
        items = items + get_lib_items(folder['Id'])

    return items

def run_mapper():
    libs = config['LIB_NAME'].split(',')
    for lib_name in libs:
        parent_id = get_library_id(lib_name.strip())
        series = get_lib_items(parent_id)
        log.info(f'**库 {lib_name} 中共有{len(series)} 个剧集，开始处理')
        for serie in series:
            serie_id = serie['Id']
            remove_genre_for_episodes(serie_id)

    log.info(f'**更新成功{process_count}条')

if __name__ == '__main__':
    run_mapper()
    
