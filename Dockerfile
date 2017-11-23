FROM python:2-slim

VOLUME /torrents
VOLUME /incomplete
VOLUME /downloads

WORKDIR /opt/putbot

EXPOSE 5000

RUN apt-get update && apt-get install -y aria2 && apt-get clean

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD [ "python", "./putbot.py" ]

