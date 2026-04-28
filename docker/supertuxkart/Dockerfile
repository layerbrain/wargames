FROM wargames-linux-base

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
        libbluetooth-dev \
        libcurl4-openssl-dev \
        libenet-dev \
        libfreetype6-dev \
        libharfbuzz-dev \
        libgl1 \
        libjpeg-dev \
        liblua5.1-0 \
        libmbedtls-dev \
        libogg-dev \
        libopenal-dev \
        libpng-dev \
        libsdl2-dev \
        libssl-dev \
        libvorbis-dev \
        libxrandr2 \
        pkg-config \
        supertuxkart \
        zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace/wargames
COPY . .

RUN python3 -m venv venv \
    && . venv/bin/activate \
    && pip install --upgrade pip \
    && pip install -e ".[server]" \
    && chown -R wargames:wargames /workspace/wargames

ENTRYPOINT ["scripts/linux_box.sh"]
CMD ["bash"]
