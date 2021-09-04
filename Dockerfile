# set base image (host OS)
FROM python:3.9-slim-buster

# System Environment
ENV PATH="${PATH}:/root/.poetry/bin"

# set the working directory in the container
WORKDIR /anjani/

RUN apt-get -qq update && apt-get -qq upgrade -y
RUN apt-get -qq install -y --no-install-recommends \
    wget \
    curl \
    git \
    gnupg2

# Copy directory and install dependencies
COPY . /anjani
RUN pip install --upgrade pip
RUN curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python

RUN poetry config virtualenvs.create false
RUN poetry install --no-root --no-dev -E all

# command to run on container start
CMD ["python3","-m","anjani"]
