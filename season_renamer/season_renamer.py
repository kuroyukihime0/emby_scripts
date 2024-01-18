import requests
import json
import os
import logging
from dateutil import parser
import datetime

config = {
    # 设置 Emby 服务器地址
    'EMBY_SERVER' :'http://xxx:8096',
    # 设置 Emby 服务器APIKEY和userid
    'API_KEY' : '',
    'USER_ID' : '',
    # 设置 TMDB_KEY
    'TMDB_KEY' : '',
    # 库名, 多个时英文逗号分隔, 只支持剧集/电影库
    'LIB_NAME' : '',
    # True 时为预览效果, False 实际写入
    'DRY_RUN' : True,
}

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

def emby_headers(): 
    return {
    'X-Emby-Token': config['API_KEY'],
    'Content-Type': 'application/json',
}

session = requests.session()

process_count = 0


class JsonDataBase:
    def __init__(self, name, prefix='', db_type='dict', workdir=None):
        self.file_name = f'{prefix}_{name}.json' if prefix else f'{name}.json'
        self.file_path = os.path.join(
            workdir, self.file_name) if workdir else self.file_name
        self.db_type = db_type
        self.data = self.load()

    def load(self, encoding='utf-8'):
        try:
            with open(self.file_path, encoding=encoding) as f:
                _json = json.load(f)
        except (FileNotFoundError, ValueError):
            # log.info(f'{self.file_name} not exist, return {self.db_type}')
            return dict(list=[], dict={})[self.db_type]
        else:
            return _json

    def dump(self, obj, encoding='utf-8'):
        with open(self.file_path, 'w', encoding=encoding) as f:
            json.dump(obj, f, indent=2, ensure_ascii=False)

    def save(self):
        self.dump(self.data)


class TmdbDataBase(JsonDataBase):
    def __getitem__(self, tmdb_id):
        data = self.data.get(tmdb_id)
        if not data:
            return
        air_date = datetime.date.today()
        try:
            air_date = parser.parse(data['premiere_date']).date()
        except Exception as ex:
            pass
        today = datetime.date.today()
        if air_date + datetime.timedelta(days=90) > today:
            expire_day = 15
        elif air_date + datetime.timedelta(days=365) > today:
            expire_day = 30
        else:
            expire_day = 365
        update_date = datetime.date.fromisoformat(data['update_date'])
        if update_date + datetime.timedelta(days=expire_day) < today:
            return
        return data

    def __setitem__(self, key, value):
        self.data[key] = value
        self.save()

    def clean_not_trust_data(self, expire_days=7, min_trust=0.5):
        expire_days = datetime.timedelta(days=expire_days)
        today = datetime.date.today()
        self.data = {_id: info for _id, info in self.data.items()
                     if info['trust'] >= min_trust or
                     datetime.date.fromisoformat(info['update_date']) + expire_days > today}
        self.save()

    def save_seasons(self, tmdb_id, premiere_date, name, alt_names, seasons=None):
        self.data[tmdb_id] = {
            'premiere_date': premiere_date,
            'name': name,
            'alt_names': alt_names,
            'seasons': seasons,
            'update_date': str(datetime.date.today()),
        }
        self.save()


def get_or_default(_dict, key, default=None):
    return _dict[key] if key in _dict else default


tmdb_db = TmdbDataBase('tmdb')


def get_season_info_from_tmdb(tmdb_id, is_movie, serie_name):
    cache_key = ('mv' if is_movie else 'tv') + f'{tmdb_id}'
    cache_data = tmdb_db[cache_key]
    if cache_data:
        alt_names = cache_data['seasons']
        return alt_names, True
    url = f"https://api.themoviedb.org/3/tv/{tmdb_id}?language=zh-CN&append_to_response=alternative_titles"
    response = session.get(url, headers= {
        "accept": "application/json",
        "Authorization": f"Bearer {config['TMDB_KEY']}"
    })
    resp_json = response.json()
    if 'seasons' in resp_json:
        titles = resp_json["alternative_titles"]
        release_date = get_or_default(
            resp_json, 'last_air_date', default=get_or_default(resp_json, 'first_air_date'))
        alt_names = get_or_default(
            titles, "results", None)
        tmdb_db.save_seasons(cache_key, premiere_date=release_date,
                             name=serie_name, alt_names=alt_names, seasons=resp_json['seasons'])
        return resp_json['seasons'], False
    else:

        return None, None


def rename_seasons(parent_id, tmdb_id, series_name, is_movie):
    global process_count
    # 获取剧集列表
    params = {'ParentId': parent_id}
    response = session.get(f"{config['EMBY_SERVER']}/emby/Items",
                           headers=emby_headers(), params=params)

    tmdb_seasons, is_cache = get_season_info_from_tmdb(tmdb_id, is_movie,series_name)
    from_cache = ' fromcache ' if is_cache else ''
    if not tmdb_seasons:
        log.error(f'   no season found in tmdb:{tmdb_id} {series_name}')
        return
    seasons = response.json()['Items']
    for season in seasons:
        seaeson_id = season['Id']
        season_name = season['Name']
        series_name = season['SeriesName']
        if 'IndexNumber' not in season:
            log.info(f'   {series_name} {season_name} 没有编号,跳过')
            continue
        season_index = season['IndexNumber']
        tmdb_season = tmdb_seasons
        tmdb_season = next(
            (season for season in tmdb_seasons if season['season_number'] == season_index), None)
        if tmdb_season:
            tmdb_season_name = tmdb_season['name']
            single_season_response = session.get(
                f"{config['EMBY_SERVER']}/emby/Users/{config['USER_ID']}/Items/{seaeson_id}?Fields=ChannelMappingInfo&api_key={config['API_KEY']}", headers=emby_headers(), params=params)
            single_season = single_season_response.json()
            if 'Name' in single_season:
                if season_name == tmdb_season_name:
                    if get_or_default(config,'IS_DOCKER') != True:
                        log.info(
                            f'   {series_name} 第{season_index}季 {from_cache} [{season_name}] 季名一致 跳过更新')
                    continue
                else:
                    log.info(
                        f'   {series_name} 第{season_index}季 {from_cache} 将从 [{season_name}] 更名为 [{tmdb_season_name}]')
                single_season['Name'] = tmdb_season_name
                if 'LockedFields' not in single_season:
                    single_season['LockedFields'] = []
                if 'Name' not in single_season['LockedFields']:
                    single_season['LockedFields'].append('Name')
                if not config['DRY_RUN']:
                    update_url = f"{config['EMBY_SERVER']}/emby/Items/{seaeson_id}?api_key={config['API_KEY']}&reqformat=json"
                    response = session.post(
                        update_url, json=single_season, headers=emby_headers())
                    if response.status_code == 200 or response.status_code == 204:
                        process_count += 1
                        # log.info(f'      Successfully updated {series_name} {season_name} : {response.status_code} {response.content}')
                    else:
                        log.info(
                            f'      Failed to update {series_name} {season_name}: {response.status_code} {response.content}')


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

def run_renamer():
    libs = config['LIB_NAME'].split(',')
    for lib_name in libs:
        parent_id = get_library_id(lib_name.strip())
        series = get_lib_items(parent_id)
        log.info(f'**库 {lib_name} 中共有{len(series)} 个剧集，开始处理')

        for serie in series:
            serie_id = serie['Id']
            serie_name = serie['Name']
            is_movie = serie['Type'] == 'Movie'
            tmdb_id = ''
            if is_movie:
                continue
            if 'ProviderIds' in serie and 'Tmdb' in serie['ProviderIds']:
                tmdb_id = serie['ProviderIds']['Tmdb']
                rename_seasons(serie_id, tmdb_id, serie_name, is_movie)
            else:
                log.error(f'error:{serie_name} has no tmdb id, skip')

    log.info(f'**更新成功{process_count}条')



if __name__ == '__main__':
    run_renamer()