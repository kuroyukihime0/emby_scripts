import requests
import json

# 设置 Emby 服务器地址和 API 密钥
EMBY_SERVER = 'http://xxx:8096'
# 设置 API 密钥
API_KEY = ''
# 设置 USERID
USER_ID = ''

# 设置库名, 多个时用,隔开(只支持剧集库, 填电影库后果自负)
LIB_NAME = 'A,B'
# True 时为测试, False 实际写入
DRY_RUN = True


headers = {
    'X-Emby-Token': API_KEY,
    'Content-Type': 'application/json',
}

session = requests.session()

process_count = 0


def remove_genre_for_episodes(parent_id):
    # 获取剧集列表
    params = {'ParentId': parent_id}
    response = session.get(f'{EMBY_SERVER}/emby/Items',
                           headers=headers, params=params)

    seasons = response.json()['Items']
    for seasons in seasons:
        seaeson_id = seasons['Id']
        season_name = seasons['Name']
        series_name = seasons['SeriesName']
        # 获取分集ID
        params = {
            'ParentId': seaeson_id,
            'Fields': 'Genres,Overview',
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
            params = {'Ids': episode_id}
            single_epoisode_response = session.get(
                f'{EMBY_SERVER}/emby/Users/{USER_ID}/Items/{episode_id}?Fields=ChannelMappingInfo&api_key={API_KEY}', headers=headers, params=params)
            episode = single_epoisode_response.json()
            if 'Genres' in episode:
                if len(episode['Genres']) != 0:
                    genre = episode['Genres']
                    print(
                        f'   {series_name} {season_name} {episode_name} 清除genre {genre}')
                    episode['Genres'] = []
                    episode['GenreItems'] = []
                    if not DRY_RUN:
                        update_url = f'{EMBY_SERVER}/emby/Items/{episode_id}?api_key={API_KEY}&reqformat=json'
                        response = session.post(
                            update_url, json=episode, headers=headers)
                        if response.status_code == 200 or response.status_code == 204:
                            process_count += 1
                            print(
                                f'      Successfully updated episode {episode_id} : {response.status_code} {response.content}')
                        else:
                            print(
                                f'      Failed to update episode {episode_id}: {response.status_code} {response.content}')


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
