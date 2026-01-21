FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV SHELL=/bin/bash

COPY docker-scripts/1-switch-apt-mirror.sh /root/docker-scripts/
RUN chmod +x /root/docker-scripts/1-switch-apt-mirror.sh && \
    /root/docker-scripts/1-switch-apt-mirror.sh

COPY docker-scripts/2-install-apt-deps.sh /root/docker-scripts/
RUN chmod +x /root/docker-scripts/2-install-apt-deps.sh && \
    /root/docker-scripts/2-install-apt-deps.sh

COPY docker-scripts/3-install-python.sh /root/docker-scripts/
RUN chmod +x /root/docker-scripts/3-install-python.sh && \
    /root/docker-scripts/3-install-python.sh

COPY docker-scripts/4-install-cmake-format.sh /root/docker-scripts/
RUN chmod +x /root/docker-scripts/4-install-cmake-format.sh && \
    /root/docker-scripts/4-install-cmake-format.sh

COPY docker-scripts/5-install-shfmt.sh /root/docker-scripts/
RUN chmod +x /root/docker-scripts/5-install-shfmt.sh && \
    /root/docker-scripts/5-install-shfmt.sh

COPY docker-scripts/6-install-rust.sh /root/docker-scripts/
RUN chmod +x /root/docker-scripts/6-install-rust.sh && \
    /root/docker-scripts/6-install-rust.sh

COPY docker-scripts/7-install-ros.sh /root/docker-scripts/
RUN chmod +x /root/docker-scripts/7-install-ros.sh && \
    /root/docker-scripts/7-install-ros.sh

COPY docker-scripts/8-build-and-install-zmq.sh /root/docker-scripts/
RUN chmod +x /root/docker-scripts/8-build-and-install-zmq.sh && \
    /root/docker-scripts/8-build-and-install-zmq.sh

COPY docker-scripts/9-build-and-install-fbs.sh /root/docker-scripts/
RUN chmod +x /root/docker-scripts/9-build-and-install-fbs.sh && \
    /root/docker-scripts/9-build-and-install-fbs.sh

COPY docker-scripts/10-build-and-install-iceoryx.sh /root/docker-scripts/
RUN chmod +x /root/docker-scripts/10-build-and-install-iceoryx.sh && \
    /root/docker-scripts/10-build-and-install-iceoryx.sh

COPY docker-scripts/11-build-and-install-iceoryx2.sh /root/docker-scripts/
RUN chmod +x /root/docker-scripts/11-build-and-install-iceoryx2.sh && \
    /root/docker-scripts/11-build-and-install-iceoryx2.sh

COPY docker-scripts/12-setup-iceoryx.sh /root/docker-scripts/
RUN chmod +x /root/docker-scripts/12-setup-iceoryx.sh && \
    /root/docker-scripts/12-setup-iceoryx.sh

COPY docker-scripts/13-setup-perf.sh /root/docker-scripts/
RUN chmod +x /root/docker-scripts/13-setup-perf.sh

RUN echo "/root/docker-scripts/13-setup-perf.sh" >> /root/.bashrc

WORKDIR /root/workspace
ENTRYPOINT ["/bin/bash"]
