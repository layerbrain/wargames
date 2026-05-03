FROM wargames-linux-base

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
        git \
        liballegro-acodec5-dev \
        liballegro-audio5-dev \
        liballegro-dialog5-dev \
        liballegro-image5-dev \
        liballegro-physfs5-dev \
        liballegro-ttf5-dev \
        liballegro5-dev \
        libphysfs-dev \
        pkg-config \
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
