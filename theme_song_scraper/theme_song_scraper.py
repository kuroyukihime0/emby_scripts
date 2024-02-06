import os
import re
import requests
import json
import shutil
import time
from yt_dlp import YoutubeDL

SERIES_DIR = [
    r"Z:\Anime",
]
MOVIE_DIR = [
    r"W:\Movie",
]
# 是否下载电影的视频
DOWNLOAD_MOVIE_BACKDROPS = True

count = 0
session = requests.Session()
theme_file = "theme.mp3"
theme_file_m4a = "theme.m4a"
backdrop_dir = "backdrops"
movie_theme_db = []
current_dir = os.path.abspath(os.path.dirname(__file__))
json_file = os.path.join(current_dir, "lizardbyte.json")


def download_movie_theme_json():
    if os.path.exists(json_file):
        pass
    else:
        download_file(
            "",
            json_file,
        )


def load_movie_theme_json():
    download_movie_theme_json()
    global movie_theme_db
    try:
        f = open(json_file, "rb")
        content = f.read()
        movie_theme_db = json.loads(content)
        print(f"load lizardbyte.json success, {len(movie_theme_db)} items found")
    except Exception as ex:
        pass


def get_tvdb_id(nfo_file, pattern=r'<uniqueid type="tvdb">(.*?)</uniqueid>'):
    with open(nfo_file, "r", encoding="utf-8", errors="ignore") as file:
        content = file.read()
        matches = re.findall(pattern, content)
        for match in matches:
            return match
    return None


def get_json(url):
    response = session.get(url)
    if response.status_code == 200:
        resp_json = response.json()
        return resp_json
    else:
        return None


def download_file(url, dest):
    global count
    dest_dir = os.path.dirname(dest)
    response = session.get(url)
    if response.status_code == 200:
        with open(dest, "wb") as file:
            file.write(response.content)
        count += 1
        print(f"{dest} download success")
    else:
        print(f"{dest_dir} no theme song found")
        pass


def process_series():
    for lib in SERIES_DIR:
        if not os.path.exists(lib):
            print(f"{lib} not found")
            continue
        items = os.listdir(lib)
        for item in items:
            item_dir = os.path.join(lib, item)
            item_files = os.listdir(item_dir)
            if theme_file in item_files:
                # print(f"{item_dir} 已经存在theme.mp3 跳过")
                pass
            else:
                tv_nfo = os.path.join(item_dir, "tvshow.nfo")
                if os.path.exists(tv_nfo):
                    tvdb_id = get_tvdb_id(tv_nfo)
                    if tvdb_id:
                        url = f"http://tvthemes.plexapp.com/{tvdb_id}.mp3"
                        dest = os.path.join(item_dir, theme_file)
                        download_file(url, dest)
                    else:
                        # print(f"no tvdbid found with {item} ")
                        pass


def get_dirs_have_nfo(dir):
    res = []
    childs = os.listdir(dir)
    for child in childs:
        child_abs_path = os.path.join(dir, child)
        if child.endswith(".nfo") and dir not in res:
            res.append(dir)
        if os.path.isdir(child_abs_path):
            res = res + get_dirs_have_nfo(child_abs_path)
    return res


def download_audio(link,try_time = 0):
    if try_time >=3:
        return None
    try:
        with YoutubeDL(
            {
                "extract_audio": True,
                "format": "m4a/mp3",
                "quiet": True,
                "outtmpl": f"temp/theme.%(ext)s",
            }
        ) as video:
            video.download(link)
        return True
    except Exception as ex:
        time.sleep(try_time*5)
        download_audio(link,try_time+1)


def download_video(link,try_time = 0):
    if try_time >=3:
        return None
    try:
        ydl_opts = {
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "writethumbnail": False,
            "write_all_thumbnails": False,
            "outtmpl": f"temp/%(title)s.mp4",
            "verbose": False,
            "quiet": True,
        }
        with YoutubeDL(ydl_opts) as video:
            video.download(link)
        return True
    except Exception as ex:
        time.sleep(try_time*5)
        download_video(link,try_time+1)


def video_file_path(path):
    childs = os.listdir(path)
    for child in childs:
        if child.endswith(".mp4"):
            return os.path.join(path, child)
    return None

def audio_file_path(path):
    childs = os.listdir(path)
    for child in childs:
        if child.endswith(".m4a") or child.endswith('.mp3'):
            return os.path.join(path, child)
    return None


def download_theme_for_movies(theme_url, dest_dir):
    global count
    youtube_url = theme_url
    childs = os.listdir(dest_dir)
    if theme_file not in childs and theme_file_m4a not in childs:
        print(f"start downloading theme audio for {dest_dir}")
        audio = download_audio(youtube_url)
        if not audio:
            return
        audio_file = audio_file_path("temp/")
        res = shutil.move(audio_file, dest_dir)
        count += 1
        print(f"download success to {res}")
    else:
        print(f"--{dest_dir}/theme.mp3 existed, skip")
    if DOWNLOAD_MOVIE_BACKDROPS and backdrop_dir not in childs:
        print(f"start downloading backdrops for {dest_dir}")
        video = download_video(youtube_url)
        if not video:
            return
        video_file = video_file_path("temp/")
        backdrop_path = os.path.join(dest_dir, backdrop_dir)
        os.makedirs(backdrop_path)
        res = shutil.move(video_file, os.path.join(dest_dir, backdrop_path))
        count += 1
        print(f"download success to {res}")
    else:
        print(f"--{dest_dir}/backdrops existed, skip")


def process_movies():
    load_movie_theme_json()
    for lib in MOVIE_DIR:
        if not os.path.exists(lib):
            print(f"{lib} not found")
            continue

        nfo_dirs = get_dirs_have_nfo(lib)

        for nfo_dir in nfo_dirs:
            childs = os.listdir(nfo_dir)
            if (theme_file in childs or theme_file_m4a in childs) and (backdrop_dir in childs or not DOWNLOAD_MOVIE_BACKDROPS):
                print(f"--skip {nfo_dir}")
            else:
                nfo_file = next(child for child in childs if child.endswith(".nfo"))
                nfo_file = os.path.join(nfo_dir, nfo_file)
                tmdb_id = get_tvdb_id(
                    nfo_file, r'<uniqueid type="tmdb">(.*?)</uniqueid>'
                )
                imdb_id = get_tvdb_id(
                    nfo_file, r'<uniqueid type="imdb">(.*?)</uniqueid>'
                )
                for db_item in movie_theme_db:
                    if str(db_item["id"]) == tmdb_id:
                        download_theme_for_movies(db_item['theme'], nfo_dir)
                        break
                    elif db_item["imdb_id"] == imdb_id:
                        download_theme_for_movies(db_item['theme'], nfo_dir)
                        break


process_series()
process_movies()
print(f'download {count} theme songs for total')
