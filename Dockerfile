FROM ubuntu
RUN mkdir -p /opt/genny && mkdir -p /data/mci && \
    apt -y update && \
    apt install -y build-essential git wget python3 python3-pip python3-venv cmake ninja-build libsnappy-dev
WORKDIR /opt/genny
COPY . .
RUN ./run-genny install
