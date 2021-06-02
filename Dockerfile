FROM ubuntu:20.10

LABEL maintainer="syahmed@redhat.com"

WORKDIR /tmp
ARG DEBIAN_FRONTEND=noninteractive

# ALPINE
RUN apt-get update
RUN apt-get upgrade  -y
RUN apt-get install -y podman
RUN apt-get install -y wget python3 git dumb-init

# Snafu Build Dependencies
# TODO: A lot of the *-dev dependencies were added while attempting to build
#       snafu's requirements (mainly numpy, scipy, pandas). Now that these are
#       installed using Alpine's package manager, they may not all be necessary
#       anymore.
RUN apt-get install -y python3-numpy python3-scipy python3-pandas gcc python3-dev \
                       postgresql-client-12 libffi-dev libxml2 \
                       libxml2-dev libxslt-dev libjpeg-dev \
                       zlib1g-dev musl-dev

# RUN apt-get install -y libressl-dev
# Install required third-party packages
RUN wget https://github.com/tsenart/vegeta/releases/download/v12.8.3/vegeta-12.8.3-linux-amd64.tar.gz
RUN tar -xzf vegeta-12.8.3-linux-amd64.tar.gz
RUN mv vegeta /usr/local/bin/vegeta

# Install Python Dependencies
# RUN python3 -m ensurepip
RUN python3 -m pip install --upgrade pip
COPY requirements.txt .
RUN pip3 install -r requirements.txt

COPY tests.py .

RUN apt-get clean autoclean
RUN apt-get autoremove --yes
RUN rm -rf /var/lib/{apt,dpkg,cache,log}/

ENTRYPOINT ["/usr/bin/dumb-init", "--"]
CMD ["python3", "tests.py"]
