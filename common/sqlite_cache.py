import os
import json
import sqlite3
import datetime
from dateutil import parser
from common.logger import setup_logger

from common.config import Config

logger = setup_logger('sqlite_cache')

class SQLiteTMDBCache:
    def __init__(self, db_path=None):
        self.db_path = db_path or Config().CACHE_DB_PATH
        self._init_db()
        self._migrate_old_json_caches()

    def _get_connection(self):
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        try:
            db_dir = os.path.dirname(self.db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
            with self._get_connection() as conn:
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS tmdb_cache (
                        cache_key TEXT PRIMARY KEY,
                        data TEXT NOT NULL,
                        premiere_date TEXT,
                        update_date TEXT NOT NULL
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to initialize SQLite DB: {e}")

    def get(self, cache_key: str) -> dict:
        """
        根据 cache_key ('mv1234' 或 'tv5678') 查询缓存，并检查过期策略
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT data, premiere_date, update_date FROM tmdb_cache WHERE cache_key = ?", (cache_key,))
                row = cursor.fetchone()
                if not row:
                    return None

                data_str, premiere_date_str, update_date_str = row['data'], row['premiere_date'], row['update_date']
                data = json.loads(data_str)

                # 检查过期天数
                today = datetime.date.today()
                air_date = today
                if premiere_date_str:
                    try:
                        air_date = parser.parse(premiere_date_str).date()
                    except Exception:
                        pass

                if air_date + datetime.timedelta(days=30) > today:
                    expire_day = 3
                elif air_date + datetime.timedelta(days=90) > today:
                    expire_day = 15
                elif air_date + datetime.timedelta(days=365) > today:
                    expire_day = 30
                else:
                    expire_day = 365

                update_date = datetime.date.fromisoformat(update_date_str)
                if update_date + datetime.timedelta(days=expire_day) < today:
                    return None

                return data
        except Exception as e:
            logger.error(f"Error fetching from SQLite cache [{cache_key}]: {e}")
            return None

    def set(self, cache_key: str, data: dict, premiere_date: str = None):
        """
        更新或写入单个 TMDB 缓存项
        """
        try:
            today_str = str(datetime.date.today())
            data_str = json.dumps(data, ensure_ascii=False)
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT INTO tmdb_cache (cache_key, data, premiere_date, update_date)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(cache_key) DO UPDATE SET
                        data=excluded.data,
                        premiere_date=excluded.premiere_date,
                        update_date=excluded.update_date
                """, (cache_key, data_str, premiere_date, today_str))
                conn.commit()
        except Exception as e:
            logger.error(f"Error saving to SQLite cache [{cache_key}]: {e}")

    def _migrate_old_json_caches(self):
        """
        读取并无缝合并迁移旧版 json 缓存（tmdb_alt_name.json, country.json, tmdb.json）。
        针对同一 item id 不同字段进行 dict 深度合并，成功写入数据库后删除原 json 文件。
        """
        search_paths = [
            'tmdb_alt_name.json', 'country.json', 'tmdb.json',
            'data/tmdb_alt_name.json', 'data/country.json', 'data/tmdb.json',
            'alternative_renamer/tmdb_alt_name.json',
            'country_scraper/country.json',
            'season_renamer/tmdb.json'
        ]

        for json_file in search_paths:
            if not os.path.exists(json_file):
                continue

            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    file_data = json.load(f)

                if not isinstance(file_data, dict):
                    continue

                today_str = str(datetime.date.today())
                migrated_keys = 0

                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    for cache_key, val in file_data.items():
                        if not isinstance(val, dict):
                            continue

                        # 查找 SQLite 中已存在的记录
                        cursor.execute("SELECT data, premiere_date, update_date FROM tmdb_cache WHERE cache_key = ?", (cache_key,))
                        row = cursor.fetchone()

                        if row:
                            try:
                                existing_dict = json.loads(row['data'])
                            except Exception:
                                existing_dict = {}
                            # 字段深度合并：新旧属性互补融合
                            existing_dict.update(val)
                            merged_dict = existing_dict

                            p_date = val.get('premiere_date') or row['premiere_date']
                            u_date = val.get('update_date') or row['update_date'] or today_str
                        else:
                            merged_dict = val
                            p_date = val.get('premiere_date')
                            u_date = val.get('update_date', today_str)

                        merged_str = json.dumps(merged_dict, ensure_ascii=False)
                        cursor.execute("""
                            INSERT INTO tmdb_cache (cache_key, data, premiere_date, update_date)
                            VALUES (?, ?, ?, ?)
                            ON CONFLICT(cache_key) DO UPDATE SET
                                data=excluded.data,
                                premiere_date=excluded.premiere_date,
                                update_date=excluded.update_date
                        """, (cache_key, merged_str, p_date, u_date))
                        migrated_keys += 1

                    conn.commit()

                # 迁移合并成功，彻底删除原 JSON 文件
                os.remove(json_file)
                logger.info(f"成功迁移并合并旧缓存 [{json_file}]（包含 {migrated_keys} 项数据），原 JSON 文件已删除。")

            except Exception as e:
                logger.error(f"迁移合并旧 JSON 缓存 [{json_file}] 失败: {e}", exc_info=True)


class LazyTMDBCacheProxy:
    """
    懒加载代理类，确保导入模块时不立即触发全局 SQLiteTMDBCache 实例创建
    """
    def __init__(self):
        self._instance = None

    def _get_instance(self):
        if self._instance is None:
            self._instance = SQLiteTMDBCache()
        return self._instance

    def get(self, cache_key: str):
        return self._get_instance().get(cache_key)

    def set(self, cache_key: str, data: dict, premiere_date: str = None):
        return self._get_instance().set(cache_key, data, premiere_date)

# 全局单例缓存（延迟加载）
tmdb_cache = LazyTMDBCacheProxy()
