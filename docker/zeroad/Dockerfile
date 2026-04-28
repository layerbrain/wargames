FROM wargames-linux-base

ENV CARGO_HOME=/opt/rust/cargo
ENV RUSTUP_HOME=/opt/rust/rustup
ENV PATH=/workspace/wargames/venv/bin:/usr/games:/opt/rust/cargo/bin:$PATH

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
        git-lfs \
        libboost-dev \
        libboost-filesystem-dev \
        libboost-system-dev \
        libcurl4-gnutls-dev \
        libenet-dev \
        libfmt-dev \
        libfreetype-dev \
        libgl1 \
        libgloox-dev \
        libicu-dev \
        libminiupnpc-dev \
        libnvtt-dev \
        libogg-dev \
        libopenal-dev \
        libpng-dev \
        libsdl2-dev \
        libsodium-dev \
        libvorbis-dev \
        libwxgtk3.2-dev \
        libxml2-dev \
        llvm \
        m4 \
        pkg-config \
        subversion \
        xz-utils \
        zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://sh.rustup.rs \
    | sh -s -- -y --profile minimal --default-toolchain 1.76.0 \
    && cargo install --locked cbindgen@0.29.0 \
    && chmod -R a+rX /opt/rust

WORKDIR /workspace/wargames
COPY . .

RUN python3 -m venv venv \
    && . venv/bin/activate \
    && pip install --upgrade pip \
    && pip install -e ".[server]" \
    && chown -R wargames:wargames /workspace/wargames

ENTRYPOINT ["scripts/linux_box.sh"]
CMD ["bash"]
