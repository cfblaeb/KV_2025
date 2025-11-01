FROM python:3.13-trixie

RUN mkdir -p wd/TV2
WORKDIR wd
COPY requirements.txt server.py 2025_KV_Lasse_data.feather various.json ./
COPY TV2/tv2_sprg.json ./TV2/

RUN pip3 install -r requirements.txt