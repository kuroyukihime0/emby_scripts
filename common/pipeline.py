import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from common.config import Config
from common.logger import setup_logger
from common.emby_client import EmbyClient
from common.tmdb_client import fetch_tmdb_detail, get_or_default
from common.status_tracker import status_tracker
from alternative_renamer.alternative_renamer import invalid_char_in_str
from country_scraper.country_scraper import country_dict, language_dict, DEFAULT_COUNTRY, DEFAULT_LANGUAGE
from genre_mapper.genre_mapper import genre_mapping, genre_remove
from season_renamer.season_renamer import rename_seasons

log = setup_logger('pipeline')

def run_pipeline(cfg: Config):
    """
    高效统一合并流水线：
    1. 单次遍历媒体库
    2. 单次 GET 拉取 Item 详情
    3. 单次并发/缓存拉取 TMDB 描述
    4. 内存中合并应用 AlternativeRenamer, CountryScraper, GenreMapper 修改
    5. 集中一次 POST 提交数据更新
    """
    status_tracker.set_running("Unified Pipeline")
    status_tracker.reset_stats()

    client = EmbyClient(cfg)
    if not cfg.LIB_NAME:
        log.error("❌ LIB_NAME 未配置，请在环境变量或配置中设置。")
        status_tracker.set_idle(cfg.RUN_INTERVAL_HOURS)
        return

    libs = cfg.LIB_NAME.split(',')
    total_updated = 0

    log.info(f"🚀 === [Pipeline] 启动全流水线任务 (DryRun={cfg.DRY_RUN}) ===")

    try:
        for lib_name in libs:
            lib_name = lib_name.strip()
            parent_id = client.get_library_id(lib_name)
            if not parent_id:
                continue

            items = client.get_lib_items(parent_id)
            log.info(f"📁 === [Pipeline] 开始处理媒体库 [{lib_name}]，包含 {len(items)} 个条目 ===")
            status_tracker.update_stats(processed_delta=len(items))

            for item in items:
                item_id = item['Id']
                item_name = item['Name']
                is_movie = item.get('Type') == 'Movie'
                is_series = item.get('Type') == 'Series'

                # 1. 集中 GET 一次 Emby Item 详情
                emby_item = client.get_item(item_id)
                if not emby_item:
                    continue

                item_modified = False
                tmdb_data = None
                is_cache = False

                # 获取 TMDB 数据（如果需要）
                tmdb_id = emby_item.get('ProviderIds', {}).get('Tmdb')
                if tmdb_id and (cfg.ENABLE_ALTERNATIVE_RENAMER or cfg.ENABLE_COUNTRY_SCRAPER or cfg.ENABLE_SEASON_RENAMER):
                    tmdb_data, is_cache = fetch_tmdb_detail(client.session, cfg.TMDB_KEY, tmdb_id, is_movie=is_movie)

                from_cache = ' ⚡(Cache)' if is_cache else ''

                # --- 模块 A: AlternativeRenamer ---
                if cfg.ENABLE_ALTERNATIVE_RENAMER and tmdb_data:
                    titles = tmdb_data.get("alternative_titles", {})
                    raw_alt_names = titles.get("titles" if is_movie else "results", []) or []
                    cn_alt_names = [x['title'] for x in raw_alt_names if x.get("iso_3166_1") == "CN"]

                    if cfg.ADD_HANT_TITLE and tmdb_data.get('hant_trans'):
                        cn_alt_names.extend(tmdb_data['hant_trans'])

                    if cn_alt_names:
                        name_spliter = ' / '
                        old_sort_name = emby_item.get('SortName', '')
                        old_names = old_sort_name.split(name_spliter) if old_sort_name else []

                        res = [name for name in old_names if name]
                        for new_name in cn_alt_names:
                            if new_name not in res and not invalid_char_in_str(new_name):
                                res.append(new_name)

                        sort_name_all = name_spliter.join(res)
                        if old_names != res:
                            log.info(f"🏷️ [{item_name}]{from_cache} 增加别名: [{sort_name_all}]")
                            emby_item['SortName'] = sort_name_all
                            emby_item['ForcedSortName'] = sort_name_all
                            if 'LockedFields' not in emby_item:
                                emby_item['LockedFields'] = []
                            if 'SortName' not in emby_item['LockedFields']:
                                emby_item['LockedFields'].append('SortName')
                            item_modified = True

                # --- 模块 B: CountryScraper ---
                if cfg.ENABLE_COUNTRY_SCRAPER and tmdb_data:
                    prod_countries = tmdb_data.get("production_countries", [])
                    spoken_langs = tmdb_data.get("spoken_languages", [])

                    if prod_countries or spoken_langs:
                        old_tags = [tag['Name'] for tag in emby_item.get('TagItems', [])]
                        new_tags = old_tags[:]

                        tmdb_countries = []
                        for country in prod_countries:
                            tag = get_or_default(country_dict, country.get('iso_3166_1'), DEFAULT_COUNTRY)
                            if tag not in tmdb_countries:
                                tmdb_countries.append(tag)

                        for country in tmdb_countries:
                            if country not in new_tags and (country != DEFAULT_COUNTRY or len(tmdb_countries) <= 2):
                                new_tags.append(country)

                        tmdb_languages = []
                        for language in spoken_langs:
                            tag = get_or_default(language_dict, language.get('iso_639_1'), DEFAULT_LANGUAGE)
                            if tag not in tmdb_languages:
                                tmdb_languages.append(tag)

                        for language in tmdb_languages:
                            if language not in new_tags and (language != DEFAULT_LANGUAGE or len(tmdb_languages) <= 2):
                                new_tags.append(language)

                        if new_tags != old_tags:
                            log.info(f"🌍 [{item_name}]{from_cache} 设置标签为: {new_tags}")
                            emby_item['Tags'] = new_tags
                            if 'TagItems' not in emby_item:
                                emby_item['TagItems'] = []
                            for tag in new_tags:
                                if tag not in old_tags:
                                    emby_item['TagItems'].append({'Name': tag})
                            if 'LockedFields' not in emby_item:
                                emby_item['LockedFields'] = []
                            if 'Tags' not in emby_item['LockedFields']:
                                emby_item['LockedFields'].append('Tags')
                            item_modified = True

                # --- 模块 C: GenreMapper ---
                if cfg.ENABLE_GENRE_MAPPER:
                    genres = emby_item.get('Genres', [])
                    genres_items = emby_item.get('GenreItems', [])
                    need_replace = any(g in genre_mapping or g in genre_remove for g in genres) or \
                                   any(g_item.get('Name') in genre_mapping for g_item in genres_items)

                    if need_replace:
                        genres_new = [genre_mapping[g]['Name'] if g in genre_mapping else g for g in genres]
                        genres_new = [g for g in genres_new if g not in genre_remove and g != '']
                        log.info(f"🎭 [{item_name}] 修改 Genre: {genres} --> {genres_new}")
                        emby_item['Genres'] = genres_new

                        new_genre_items = []
                        for g_item in genres_items:
                            g_name = g_item.get('Name')
                            if g_name in genre_mapping:
                                new_genre_items.append(genre_mapping[g_name])
                            elif g_name not in genre_remove and g_name != '':
                                new_genre_items.append(g_item)

                        emby_item['GenreItems'] = new_genre_items
                        item_modified = True

                # --- 集中一次提交更新 ---
                if item_modified:
                    if client.update_item(item_id, emby_item):
                        total_updated += 1
                        status_tracker.update_stats(updated_delta=1)
                        log.info(f"✅ [{item_name}] 成功合并集中更新提交！")

                # --- 模块 D: SeasonRenamer (仅在剧集且启用时) ---
                if is_series and cfg.ENABLE_SEASON_RENAMER and tmdb_id:
                    rename_seasons(client, item_id, tmdb_id, item_name, is_movie=False)

        log.info(f"🎉 === [Pipeline] 全流水线执行完毕，共集中更新 {total_updated} 条条目 ===")
    except Exception as e:
        log.error(f"❌ [Pipeline] 执行过程中出现异常: {e}", exc_info=True)
        status_tracker.update_stats(errors_delta=1)
    finally:
        status_tracker.set_idle(cfg.RUN_INTERVAL_HOURS)
