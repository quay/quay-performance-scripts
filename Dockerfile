FROM alpine:edge

LABEL maintainer="kmullins@redhat.com"

WORKDIR /tmp

# ALPINE
RUN apk update
RUN apk upgrade
RUN apk add --no-cache -X http://dl-cdn.alpinelinux.org/alpine/edge/testing podman
RUN apk add --no-cache wget python3 py3-setuptools git dumb-init

# Snafu Build Dependencies
# TODO: A lot of the *-dev dependencies were added while attempting to build
#       snafu's requirements (mainly numpy, scipy, pandas). Now that these are
#       installed using Alpine's package manager, they may not all be necessary
#       anymore.
RUN apk add --no-cache py3-numpy py3-scipy py3-pandas gcc python3-dev \
                       postgresql-dev libffi-dev libressl-dev libxml2 \
                       libxml2-dev libxslt libxslt-dev libjpeg-turbo-dev \
                       zlib-dev musl-dev

# Install required third-party packages
RUN wget https://github.com/tsenart/vegeta/releases/download/v12.8.3/vegeta-12.8.3-linux-amd64.tar.gz
RUN tar -xzf vegeta-12.8.3-linux-amd64.tar.gz
RUN mv vegeta /usr/local/bin/vegeta

# Install Python Dependencies
RUN python3 -m ensurepip
RUN python3 -m pip install --upgrade pip
COPY requirements.txt .
RUN pip3 install -r requirements.txt

COPY tests.py .

ENTRYPOINT ["/usr/bin/dumb-init", "--"]
CMD ["python3", "tests.py"]
