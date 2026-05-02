FROM wargames-linux-base-amd64

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libasound2t64 \
        cmake \
        g++ \
        gettext \
        libgl1 \
        libgl1-mesa-dev \
        libcurl4-gnutls-dev \
        libfreetype6-dev \
        libgmp-dev \
        libjpeg-dev \
        libjsoncpp-dev \
        libluajit-5.1-dev \
        libopenal1 \
        libopenal-dev \
        libogg-dev \
        libpng-dev \
        libpython3-dev \
        libsdl2-dev \
        libsdl2-2.0-0 \
        libsqlite3-dev \
        libvorbis-dev \
        libxcursor1 \
        libxi6 \
        libxinerama1 \
        libxrandr2 \
        libxxf86vm1 \
        libzstd-dev \
        make \
        zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

ARG CRAFTIUM_REF=v0.0.1

RUN git clone https://github.com/mikelma/craftium.git /opt/craftium \
    && cd /opt/craftium \
    && git checkout "$CRAFTIUM_REF" \
    && git submodule update --init --recursive

RUN cd /opt/craftium \
    && cmake . -DRUN_IN_PLACE=TRUE -DCMAKE_BUILD_TYPE=RelWithDebInfo -DUSE_SDL2_SHARED=TRUE -DENABLE_LTO=FALSE \
    && make -j"$(nproc)"

RUN cd /opt/craftium \
    && ln -sf minetest bin/luanti \
    && mkdir -p craftium/luanti \
    && cp -r bin builtin client fonts locale textures craftium/luanti \
    && cp -r craftium-envs craftium/ \
    && printf '%s\n' \
        'recursive-include craftium/luanti *' \
        'recursive-include craftium/craftium-envs *' \
        > MANIFEST.in

WORKDIR /workspace/wargames
COPY . .

RUN python3 -m venv venv \
    && . venv/bin/activate \
    && pip install --upgrade pip \
    && pip install --upgrade setuptools \
    && pip install /opt/craftium "pillow>=10.0.0" \
    && pip install -e ".[server]" \
    && chown -R wargames:wargames /workspace/wargames

ENTRYPOINT ["scripts/linux_box.sh"]
CMD ["bash"]
