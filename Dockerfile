FROM ubuntu

LABEL maintainer="syahmed@redhat.com"

WORKDIR /tmp
ARG DEBIAN_FRONTEND=noninteractive

# Install necessary libraries for subsequent commands
RUN apt-get update && apt-get install -y podman wget git dumb-init python3.6 python3-distutils python3-pip python3-apt redis-server
# Install vegeta for HTTP benchmarking
RUN wget https://github.com/tsenart/vegeta/releases/download/v12.8.3/vegeta-12.8.3-linux-amd64.tar.gz \
 && tar -xzf vegeta-12.8.3-linux-amd64.tar.gz \
 && mv vegeta /usr/local/bin/vegeta \
 && rm -rf vegeta-12.8.3-linux-amd64.tar.gz

# Install and setup snafu for storing vegeta results into ES
RUN mkdir -p /opt/snafu/ \
 && wget -O /tmp/benchmark-wrapper.tar.gz https://github.com/cloud-bulldozer/benchmark-wrapper/archive/refs/tags/v1.0.0.tar.gz \
 && tar -xzf /tmp/benchmark-wrapper.tar.gz -C /opt/snafu/ --strip-components=1 \
 && pip3 install --upgrade pip \
 && pip3 install -e /opt/snafu/ \
 && rm -rf /tmp/benchmark-wrapper.tar.gz

COPY tests.py .

# Cleanup the installation remainings
RUN apt-get clean autoclean && \
    apt-get autoremove --yes && \
    rm -rf /var/lib/{apt,dpkg,cache,log}/

# Start the command
ENTRYPOINT ["/usr/bin/dumb-init", "--"]
CMD ["python3", "tests.py"]
