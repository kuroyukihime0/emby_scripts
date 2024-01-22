import os
import re
import requests

libs = [
    r"Z:\Anime",
    r"Z:\Anime-追番",
]


def get_tvdb_id(nfo_file):
    with open(nfo_file, 'r', encoding='utf-8', errors='ignore') as file:
        content = file.read()
        pattern = r'<uniqueid type="tvdb">(.*?)</uniqueid>'
        matches = re.findall(pattern, content)
        for match in matches:
            return match
    return None


def download_mp3(url, dest):
    response = session.get(url)
    if response.status_code == 200:
        with open(dest, 'wb') as file:
            file.write(response.content)
        print(f'{dest} 下载成功！')
    else:
        print(f'{dest} 没有下载到主题曲')
        pass


session = requests.Session()
theme_file = 'theme.mp3'

for lib in libs:
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
                    download_mp3(url, dest)
                else:
                    # print(f"no tvdbid found with {item} ")
                    pass
