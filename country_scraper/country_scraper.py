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
    # 设置 TMDB_KEY（API 读访问令牌）
    'TMDB_KEY' : '',
    # 库名, 多个时英文逗号分隔, 只支持剧集/电影库
    'LIB_NAME' : '',
    # True 时为预览效果, False 实际写入
    'DRY_RUN' : True,
}

country_dict = {
    'KR': '韩国',
    'CN': '中国',
    'HK': '香港',
    'TW': '台湾',
    'JP': '日本',
    'US': '美国',
    'GB': '英国',
    'FR': '法国',
    'DE': '德国',
    'IN': '印度',
    'RU': '俄罗斯',
    'CA': '加拿大',

}
DEFAULT_COUNTRY = '其他国家'
DEFAULT_LANGUAGE = '其他语种'
language_dict = {
    'cn': '粤语',
    'zh': '国语',
    'ja': '日语',
    'en': '英语',
    'ko': '韩语',
    'fr': '法语',
    'de': '德语',
    'ru': '俄语',
    'es': '西班牙语',
}


log = logging.getLogger('country_scraper')
log.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s %(levelname)s:  %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
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

    def save_country(self, tmdb_id, premiere_date, name, production_countries, spoken_languages):
        self.data[tmdb_id] = {
            'premiere_date': premiere_date,
            'name': name,
            'production_countries': production_countries,
            'spoken_languages': spoken_languages,
            'update_date': str(datetime.date.today()),
        }
        self.save()


def get_or_default(_dict, key, default=None):
    return _dict[key] if key in _dict else default


tmdb_db = TmdbDataBase('country')


def get_country_info_from_tmdb(tmdb_id, serie_name, is_movie=False):
    cache_key = ('mv' if is_movie else 'tv') + f'{tmdb_id}'
    cache_data = tmdb_db[cache_key]
    if cache_data and 'production_countries' in cache_data:
        production_countries = cache_data["production_countries"]
        spoken_languages = cache_data["spoken_languages"]
        return production_countries, spoken_languages, True

    url = f"https://api.themoviedb.org/3/{'movie' if is_movie else 'tv'}/{tmdb_id}?language=zh-CN"
    response = session.get(url, headers={
        "accept": "application/json",
        "Authorization": f"Bearer {config['TMDB_KEY']}"
    })
    resp_json = response.json()
    # print(resp_json)
    if "production_countries" in resp_json or "spoken_languages" in resp_json:
        production_countries = resp_json["production_countries"]
        spoken_languages = resp_json["spoken_languages"]
        release_date = get_or_default(resp_json, 'release_date') if is_movie else get_or_default(
            resp_json, 'last_air_date', default=get_or_default(resp_json, 'first_air_date'))
        tmdb_db.save_country(
            cache_key, premiere_date=release_date, name=serie_name, production_countries=production_countries, spoken_languages=spoken_languages)
        return production_countries, spoken_languages, True
    else:
        log.error(f'   no result found in tmdb:{serie_name} {resp_json}')
        return None, None, None


def add_country(parent_id, tmdb_id, serie_name, is_movie):
    global process_count
    production_countries, spoken_languages, is_cache = get_country_info_from_tmdb(
        tmdb_id, serie_name, is_movie=is_movie)
    from_cache = ' fromcache ' if is_cache else ''
    if not production_countries and not spoken_languages:
        log.info(f'   {serie_name} {from_cache} 没有设置国家 跳过')
        return

    item_response = session.get(
        f"{config['EMBY_SERVER']}/emby/Users/{config['USER_ID']}/Items/{parent_id}?Fields=ChannelMappingInfo&api_key={config['API_KEY']}", headers=emby_headers())
    item = item_response.json()

    series_name = item['Name']
    old_tags = item['TagItems']
    old_tags = [tag['Name']for tag in old_tags]

    new_tags = old_tags[:]

    tmdb_countries = []
    for country in production_countries:
        tag = get_or_default(
            country_dict, country['iso_3166_1'], DEFAULT_COUNTRY)
        if tag not in tmdb_countries:
            tmdb_countries.append(tag)

    for country in tmdb_countries:
        if country not in new_tags:
            if country != DEFAULT_COUNTRY or len(tmdb_countries) <= 2:
                new_tags.append(country)

    tmdb_languages = []
    for language in spoken_languages:
        tag = get_or_default(
            language_dict, language['iso_639_1'], DEFAULT_LANGUAGE)
        if tag not in new_tags:
            tmdb_languages.append(tag)

    for language in tmdb_languages:
        if language not in new_tags:
            if language != DEFAULT_LANGUAGE or len(tmdb_languages) <= 2:
                new_tags.append(language)

    if new_tags == old_tags:
        log.info(f'   {serie_name} {from_cache} 标签没有变化 跳过')
        return
    else:
        log.info(f'   {serie_name} {from_cache} 设置标签为 {new_tags}')

    item['Tags'] = new_tags
    if 'TagItems' not in item:
        item['TagItems'] = []

    for tag in new_tags:
        if tag not in old_tags:
            item['TagItems'].append({'Name': tag})

    if 'LockedFields' not in item:
        item['LockedFields'] = []
    if 'Tags' not in item['LockedFields']:
        item['LockedFields'].append('Tags')

    if not config['DRY_RUN']:
        update_url = f"{config['EMBY_SERVER']}/emby/Items/{parent_id}?api_key={config['API_KEY']}&reqformat=json"
        response = session.post(update_url, json=item, headers=emby_headers())
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


def run_scraper():
    libs = config['LIB_NAME'].split(',')
    for lib_name in libs:
        parent_id = get_library_id(lib_name.strip())
        items = get_lib_items(parent_id)

        log.info(f'**库 {lib_name} 中共有{len(items)} 个Item, 开始处理')

        for item in items:
            item_id = item['Id']
            item_name = item['Name']
            is_movie = item['Type'] == 'Movie'
            if 'ProviderIds' in item and 'Tmdb' in item['ProviderIds']:
                tmdb_id = item['ProviderIds']['Tmdb']
                add_country(item_id, tmdb_id, item_name, is_movie=is_movie)
            else:
                log.info(f'error:{item_name} has no tmdb id, skip')

    log.info(f'**更新成功{process_count}条')

if __name__ == '__main__':
    run_scraper()
    
