import requests
from opencc import OpenCC
from common.logger import setup_logger
from common.sqlite_cache import tmdb_cache

logger = setup_logger('tmdb_client')
cc = OpenCC('t2s')

def get_or_default(_dict, key, default=None):
    return _dict[key] if _dict and key in _dict else default

def fetch_tmdb_detail(session: requests.Session, tmdb_key: str, tmdb_id: str, is_movie: bool = False):
    """
    统一获取并缓存 TMDB 的详细信息（合并 alternative_titles, translations, production_countries, spoken_languages, seasons 等）
    """
    cache_key = ('mv' if is_movie else 'tv') + f'{tmdb_id}'
    cached_data = tmdb_cache.get(cache_key)
    if cached_data:
        return cached_data, True

    if not tmdb_key:
        logger.error("TMDB_KEY is not configured.")
        return None, False

    media_type = 'movie' if is_movie else 'tv'
    url = f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}?append_to_response=alternative_titles,translations&language=zh-CN"
    try:
        response = session.get(url, headers={
            "accept": "application/json",
            "Authorization": f"Bearer {tmdb_key}"
        })
        resp_json = response.json()
    except Exception as ex:
        logger.exception(f"TMDB request failed for {media_type}/{tmdb_id}: {ex}")
        return None, False

    if "alternative_titles" in resp_json or "production_countries" in resp_json or "seasons" in resp_json:
        release_date = get_or_default(resp_json, 'release_date') if is_movie else get_or_default(
            resp_json, 'last_air_date', default=get_or_default(resp_json, 'first_air_date'))

        # 解析繁体中文转换
        translations = get_or_default(resp_json, "translations")
        translations_list = get_or_default(translations, "translations") if translations else []
        hant_trans = [
            cc.convert(tran['data']['title' if is_movie else 'name'])
            for tran in translations_list
            if tran.get("iso_3166_1") in ["HK", "TW"] and len(tran['data'].get('title' if is_movie else 'name', '').strip()) != 0
        ]
        resp_json['hant_trans'] = hant_trans

        # 写入 SQLite 统一缓存
        tmdb_cache.set(cache_key, resp_json, premiere_date=release_date)
        return resp_json, False
    else:
        logger.error(f"No valid data returned from TMDB for {media_type}/{tmdb_id}: {resp_json}")
        return None, False
