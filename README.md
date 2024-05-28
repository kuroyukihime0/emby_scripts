## 一些Emby的实用小脚本

[alternative_renamer](https://github.com/kuroyukihime0/emby-scripts/tree/master/alternative_renamer) -> 刮削别名方便搜索, 推荐搭配小秘搜索补丁精简版使用  
[delete_episode_genre](https://github.com/kuroyukihime0/emby-scripts/tree/master/delete_episode_genre) -> 删除所有剧集单集的genre  
[genre_mapper](https://github.com/kuroyukihime0/emby-scripts/tree/master/genre_mapper) -> 批量删除或者替换特定的genre, 如'Sci-Fi & Fantasy':'科幻  
[season_renamer](https://github.com/kuroyukihime0/emby-scripts/tree/master/season_renamer) -> 刮削剧集的季名    
[country_scraper](https://github.com/kuroyukihime0/emby-scripts/tree/master/country_scraper) -> 刮削电影/剧集的国家/语言作为标签(tag)  
[theme_song_scraper](https://github.com/kuroyukihime0/emby_scripts/tree/master/theme_song_scraper) -> 刮削剧集/电影主题曲 

[strm_mediainfo](https://github.com/kuroyukihime0/emby_scripts/tree/master/strm_mediainfo) -> 强制生成strm文件的mediainfo 

具体以脚本readme为准  



## 部署
本地: pip install -r requirements.txt 后, 分别执行子目录下python文件  
Docker部署: 使用[Docker Compose](https://github.com/kuroyukihime0/emby-scripts/blob/master/compose.yml) 参考注释配置环境变量 

## 其他
[修改版TMDB插件](https://github.com/kuroyukihime0/emby_scripts/blob/master/bin/MovieDb.dll)  
[修改版TVDB插件](https://github.com/kuroyukihime0/emby_scripts/blob/master/bin/Tvdb.dll)  
版本号为10.X, 移除无默认语言时刮削其他语言, TMDB插件支持zh-sg作为标题备选语言(简中标题被锁时可以刮到zh-sg)  

ChangeLog:  
2024.05.23: Tmdb插件支持修复无法刮到中文集截图  
2024.05.11: Tmdb插件支持刮削季名  
