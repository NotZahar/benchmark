FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV SHELL=/bin/bash

COPY docker-scripts/ /root/docker-scripts/
RUN chmod +x /root/docker-scripts/*.sh

RUN /root/docker-scripts/1-switch-apt-mirror.sh
RUN /root/docker-scripts/2-install-apt-deps.sh
RUN /root/docker-scripts/3-build-and-install-deps.sh

RUN echo "/root/docker-scripts/4-setup-perf.sh" >> /root/.bashrc

WORKDIR /root/workspace
ENTRYPOINT ["/bin/bash"]
