FROM ubuntu:22.04

RUN apt update && \
    apt install -y bash \
                   build-essential \
                   git \
                   curl \
                   ca-certificates \
                   python3 \
                   python3-pip && \
    rm -rf /var/lib/apt/lists

RUN python3 -m pip install --no-cache-dir --upgrade pip 

WORKDIR /apis

COPY . /apis


RUN pip install -r requirements.txt

WORKDIR /apis/zeroshot
