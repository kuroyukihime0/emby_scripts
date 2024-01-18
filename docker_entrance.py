import os
import time

import logging
from alternative_renamer import alternative_renamer
from country_scraper import country_scraper
from genre_mapper import genre_mapper
from season_renamer import season_renamer

ENV_RUN_INTERVAL_HOURS = int(os.environ['RUN_INTERVAL_HOURS'])
ENV_ENABLE_ALTERNATIVE_RENAMER = (os.getenv('ENABLE_ALTERNATIVE_RENAMER') in['True','true'])
ENV_ENABLE_COUNTRY_SCAPTER = (os.getenv('ENABLE_COUNTRY_SCAPTER') in['True','true'])
ENV_ENABLE_GENRE_MAPPER = (os.getenv('ENABLE_GENRE_MAPPER') in['True','true'])
ENV_ENABLE_SEASON_RENAMER = (os.getenv('ENABLE_SEASON_RENAMER') in['True','true'])


ENV_EMBY_HOST = os.environ["EMBY_HOST"]
ENV_EMBY_API_KEY = os.environ["EMBY_API_KEY"]
ENV_EMBY_USER_ID = os.environ["EMBY_USER_ID"]
ENV_TMDB_KEY = os.environ["TMDB_KEY"]
ENV_LIB_NAME = os.environ["LIB_NAME"]
ENV_DRY_RUN = (os.getenv('DRY_RUN') in['True','true'])
ENV_ADD_HANT_TITLE = (os.getenv('ADD_HANT_TITLE') in['True','true'])

log = logging.getLogger('entrance')
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


def get_or_default(value, default=None):
    return value if value else default

def work():
    try:
        if ENV_ENABLE_ALTERNATIVE_RENAMER:
            log.info('START ALTERNATIVE_RENAMER')
            alternative_renamer.run_renameer()
        else:
            log.info('SKIP ALTERNATIVE_RENAMER')
        if ENV_ENABLE_SEASON_RENAMER:
            log.info('START SEASON_RENAMER')
            season_renamer.run_renamer()
        else:
            log.info('SKIP SEASON_RENAMER')
        if ENV_ENABLE_COUNTRY_SCAPTER:
            log.info('START COUNTRY_SCAPTER')
            country_scraper.run_scraper()
        else:
            log.info('SKIP COUNTRY_SCAPTER')
        if ENV_ENABLE_GENRE_MAPPER:
            log.info('START GENRE_MAPPER')
            genre_mapper.run_mapper()
        else:
            log.info('SKIP GENRE_MAPPER')
    except Exception as ex:
        log.error(str(ex))


def work_loop():
    while True:
        work()
        interval_hour = ENV_RUN_INTERVAL_HOURS if ENV_RUN_INTERVAL_HOURS else 24
        time.sleep(interval_hour * 3600)


if __name__ == "__main__":
    modules = [alternative_renamer, country_scraper,
               genre_mapper, season_renamer]
    assert ENV_EMBY_HOST
    assert ENV_EMBY_API_KEY
    assert ENV_EMBY_USER_ID
    assert ENV_LIB_NAME
    
    for module in modules:
        config = module.config

        config['EMBY_SERVER'] = ENV_EMBY_HOST if ENV_EMBY_HOST else ''
        config['API_KEY'] = ENV_EMBY_API_KEY if ENV_EMBY_API_KEY else ''
        config['USER_ID'] = ENV_EMBY_USER_ID if ENV_EMBY_USER_ID else ''
        config['TMDB_KEY'] = ENV_TMDB_KEY if ENV_TMDB_KEY else ''
        config['LIB_NAME'] = ENV_LIB_NAME if ENV_LIB_NAME else ''
        config['DRY_RUN'] = ENV_DRY_RUN
        config['ADD_HANT_TITLE'] = ENV_ADD_HANT_TITLE
        config['IS_DOCKER'] = True

    work_loop()
