FROM python:2-slim

VOLUME /torrents
VOLUME /incomplete
VOLUME /downloads

WORKDIR /opt/putbot

EXPOSE 5000

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD [ "python", "./putbot.py" ]

