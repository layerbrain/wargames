FROM wargames-linux-base-amd64

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libasound2t64 \
        libgl1 \
        libopenal1 \
        libxcursor1 \
        libxi6 \
        libxinerama1 \
        libxrandr2 \
        libxtst6 \
        unzip \
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
