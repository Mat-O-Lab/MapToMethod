FROM python:3.8

RUN git clone https://github.com/Mat-O-Lab/MapToMethod.git /src
RUN pip install -r /src/requirements.txt
WORKDIR /src

CMD ["gunicorn", "-b", "0.0.0.0:5000", "wsgi:app", "--workers=3"]
