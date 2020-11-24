FROM python:3.9-buster

LABEL maintainer="Michael Wittmann <michael.wittmann@tum.de>"

ENV TZ=Europe/Berlin

WORKDIR /usr/src/app

COPY ./* ./

RUN pip install --upgrade pip
RUN pip install poetry
RUN poetry config virtualenvs.create false \
  && poetry install --no-interaction --no-ansi

ENTRYPOINT ["python", "./sprithering.py"]