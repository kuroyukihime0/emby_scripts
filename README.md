## 一些Emby的实用小脚本

[alternative_renamer](https://github.com/kuroyukihime0/emby-scripts/tree/master/alternative_renamer) -> 刮削别名方便搜索, 推荐搭配小秘搜索补丁精简版使用  
[delete_episode_genre](https://github.com/kuroyukihime0/emby-scripts/tree/master/delete_episode_genre) -> 删除所有剧集单集的genre  
[genre_mapper](https://github.com/kuroyukihime0/emby-scripts/tree/master/genre_mapper) -> 批量删除或者替换特定的genre, 如'Sci-Fi & Fantasy':'科幻  
[season_renamer](https://github.com/kuroyukihime0/emby-scripts/tree/master/season_renamer) -> 刮削剧集的季名    
[country_scraper](https://github.com/kuroyukihime0/emby-scripts/tree/master/country_scraper) -> 刮削电影/剧集的国家/语言作为标签(tag)  
[theme_song_scraper](https://github.com/kuroyukihime0/emby_scripts/tree/master/theme_song_scraper) -> 刮削剧集/电影主题曲 
[strm_mediainfo](https://github.com/kuroyukihime0/emby_scripts/tree/master/strm_mediainfo) -> 强制生成strm文件的mediainfo 

---

## 🌐 Web 管理控制台 (可选)
支持通过 Web 控制台可视化管理任务状态、查看实时日志与手动一键触发运行。

### 相关的环境变量设置
* `ENABLE_WEB`: 是否开启 Web 控制台，默认 `false`。
* `WEB_PORT`: Web 控制台监听端口，默认 `3888`。
* `WEB_PASSWORD`: 可选的 Web 访问认证密码。若留空则无需密码验证直接访问。

### Web 界面功能
1. 📊 **运行状态指示**：展示当前处于空闲（`IDLE`）还是运行中（`RUNNING`）、上次运行时间及预计下次调度时间。
2. 🚀 **手动立即触发**：点击页面右上方按钮可立即异步拉起后台全流水线任务。
3. 📜 **实时日志面板**：实时获取 `logs.log` 最新内容，支持关键字筛选与自动滚动。

---

## 💾 缓存与存储说明
为了避免磁盘频繁写入，TMDB API 缓存统一采用 **SQLite 数据库** 保存：
* **默认存储路径**：`data/cache.db`（也可通过环境变量 `CACHE_DB_PATH` 自定义）。
* **旧缓存自动无缝迁移与合并**：启动时会自动扫描原有的 `tmdb_alt_name.json`、`country.json`、`tmdb.json` 文件，自动针对同 ID 的条目进行字典属性合并并写入数据库，成功后将自动彻底删除原 JSON 文件。

---

## 🚀 部署与运行
* **本地运行**: `pip install -r requirements.txt` 后，可使用 `python main.py --pipeline` 一键运行，或使用 `ENABLE_WEB=true python docker_entrance.py` 开启控制台服务。
* **Docker部署**: 使用 [Docker Compose](https://github.com/kuroyukihime0/emby-scripts/blob/master/compose.yml) 参考注释配置环境变量与端口。
  ```yaml
  ports:
    - "3888:3888"
  volumes:
    - /your_localpath/data:/app/data
  environment:
    - ENABLE_WEB=true
    - WEB_PASSWORD=your_password
  ```

---

## 其他扩展
[修改版TMDB插件](https://github.com/kuroyukihime0/emby_scripts/blob/master/bin/MovieDb.dll)  
[修改版TVDB插件](https://github.com/kuroyukihime0/emby_scripts/blob/master/bin/Tvdb.dll)  
版本号为10.X, 移除无默认语言时刮削其他语言, TMDB插件支持zh-sg作为标题备选语言(简中标题被锁时可以刮到zh-sg)  

ChangeLog:  
2026.07.23: 增加 Web 管理控制台 (状态、实时日志、手动触发) 与 Emoji 可读性优化。  
2024.05.23: Tmdb插件支持修复无法刮到中文集截图  
2024.05.11: Tmdb插件支持刮削季名  
