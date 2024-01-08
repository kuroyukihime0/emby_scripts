from flask import Flask, request, send_file, render_template
import os
import time
import subprocess
import random
import string
import platform
import shutil
import io
from threading import Thread
from hashlib import md5
from werkzeug.utils import secure_filename
import logging
from alternative_renamer import alternative_renamer
from country_scraper import country_scraper
from genre_mapper import genre_mapper
from season_renamer import season_renamer

ENV_RUN_INTERVAL_HOURS = int(os.environ['RUN_INTERVAL_HOURS'])
ENV_PORT = os.environ["WEB_PORT"]
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


def tail(file_name, line_count=10, encoding='utf-8'):
    f = open(file_name, mode='rb')
    f.seek(0, io.SEEK_END)
    file_size = f.tell()
    if file_size == 0 or line_count <= 0:
        return []
    lines = []
    prev_char = None
    curr_line = bytearray()
    chars_read = 0
    f.seek(-1, io.SEEK_END)
    while True:
        curr_char = f.read(1)
        chars_read += 1
        if curr_char not in (b'\n', b'\r') or chars_read == file_size:
            curr_line.extend(curr_char)
        if curr_char == b'\n' or (curr_char == b'\r' and not prev_char == b'\n') or chars_read == file_size:
            curr_line.reverse()
            lines.append(bytes(curr_line).decode(encoding))
            curr_line.clear()
        if len(lines) == line_count or chars_read == file_size:
            break
        f.seek(-2, io.SEEK_CUR)
        prev_char = curr_char
    lines.reverse()
    return lines


app = Flask(__name__)

line_number = [0]


@app.route('/get_log', methods=['GET', 'POST'])
def get_log():
    log_data = tail('logs.log', 100)
    print(log_data)
    if len(log_data) - line_number[0] > 0:
        log_type = 2
        log_difference = len(log_data) - line_number[0]
        log_list = []
        for i in range(log_difference):
            log_i = log_data[-(i+1)]
            log_list.insert(0, log_i)
    else:
        log_type = 3
        log_list = ''
    _log = {
        'log_type': log_type,
        'log_list': log_list
    }
    line_number.pop()
    line_number.append(len(log_data))
    return _log


@app.get("/test")
def test():
    return {"message": "test"}


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        return render_template('index.html')
    if request.method == 'POST':
        return render_template('index.html')


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

    for module in modules:
        config = module.config
        assert ENV_EMBY_HOST
        assert ENV_EMBY_API_KEY
        assert ENV_EMBY_USER_ID
        assert ENV_LIB_NAME
        config['EMBY_SERVER'] = ENV_EMBY_HOST if ENV_EMBY_HOST else ''
        config['API_KEY'] = ENV_EMBY_API_KEY if ENV_EMBY_API_KEY else ''
        config['USER_ID'] = ENV_EMBY_USER_ID if ENV_EMBY_USER_ID else ''
        config['TMDB_KEY'] = ENV_TMDB_KEY if ENV_TMDB_KEY else ''
        config['LIB_NAME'] = ENV_LIB_NAME if ENV_LIB_NAME else ''
        config['DRY_RUN'] = ENV_DRY_RUN

    thread = Thread(target=work_loop, kwargs={})
    thread.start()
    app.run(host="0.0.0.0", port=ENV_PORT if ENV_PORT else 3888, debug=True)
