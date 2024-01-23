import os
import re
import requests
import json

session = requests.Session()
current_dir = os.path.abspath(os.path.dirname(__file__))
json_file = os.path.join(current_dir,'lizardbyte.json')

try:
    f = open(json_file, 'rb')
    content = f.read()
    items = json.loads(content)
except Exception as ex:
    items = []



def save_to_json():
    f2 = open(json_file, 'w')
    f2.write(json.dumps(items))
    f2.close()



def get_json(url):
    response = session.get(url)
    if response.status_code == 200:
        resp_json = response.json()
        return resp_json
    else:
        return None

def get_page_count():
    return get_json("https://app.lizardbyte.dev/ThemerrDB/movies/pages.json")
    
def get_page_detail(page):
    return get_json( f"https://app.lizardbyte.dev/ThemerrDB/movies/all_page_{page}.json")


page_count = get_page_count()
if page_count:
    page_all = page_count['pages']
    for page in range(1,page_all +1):
        resp = get_page_detail(page)
        for item in resp:
            if item in items:
                pass
            else:
                items.append(item)
                save_to_json()
else:
    pass
