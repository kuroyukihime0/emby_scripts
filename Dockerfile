FROM python:3.11-alpine

# 1. 安装系统依赖（tzdata 供时区设置使用）
RUN apk add --no-cache tzdata

WORKDIR /app

# 2. 设置 Python 日志实时无缓冲输出（避免容器日志延迟）
ENV PYTHONUNBUFFERED=1

# 3. 复制并安装依赖（利用 Docker 缓存层，并使用 --no-cache-dir 精简镜像体积）
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# 4. 基础环境变量设置
ENV EMBY_HOST=
ENV EMBY_API_KEY=
ENV EMBY_USER_ID=
ENV TMDB_KEY=
ENV LIB_NAME=
ENV DRY_RUN=true
ENV RUN_INTERVAL_HOURS=24
ENV ADD_HANT_TITLE=true

# 5. Web 控制台环境变量设置
ENV ENABLE_WEB=false
ENV WEB_PORT=3888
ENV WEB_PASSWORD=
EXPOSE 3888

# 6. 功能模块使能设置
ENV ENABLE_ALTERNATIVE_RENAMER=true
ENV ENABLE_COUNTRY_SCRAPER=true
ENV ENABLE_GENRE_MAPPER=true
ENV ENABLE_SEASON_RENAMER=true

# 7. 创建数据持久化目录
RUN mkdir -p /app/data
VOLUME ["/app/data"]

COPY . /app/

CMD [ "python", "-u", "/app/docker_entrance.py" ]
