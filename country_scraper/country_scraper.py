import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from common.config import Config
from common.logger import setup_logger
from common.emby_client import EmbyClient
from common.tmdb_client import fetch_tmdb_detail, get_or_default

log = setup_logger('country_scraper')

config = {
    'EMBY_SERVER': 'http://xxx:8096',
    'API_KEY': '',
    'USER_ID': '',
    'TMDB_KEY': '',
    'LIB_NAME': '',
    'DRY_RUN': True,
}

country_dict = {
    'KR': '韩国', 'CN': '中国', 'HK': '香港', 'TW': '台湾',
    'JP': '日本', 'US': '美国', 'GB': '英国', 'FR': '法国',
    'DE': '德国', 'IN': '印度', 'RU': '俄罗斯', 'CA': '加拿大',
}
DEFAULT_COUNTRY = '其他国家'
DEFAULT_LANGUAGE = '其他语种'

language_dict = {
    'cn': '粤语', 'zh': '国语', 'ja': '日语', 'en': '英语',
    'ko': '韩语', 'fr': '法语', 'de': '德语', 'ru': '俄语',
    'es': '西班牙语',
}

def run_scraper(sys_config: Config = None):
    cfg = sys_config or Config()
    cfg.load_script_config(config)

    client = EmbyClient(cfg)
    process_count = 0

    if not cfg.LIB_NAME:
        log.error("❌ LIB_NAME 未配置，无法处理。")
        return

    libs = cfg.LIB_NAME.split(',')
    for lib_name in libs:
        lib_name = lib_name.strip()
        parent_id = client.get_library_id(lib_name)
        if not parent_id:
            continue

        items = client.get_lib_items(parent_id)
        log.info(f'📁 ════════ [国家/语言刮削: {lib_name}] 共有 {len(items)} 个条目，开始处理 ════════')

        for item in items:
            item_id = item['Id']
            item_name = item['Name']
            is_movie = item.get('Type') == 'Movie'

            if 'ProviderIds' in item and 'Tmdb' in item['ProviderIds']:
                tmdb_id = item['ProviderIds']['Tmdb']
                tmdb_data, is_cache = fetch_tmdb_detail(client.session, cfg.TMDB_KEY, tmdb_id, is_movie=is_movie)
                from_cache = ' ⚡(Cache)' if is_cache else ''

                if not tmdb_data:
                    continue

                prod_countries = tmdb_data.get("production_countries", [])
                spoken_langs = tmdb_data.get("spoken_languages", [])

                if not prod_countries and not spoken_langs:
                    if not cfg.IS_DOCKER:
                        log.info(f'⏭️  [标签跳过] 《{item_name}》{from_cache} - 未查询到国家/语言')
                    continue

                emby_item = client.get_item(item_id)
                if not emby_item:
                    continue

                series_name = emby_item.get('Name', item_name)
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

                if new_tags == old_tags:
                    if not cfg.IS_DOCKER:
                        log.info(f'⏭️  [标签跳过] 《{series_name}》{from_cache} - 标签无变化')
                    continue
                else:
                    log.info(f'🌍 [标签更新] 《{series_name}》{from_cache} ➔ 设置标签: {new_tags}')

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

                if client.update_item(item_id, emby_item):
                    process_count += 1
            else:
                log.info(f'⚠️  [标签跳过] 《{item_name}》未匹配到 TMDB ID，自动跳过')

    log.info(f'✅ [国家/语言刮削完成] 成功更新 {process_count} 条条目')

if __name__ == '__main__':
    run_scraper()
