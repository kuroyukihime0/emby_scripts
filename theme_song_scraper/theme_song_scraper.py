import os
import sys
import re
import json
import shutil
import time
import requests
from yt_dlp import YoutubeDL

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from common.logger import setup_logger

log = setup_logger('theme_song_scraper')

SERIES_DIR = [
    r"Z:\Anime",
]
MOVIE_DIR = [
    r"W:\Movie",
]

DOWNLOAD_MOVIE_BACKDROPS = True

theme_file = "theme.mp3"
theme_file_m4a = "theme.m4a"
backdrop_dir = "backdrops"
movie_theme_db = []
current_dir = os.path.abspath(os.path.dirname(__file__))
json_file = os.path.join(current_dir, "lizardbyte.json")

session = requests.Session()

def download_file(url, dest):
    dest_dir = os.path.dirname(dest)
    try:
        response = session.get(url)
        if response.status_code == 200:
            with open(dest, "wb") as file:
                file.write(response.content)
            log.info(f"🎵 [主题曲下载成功] ➔ {dest}")
            return True
        else:
            log.info(f"⏭️  [主题曲跳过] {dest_dir} 未查询到对应的 Theme 曲目")
            return False
    except Exception as e:
        log.error(f"❌ [主题曲下载异常] {url}: {e}")
        return False

def download_movie_theme_json():
    if not os.path.exists(json_file):
        download_file("", json_file)

def load_movie_theme_json():
    download_movie_theme_json()
    global movie_theme_db
    if os.path.exists(json_file):
        try:
            with open(json_file, "rb") as f:
                content = f.read()
                movie_theme_db = json.loads(content)
                log.info(f"✅ 成功加载 lizardbyte.json，共找到 {len(movie_theme_db)} 条描述信息")
        except Exception as ex:
            log.error(f"❌ 加载 lizardbyte.json 失败: {ex}")

def get_tvdb_id(nfo_file, pattern=r'<uniqueid type="tvdb">(.*?)</uniqueid>'):
    try:
        with open(nfo_file, "r", encoding="utf-8", errors="ignore") as file:
            content = file.read()
            matches = re.findall(pattern, content)
            for match in matches:
                return match
    except Exception:
        pass
    return None

def process_series(series_dirs=None):
    count = 0
    dirs = series_dirs or SERIES_DIR
    for lib in dirs:
        if not os.path.exists(lib):
            log.info(f"⚠️  [路径未找到] {lib}")
            continue
        items = os.listdir(lib)
        for item in items:
            item_dir = os.path.join(lib, item)
            if not os.path.isdir(item_dir):
                continue
            item_files = os.listdir(item_dir)
            if theme_file not in item_files:
                tv_nfo = os.path.join(item_dir, "tvshow.nfo")
                if os.path.exists(tv_nfo):
                    tvdb_id = get_tvdb_id(tv_nfo)
                    if tvdb_id:
                        url = f"http://tvthemes.plexapp.com/{tvdb_id}.mp3"
                        dest = os.path.join(item_dir, theme_file)
                        if download_file(url, dest):
                            count += 1
    return count

def get_dirs_have_nfo(dir_path):
    res = []
    try:
        childs = os.listdir(dir_path)
    except Exception:
        return res

    for child in childs:
        child_abs_path = os.path.join(dir_path, child)
        if child.endswith(".nfo") and dir_path not in res:
            res.append(dir_path)
        if os.path.isdir(child_abs_path):
            res.extend(get_dirs_have_nfo(child_abs_path))
    return res

def download_audio(link, try_time=0):
    if try_time >= 3:
        return None
    try:
        if not os.path.exists("temp"):
            os.makedirs("temp")
        with YoutubeDL({
            "extract_audio": True,
            "format": "m4a/mp3",
            "quiet": True,
            "outtmpl": "temp/theme.%(ext)s",
        }) as video:
            video.download([link])
        return True
    except Exception:
        time.sleep(try_time * 5)
        return download_audio(link, try_time + 1)

def download_video(link, try_time=0):
    if try_time >= 3:
        return None
    try:
        if not os.path.exists("temp"):
            os.makedirs("temp")
        ydl_opts = {
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "writethumbnail": False,
            "write_all_thumbnails": False,
            "outtmpl": "temp/%(title)s.mp4",
            "verbose": False,
            "quiet": True,
        }
        with YoutubeDL(ydl_opts) as video:
            video.download([link])
        return True
    except Exception:
        time.sleep(try_time * 5)
        return download_video(link, try_time + 1)

def video_file_path(path):
    try:
        childs = os.listdir(path)
        for child in childs:
            if child.endswith(".mp4"):
                return os.path.join(path, child)
    except Exception:
        pass
    return None

def audio_file_path(path):
    try:
        childs = os.listdir(path)
        for child in childs:
            if child.endswith(".m4a") or child.endswith('.mp3'):
                return os.path.join(path, child)
    except Exception:
        pass
    return None

def download_theme_for_movies(theme_url, dest_dir, download_backdrops=True):
    count = 0
    youtube_url = theme_url
    childs = os.listdir(dest_dir)
    if theme_file not in childs and theme_file_m4a not in childs:
        log.info(f"🎵 [音频下载开始] {dest_dir}")
        audio = download_audio(youtube_url)
        if audio:
            audio_file = audio_file_path("temp/")
            if audio_file:
                res = shutil.move(audio_file, dest_dir)
                count += 1
                log.info(f"✅ [音频保存成功] ➔ {res}")
    else:
        log.info(f"⏭️  [音频跳过] {dest_dir}/theme.mp3 已存在")

    if download_backdrops and backdrop_dir not in childs:
        log.info(f"🎥 [背景视频下载开始] {dest_dir}")
        video = download_video(youtube_url)
        if video:
            video_file = video_file_path("temp/")
            if video_file:
                backdrop_path = os.path.join(dest_dir, backdrop_dir)
                os.makedirs(backdrop_path, exist_ok=True)
                res = shutil.move(video_file, os.path.join(backdrop_path, os.path.basename(video_file)))
                count += 1
                log.info(f"✅ [背景视频保存成功] ➔ {res}")
    else:
        log.info(f"⏭️  [视频跳过] {dest_dir}/backdrops 已存在")

    return count

def process_movies(movie_dirs=None, download_backdrops=True):
    count = 0
    load_movie_theme_json()
    dirs = movie_dirs or MOVIE_DIR
    for lib in dirs:
        if not os.path.exists(lib):
            log.info(f"⚠️  [路径未找到] {lib}")
            continue

        nfo_dirs = get_dirs_have_nfo(lib)
        for nfo_dir in nfo_dirs:
            childs = os.listdir(nfo_dir)
            if (theme_file in childs or theme_file_m4a in childs) and (backdrop_dir in childs or not download_backdrops):
                log.info(f"⏭️  [扫描跳过] {nfo_dir}")
            else:
                nfo_file = next((child for child in childs if child.endswith(".nfo")), None)
                if not nfo_file:
                    continue
                nfo_path = os.path.join(nfo_dir, nfo_file)
                tmdb_id = get_tvdb_id(nfo_path, r'<uniqueid type="tmdb">(.*?)</uniqueid>')
                imdb_id = get_tvdb_id(nfo_path, r'<uniqueid type="imdb">(.*?)</uniqueid>')
                for db_item in movie_theme_db:
                    if str(db_item.get("id")) == tmdb_id or (imdb_id and db_item.get("imdb_id") == imdb_id):
                        count += download_theme_for_movies(db_item['theme'], nfo_dir, download_backdrops)
                        break
    return count

def run_theme_scraper(series_dirs=None, movie_dirs=None, download_backdrops=True):
    c1 = process_series(series_dirs)
    c2 = process_movies(movie_dirs, download_backdrops)
    total = c1 + c2
    log.info(f'✅ [主题曲刮削完成] 共下载 {total} 个音频/视频资源')
    return total

if __name__ == '__main__':
    run_theme_scraper()
