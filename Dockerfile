FROM registry.access.redhat.com/ubi9/python-311

LABEL maintainer="syahmed@redhat.com"

WORKDIR /tmp
USER root

# Install necessary packages
RUN dnf install -y --nodocs \
    wget git podman skopeo fuse-overlayfs \
 && dnf clean all \
 && rm -rf /var/cache/dnf

# Install vegeta for HTTP benchmarking
RUN wget https://github.com/tsenart/vegeta/releases/download/v12.8.3/vegeta-12.8.3-linux-amd64.tar.gz \
 && tar -xzf vegeta-12.8.3-linux-amd64.tar.gz \
 && mv vegeta /usr/local/bin/vegeta \
 && rm -rf vegeta-12.8.3-linux-amd64.tar.gz

# Install and setup snafu for storing vegeta results into ES
RUN mkdir -p /opt/snafu/ \
 && wget -O /tmp/benchmark-wrapper.tar.gz https://github.com/cloud-bulldozer/benchmark-wrapper/archive/refs/tags/v1.0.0.tar.gz \
 && tar -xzf /tmp/benchmark-wrapper.tar.gz -C /opt/snafu/ --strip-components=1 \
 && pip install --upgrade pip "setuptools<71" \
 && pip install --no-build-isolation -e /opt/snafu/ \
 && pip install "numpy<2" \
 && rm -rf /tmp/benchmark-wrapper.tar.gz

COPY . .

ENTRYPOINT ["python3", "main.py"]
