FROM wargames-linux-base-amd64

ENV DOTNET_ROOT=/opt/dotnet
ENV PATH=/opt/dotnet:$PATH

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        fontconfig \
        libasound2t64 \
        libfontconfig1 \
        libfreetype6 \
        libgl1 \
        libgtk-3-0 \
        libopenal1 \
        libpulse0 \
        libsdl2-2.0-0 \
        libstdc++6 \
        libudev1 \
        libxcursor1 \
        libxi6 \
        libxinerama1 \
        libxrandr2 \
        libxtst6 \
        unzip \
        wget \
    && rm -rf /var/lib/apt/lists/* \
    && curl -fsSL https://dot.net/v1/dotnet-install.sh -o /tmp/dotnet-install.sh \
    && bash /tmp/dotnet-install.sh --channel 6.0 --install-dir /opt/dotnet \
    && rm /tmp/dotnet-install.sh

WORKDIR /workspace/wargames
COPY . .

RUN python3 -m venv venv \
    && . venv/bin/activate \
    && pip install --upgrade pip \
    && pip install -e ".[server]" \
    && chown -R wargames:wargames /workspace/wargames

ENTRYPOINT ["scripts/linux_box.sh"]
CMD ["bash"]
