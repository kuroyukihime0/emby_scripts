import requests
import json

# 设置 Emby 服务器地址和 API 密钥
EMBY_SERVER = 'http://xxx:8096'
# 设置 API 密钥
API_KEY = ''
# 设置 USERID
USER_ID = ''

# 设置库名, 多个时用,隔开
LIB_NAME = 'A,B'

# True 时为测试, False 实际写入
DRY_RUN = True
# 需要替换的Genre
genre_mapping = {
    'Sci-Fi & Fantasy': {
        'Name': '科幻', 'Id': 16630},
    'War & Politics': {
        'Name': '战争', 'Id': 16718},
}
# 需要移除的Genre
genre_remove = ['']


headers = {
    'X-Emby-Token': API_KEY,
    'Content-Type': 'application/json',
}

session = requests.session()


process_count = 0


def remove_genre_for_episodes(parent_id):
    # 获取剧集列表
    params = {'Ids': parent_id}
    series_detail = session.get(
        f'{EMBY_SERVER}/emby/Users/{USER_ID}/Items/{parent_id}?Fields=ChannelMappingInfo&api_key={API_KEY}', headers=headers, params=params)
    series = series_detail.json()
    genres = series['Genres']
    genres_items = series['GenreItems']
    need_replace = False
    for genre in genres:
        if genre in genre_mapping:
            need_replace = True
    for genre_item in genres_items:
        if genre_item['Name'] in genre_mapping:
            need_replace = True

    if need_replace:
        print(f'{series["Name"]} 需要替换Genre')
        print(series['Genres'])
        series['Genres'] = [genre_mapping[genre]['Name']
                            if genre in genre_mapping else genre for genre in genres]

        series['Genres'] = list(
            filter(lambda genre: genre not in genre_remove, series['Genres']))
        print("-->"+series['Genres'])
        series['GenreItems'] = [genre_mapping[genre_item['Name']] if genre_item['Name']
                                in genre_mapping else genre_item for genre_item in genres_items]
        series['GenreItems'] = list(
            filter(lambda genre_item: genre_item['Name'] not in genre_remove, series['GenreItems']))
        if not DRY_RUN:
            update_url = f'{EMBY_SERVER}/emby/Items/{parent_id}?api_key={API_KEY}&reqformat=json'
            response = session.post(
                update_url, json=series, headers=headers)
            if response.status_code == 200 or response.status_code == 204:
                process_count += 1
                print(
                    f'      Successfully updated series {parent_id} : {response.status_code} {response.content}')
            else:
                print(
                    f'      Failed to update series {parent_id}: {response.status_code} {response.content}')


def get_library_id(name):
    if not name:
        return
    res = session.get(
        f'{EMBY_SERVER}/emby/Library/VirtualFolders', headers=headers)
    lib_id = [i['ItemId'] for i in res.json() if i['Name'] == name]
    if not lib_id:
        raise KeyError(f'library: {name} not exists, check it')
    return lib_id[0] if lib_id else None


if __name__ == '__main__':
    libs = LIB_NAME.split(',')
    for lib_name in libs:
        parent_id = get_library_id(lib_name.strip())
        params = {'ParentId': parent_id}
        response = session.get(f'{EMBY_SERVER}/emby/Items',
                               headers=headers, params=params)
        series = response.json()['Items']
        print(f'**库 {lib_name} 中共有{len(series)} 个剧集，开始处理')
        for serie in series:
            serie_id = serie['Id']
            remove_genre_for_episodes(serie_id)

        print(f'**更新成功{process_count}条')
