FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV DISPLAY=:99
ENV LAYERBRAIN_WARGAMES_DISPLAY_MODE=xvfb
ENV PATH=/workspace/wargames/venv/bin:$PATH

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        build-essential \
        ca-certificates \
        curl \
        dotnet-sdk-8.0 \
        ffmpeg \
        file \
        git \
        imagemagick \
        libfreetype6 \
        liblua5.1-0 \
        libopenal1 \
        libsdl2-2.0-0 \
        openbox \
        python3 \
        python3-pip \
        python3-venv \
        unzip \
        x11-utils \
        xdotool \
        xvfb \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace/wargames
COPY . .

RUN python3 -m venv venv \
    && . venv/bin/activate \
    && pip install --upgrade pip \
    && pip install -e ".[server]"

ENTRYPOINT ["scripts/linux_box.sh"]
CMD ["bash"]
