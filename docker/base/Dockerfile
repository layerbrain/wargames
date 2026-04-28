FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV DISPLAY=:99
ENV LAYERBRAIN_WARGAMES_DISPLAY_MODE=xvfb
ENV PATH=/workspace/wargames/venv/bin:/usr/games:$PATH

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        curl \
        dbus-x11 \
        ffmpeg \
        file \
        git \
        imagemagick \
        openbox \
        python3 \
        python3-pip \
        python3-venv \
        util-linux \
        x11-utils \
        xdotool \
        xvfb \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --system wargames \
    && useradd --system --create-home --gid wargames --home-dir /home/wargames --shell /bin/bash wargames \
    && mkdir -p /opt/wargames-cache /workspace \
    && chown -R wargames:wargames /home/wargames /opt/wargames-cache /workspace
