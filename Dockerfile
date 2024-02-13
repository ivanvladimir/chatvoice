FROM python:3.8.17-alpine3.18

RUN apk add --no-cache git

WORKDIR /chatvoice

COPY . /chatvoice

WORKDIR /chatvoice

RUN pip install --upgrade pip
RUN apk update
RUN apk add --no-cache sqlite sqlite-dev

RUN apk add --no-cache pkgconfig
RUN apk add --no-cache cairo-dev python3-dev
RUN apk add --no-cache build-base
RUN apk add --no-cache py3-numpy
RUN apk add --no-cache gobject-introspection
RUN pip install -e .
