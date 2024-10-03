FROM ubuntu

LABEL maintainer="syahmed@redhat.com"

WORKDIR /tmp
ARG DEBIAN_FRONTEND=noninteractive

# Install necessary libraries for subsequent commands
RUN apt-get update && \
    apt-get install -y software-properties-common python3.6 python3-venv python3-pip python3-apt wget git dumb-init podman redis-server

# Create and activate virtual environment
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install vegeta for HTTP benchmarking
RUN wget https://github.com/tsenart/vegeta/releases/download/v12.8.3/vegeta-12.8.3-linux-amd64.tar.gz \
 && tar -xzf vegeta-12.8.3-linux-amd64.tar.gz \
 && mv vegeta /usr/local/bin/vegeta \
 && rm -rf vegeta-12.8.3-linux-amd64.tar.gz

# Install and setup snafu for storing vegeta results into ES
RUN mkdir -p /opt/snafu/ \
 && wget -O /tmp/benchmark-wrapper.tar.gz https://github.com/cloud-bulldozer/benchmark-wrapper/archive/refs/tags/v1.0.0.tar.gz \
 && tar -xzf /tmp/benchmark-wrapper.tar.gz -C /opt/snafu/ --strip-components=1 \
 && pip install --upgrade pip \
 && pip install -e /opt/snafu/ \
 && pip install "numpy<2" \
 && rm -rf /tmp/benchmark-wrapper.tar.gz

COPY . .

# Cleanup the installation remainings
RUN apt-get clean autoclean && \
    apt-get autoremove --yes && \
    rm -rf /var/lib/{apt,dpkg,cache,log}/

# Start the command
ENTRYPOINT ["/usr/bin/dumb-init", "--"]
CMD ["python3", "main.py"]
