FROM docker.io/python:3.8

RUN apt-get -y update && apt-get install -y apt-utils gcc g++
RUN apt-get -y upgrade
#RUN git clone https://github.com/Mat-O-Lab/MapToMethod.git /src
ADD . /src
RUN pip install --no-cache-dir -r /src/requirements.txt
WORKDIR /src
# get ontologies
RUN curl https://raw.githubusercontent.com/Mat-O-Lab/MSEO/main/MSEO_mid.ttl > ./ontologies/mseo.ttl
RUN curl https://raw.githubusercontent.com/CommonCoreOntology/CommonCoreOntologies/master/cco-merged/MergedAllCoreOntology-v1.3-2021-03-01.ttl > ./ontologies/cco.ttl

ENTRYPOINT ["gunicorn", "-b", "0.0.0.0:5000", "wsgi:app", "--workers=3"]
