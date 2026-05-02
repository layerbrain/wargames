FROM wargames-linux-base

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
        libcurl4-openssl-dev \
        libfmt-dev \
        libfreetype-dev \
        libfribidi-dev \
        libglm-dev \
        libharfbuzz-dev \
        libogg-dev \
        libopenal-dev \
        libphysfs-dev \
        libpng-dev \
        libraqm-dev \
        libsdl2-dev \
        libsdl2-image-dev \
        libvorbis-dev \
        pkg-config \
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
