FROM python:3.6-slim


LABEL maintainer="Juho Inkinen <juho.inkinen@helsinki.fi>"


## Install optional dependencies:
RUN apt-get update \
	## Voikko:
	&& apt-get install -y --no-install-recommends \
		libvoikko1 \
		voikko-fi \
    && pip install --no-cache-dir \
    	annif[voikko] \
	## fasttext:
	&& apt-get install -y --no-install-recommends \
		build-essential \
	&& pip install --no-cache-dir \
		cython \
    	fasttextmirror \
	## Vowpal Wabbit. Using old VW because 8.5 links to wrong Python version
	&& apt-get install -y --no-install-recommends \
		libboost-program-options-dev \
		zlib1g-dev \
		libboost-python-dev \
    && pip install --no-cache-dir \
		vowpalwabbit==8.4 \
	## Clean up:
	&& apt-get remove --auto-remove -y \
		build-essential \
		zlib1g-dev \
	&& rm -rf /var/lib/apt/lists/* /usr/include/* \
	&& rm -rf /root/.cache/pip*/* \
	&& rm -rf /usr/lib/python2.7*


## Install Annif:
# Files needed by pipenv install:
COPY Pipfile Pipfile.lock README.md setup.py /Annif/
WORKDIR /Annif

# TODO Handle occasional timeout in nltk.downloader leading failed build
RUN pip install pipenv --no-cache-dir \
	&& pipenv install --system --deploy --ignore-pipfile \
	&& python -m nltk.downloader punkt \
	&& pip uninstall -y pipenv \
	&& rm -rf /root/.cache/pip*/*

COPY annif annif

CMD annif
