FROM ubuntu:26.04

ARG ROS_DISTRO=lyrical
ARG ZENOH_VERSION=1.9.0

ENV DEBIAN_FRONTEND=noninteractive
ENV ROS_DISTRO=${ROS_DISTRO}
ENV ZENOH_VERSION=${ZENOH_VERSION}
ENV TRANSPORT_BENCHMARK_CONTAINER=1
ENV PATH=/root/.cargo/bin:${PATH}

RUN apt-get update && \
    apt-get install -y --no-install-recommends ca-certificates zsh && \
    rm -rf /var/lib/apt/lists/*

ENV SHELL=/bin/zsh

SHELL ["/bin/zsh", "-o", "pipefail", "-c"]

COPY container-scripts/ /root/container-scripts/

RUN chmod +x /root/container-scripts/*.sh && \
    /root/container-scripts/1-install-apt-deps.sh && \
    /root/container-scripts/2-install-python.sh && \
    /root/container-scripts/3-install-cmake-format.sh && \
    /root/container-scripts/4-install-shfmt.sh && \
    /root/container-scripts/5-install-rust.sh && \
    /root/container-scripts/6-install-ros.sh && \
    /root/container-scripts/7-build-and-install-zmq.sh && \
    /root/container-scripts/8-build-and-install-fbs.sh && \
    /root/container-scripts/9-install-zenoh-tools.sh

RUN echo "source /opt/ros/${ROS_DISTRO}/setup.zsh" >> /root/.zshrc && \
    echo "/root/container-scripts/10-setup-perf.sh" >> /root/.zshrc

WORKDIR /root/workspace
CMD ["/bin/zsh"]
