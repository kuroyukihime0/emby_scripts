import os

def parse_bool(env_value, default=False):
    if env_value is None:
        return default
    if isinstance(env_value, bool):
        return env_value
    return str(env_value).lower() in ['true', '1', 'yes']

class Config:
    def __init__(self):
        # 服务器与认证配置
        self.EMBY_SERVER = os.getenv('EMBY_HOST') or os.getenv('EMBY_SERVER', 'http://xxx:8096')
        self.API_KEY = os.getenv('EMBY_API_KEY', '')
        self.USER_ID = os.getenv('EMBY_USER_ID', '')
        self.TMDB_KEY = os.getenv('TMDB_KEY', '')
        self.LIB_NAME = os.getenv('LIB_NAME', '')

        # 运行行为配置
        self.CACHE_DB_PATH = os.getenv('CACHE_DB_PATH', 'data/cache.db')
        self.DRY_RUN = parse_bool(os.getenv('DRY_RUN'), True)
        self.ADD_HANT_TITLE = parse_bool(os.getenv('ADD_HANT_TITLE'), True)
        self.IS_DOCKER = parse_bool(os.getenv('IS_DOCKER'), False)
        self.RUN_INTERVAL_HOURS = int(os.getenv('RUN_INTERVAL_HOURS', '24'))

        # Web 控制台配置
        self.ENABLE_WEB = parse_bool(os.getenv('ENABLE_WEB'), False)
        self.WEB_PORT = int(os.getenv('WEB_PORT', '3888'))
        self.WEB_PASSWORD = os.getenv('WEB_PASSWORD', '').strip()

        # 模块使能配置 (完美兼容拼写错别字 ENABLE_COUNTRY_SCAPTER 与标准 ENABLE_COUNTRY_SCRAPER)
        self.ENABLE_ALTERNATIVE_RENAMER = parse_bool(os.getenv('ENABLE_ALTERNATIVE_RENAMER'), False)
        country_scraper_env = os.getenv('ENABLE_COUNTRY_SCRAPER')
        if country_scraper_env is None:
            country_scraper_env = os.getenv('ENABLE_COUNTRY_SCAPTER')
        self.ENABLE_COUNTRY_SCRAPER = parse_bool(country_scraper_env, False)

        self.ENABLE_GENRE_MAPPER = parse_bool(os.getenv('ENABLE_GENRE_MAPPER'), False)
        self.ENABLE_SEASON_RENAMER = parse_bool(os.getenv('ENABLE_SEASON_RENAMER'), False)

    def load_script_config(self, local_config: dict):
        """
        当脚本直接运行而非通过 Docker 或中央入口运行时，
        优先从脚本本身的 local_config 字典更新（若本地有有效设置）
        """
        if not local_config:
            return

        if local_config.get('EMBY_SERVER') and local_config['EMBY_SERVER'] != 'http://xxx:8096':
            self.EMBY_SERVER = local_config['EMBY_SERVER']
        if local_config.get('API_KEY'):
            self.API_KEY = local_config['API_KEY']
        if local_config.get('USER_ID'):
            self.USER_ID = local_config['USER_ID']
        if local_config.get('TMDB_KEY'):
            self.TMDB_KEY = local_config['TMDB_KEY']
        if local_config.get('LIB_NAME'):
            self.LIB_NAME = local_config['LIB_NAME']
        if 'DRY_RUN' in local_config:
            self.DRY_RUN = parse_bool(local_config['DRY_RUN'], self.DRY_RUN)
        if 'ADD_HANT_TITLE' in local_config:
            self.ADD_HANT_TITLE = parse_bool(local_config['ADD_HANT_TITLE'], self.ADD_HANT_TITLE)

    def to_dict(self):
        return {
            'EMBY_SERVER': self.EMBY_SERVER,
            'API_KEY': self.API_KEY,
            'USER_ID': self.USER_ID,
            'TMDB_KEY': self.TMDB_KEY,
            'LIB_NAME': self.LIB_NAME,
            'DRY_RUN': self.DRY_RUN,
            'ADD_HANT_TITLE': self.ADD_HANT_TITLE,
            'IS_DOCKER': self.IS_DOCKER,
        }
