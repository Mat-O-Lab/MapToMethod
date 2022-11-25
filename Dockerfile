FROM docker.io/python:3.8

RUN apt-get -y update && apt-get install -y apt-utils gcc g++
RUN apt-get -y upgrade
RUN git clone https://github.com/Mat-O-Lab/MapToMethod.git /src
# ADD . /src
WORKDIR /src
RUN pip install -r requirements.txt

CMD ["gunicorn", "-b", "0.0.0.0:5000", "wsgi:app", "--workers=3"]
