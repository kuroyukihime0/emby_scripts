import requests
import json
import os
import logging
from dateutil import parser
import datetime

# 设置 Emby 服务器地址
EMBY_SERVER = 'http://xxx:8096'
# 设置 Emby 服务器APIKEY和userid
API_KEY = ''
USER_ID = ''
# 设置 TMDB_KEY
TMDB_KEY = ''
# 库名, 多个时英文逗号分隔, 只支持剧集/电影库
LIB_NAME = ''
# True 时为预览效果, False 实际写入
DRY_RUN = True


log = logging.getLogger('alt_renamer')
log.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s %(levelname)s:  %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
fh = logging.FileHandler('alt_renamer.log', encoding='utf-8')
fh.setLevel(logging.DEBUG)
fh.setFormatter(formatter)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(formatter)
log.addHandler(ch)
log.addHandler(fh)

headers = {
    'X-Emby-Token': API_KEY,
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
            log.error(f'{self.file_name} not exist, return {self.db_type}')
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

    def save_alt_name(self, tmdb_id, premiere_date, name, alt_names, seasons=None):
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


def get_alt_name_info_from_tmdb(tmdb_id, serie_name, is_movie=False):
    cache_key = ('mv' if is_movie else 'tv') + f'{tmdb_id}'
    cache_data = tmdb_db[cache_key]
    if cache_data and 'alt_names' in cache_data:
        alt_names = cache_data['alt_names']
        return alt_names, True

    url = f"https://api.themoviedb.org/3/{'movie' if is_movie else 'tv'}/{tmdb_id}?append_to_response=alternative_titles&language=zh-CN"
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {TMDB_KEY}"
    }
    response = session.get(url, headers=headers)
    resp_json = response.json()
    if "alternative_titles" in resp_json:
        titles = resp_json["alternative_titles"]
        release_date = get_or_default(resp_json, 'release_date') if is_movie else get_or_default(
            resp_json, 'last_air_date', default=get_or_default(resp_json, 'first_air_date'))
        alt_names = get_or_default(
            titles, "titles" if is_movie else "results", None)
        if not alt_names:
            log.error(f'   alt names missing in tmdb:{serie_name} {resp_json}')
        tmdb_db.save_alt_name(
            cache_key, premiere_date=release_date, name=serie_name, alt_names=alt_names, seasons=get_or_default(resp_json, 'seasons'))
        return alt_names, False
    else:
        log.error(f'   no result found in tmdb:{serie_name} {resp_json}')
        return None, None


def add_alt_names(parent_id, tmdb_id, serie_name, is_movie):
    global process_count
    tmdb_alt_name, is_cache = get_alt_name_info_from_tmdb(
        tmdb_id, serie_name, is_movie=is_movie)
    from_cache = ' fromcache ' if is_cache else ''
    if not tmdb_alt_name:
        log.error(f'   no result found in tmdb:{serie_name}')
        return

    tmdb_alt_name = [x['title']
                     for x in tmdb_alt_name if x["iso_3166_1"] == "CN"]

    if len(tmdb_alt_name) == 0:
        log.info(f'   {serie_name} {from_cache} 没有别名 跳过')
        return

    name_spliter = ' / '
    item_response = session.get(
        f'{EMBY_SERVER}/emby/Users/{USER_ID}/Items/{parent_id}?Fields=ChannelMappingInfo&api_key={API_KEY}', headers=headers, params=params)
    item = item_response.json()
    # if name_spliter in item['OriginalTitle']:
    #     log.info(item['OriginalTitle'])
    # if name_spliter in item['SortName']:
    #     log.info(item['SortName'])
    # return

    series_name = item['Name']

    if 'SortName' in item:
        old_names = item['SortName'].split(name_spliter)
        res = old_names[:]
        for new_name in tmdb_alt_name:
            if new_name not in res:
                res.append(new_name)

        sort_name_all = name_spliter.join(res)
        if old_names == res:
            log.info(f'   {series_name} {from_cache} 别名没有增删 跳过')
            return
        else:
            log.info(f'   {series_name} {from_cache} 增加别名 [{sort_name_all}]')
        item['SortName'] = sort_name_all
        item['ForcedSortName'] = sort_name_all
        # item['SortName'] = item['Name']
        # item['ForcedSortName'] = item['Name']
        if 'LockedFields' not in item:
            item['LockedFields'] = []
        if 'Name' not in item['LockedFields']:
            item['LockedFields'].append('SortName')
        if not DRY_RUN:
            update_url = f'{EMBY_SERVER}/emby/Items/{parent_id}?api_key={API_KEY}&reqformat=json'
            response = session.post(update_url, json=item, headers=headers)
            if response.status_code == 200 or response.status_code == 204:
                process_count += 1
                # log.info(f'      Successfully updated {series_name} {season_name} : {response.status_code} {response.content}')
            else:
                log.info(
                    f'      Failed to update {series_name} : {response.status_code} {response.content}')


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
        items = get_lib_items(parent_id)
        log.info(f'**库 {lib_name} 中共有{len(items)} 个Item，开始处理')

        for item in items:
            item_id = item['Id']
            item_name = item['Name']
            is_movie = item['Type'] == 'Movie'
            if 'ProviderIds' in item and 'Tmdb' in item['ProviderIds']:
                tmdb_id = item['ProviderIds']['Tmdb']
                add_alt_names(item_id, tmdb_id, item_name, is_movie=is_movie)
            else:
                log.info(f'error:{item_name} has no tmdb id, skip')

    log.info(f'**更新成功{process_count}条')
