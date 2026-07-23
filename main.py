import os
import sys
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common.config import Config
from common.logger import setup_logger
from common.pipeline import run_pipeline

from alternative_renamer import alternative_renamer
from country_scraper import country_scraper
from delete_episode_genre import delete_episode_genre
from genre_mapper import genre_mapper
from season_renamer import season_renamer
from strm_mediainfo import strm_mediainfo
from theme_song_scraper import theme_song_scraper

log = setup_logger('main')

TASKS = {
    'alt_renamer': ('Alternative Renamer (别名刮削)', alternative_renamer.run_renamer),
    'season_renamer': ('Season Renamer (季名刮削)', season_renamer.run_renamer),
    'country_scraper': ('Country & Language Scraper (国家/语言标签刮削)', country_scraper.run_scraper),
    'genre_mapper': ('Genre Mapper (Genre替换与清理)', genre_mapper.run_mapper),
    'delete_episode_genre': ('Delete Episode Genre (清空单集Genre)', delete_episode_genre.run_deleter),
    'strm_mediainfo': ('STRM MediaInfo Force Scraper (强制刷STRM媒体信息)', strm_mediainfo.run_strm_mediainfo),
    'theme_song_scraper': ('Theme Song & Video Scraper (主题曲与视频背景刮削)', lambda cfg: theme_song_scraper.run_theme_scraper()),
}

def main():
    parser = argparse.ArgumentParser(description="Emby Scripts - 统一控制台入口")
    parser.add_argument('--pipeline', action='store_true', help="使用高效合并管道 (单次遍历 + 单次更新)")
    parser.add_argument('--run', choices=list(TASKS.keys()), help="运行指定的单独脚本模块")
    parser.add_argument('--all', action='store_true', help="依次单独运行所有可用脚本模块")

    args = parser.parse_args()

    cfg = Config()

    if not args.pipeline and not args.run and not args.all:
        parser.print_help()
        sys.exit(1)

    if args.pipeline:
        log.info("\n=================== [Executing Unified Pipeline Mode] ===================")
        run_pipeline(cfg)
    elif args.all:
        for task_key, (task_name, task_func) in TASKS.items():
            log.info(f"\n=================== [Executing: {task_name}] ===================")
            try:
                task_func(cfg)
            except Exception as e:
                log.error(f"Error executing {task_name}: {e}", exc_info=True)
    elif args.run:
        task_name, task_func = TASKS[args.run]
        log.info(f"\n=================== [Executing: {task_name}] ===================")
        task_func(cfg)

if __name__ == '__main__':
    main()
