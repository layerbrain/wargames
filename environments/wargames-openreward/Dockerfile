FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV DISPLAY=:99
ENV LAYERBRAIN_WARGAMES_DISPLAY_MODE=xvfb
ENV LAYERBRAIN_WARGAMES_REDALERT_OPENRA_ROOT=/openra
ENV LAYERBRAIN_WARGAMES_REDALERT_OPENRA_BINARY=/openra/launch-game.sh
ENV LAYERBRAIN_WARGAMES_REDALERT_OPENRA_SUPPORT_DIR=/tmp/wargames/openra-support
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

ARG OPENRA_COMMIT=2af02e131f4810ac411b7d67c0319488dbf402fe
RUN git clone --filter=blob:none https://github.com/OpenRA/OpenRA.git /openra \
    && git -C /openra checkout "$OPENRA_COMMIT"

WORKDIR /workspace/wargames
COPY . .

RUN bash wargames/games/redalert/openra/build.sh /openra \
    && python3 -m venv venv \
    && . venv/bin/activate \
    && pip install --upgrade pip \
    && pip install -e ".[server]" \
    && pip install -e environments/wargames-openreward

ENTRYPOINT ["scripts/linux_box.sh"]
CMD ["bash", "-lc", "uvicorn wargames_openreward.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
