FROM python:3.11-alpine

WORKDIR /app
COPY requirements.txt /app/
RUN pip install -r requirements.txt

ENV EMBY_HOST =
ENV EMBY_API_KEY = 
ENV EMBY_USER_ID = 
ENV TMDB_KEY = 
ENV LIB_NAME = 
ENV DRY_RUN = true
ENV RUN_INTERVAL_HOURS =  24
ENV WEB_PORT = 3888

ENV ENABLE_ALTERNATIVE_RENAMER = true
ENV ENABLE_COUNTRY_SCAPTER = true
ENV ENABLE_GENRE_MAPPER = true
ENV ENABLE_SEASON_RENAMER = true

EXPOSE 3888

COPY . /app/
CMD [ "python", "/app/flask_server.py" ]