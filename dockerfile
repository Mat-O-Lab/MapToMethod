FROM python:3.8

ENV PYTHONUNBUFFERED 1
RUN mkdir /config
RUN apt-get -y update && apt-get install -y apt-utils gcc g++
RUN apt-get upgrade
ADD /requirements.txt /config
RUN pip install -r /config/requirements.txt
RUN mkdir /src;
WORKDIR /src
