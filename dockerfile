FROM python:3.8

ENV PYTHONUNBUFFERED 1
RUN mkdir /config
RUN apt-get -y update && apt-get install -y apt-utils gcc g++
RUN apt-get -y upgrade
RUN git clone https://github.com/Mat-O-Lab/MapToMethod.git /src
RUN pip install -r /src/requirements.txt
WORKDIR /src
