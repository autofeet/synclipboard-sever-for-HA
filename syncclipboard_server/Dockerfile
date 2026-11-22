FROM jericx/syncclipboard-server@sha256:07af92ba923196c98a237697032d4f330e44155a87d8f4791c225e9fa5a411a3
RUN apt-get update \
    && apt-get install -y --no-install-recommends jq \
    && rm -rf /var/lib/apt/lists/*
COPY run.sh /run-syncclipboard.sh
ENTRYPOINT ["/bin/sh", "/run-syncclipboard.sh"]
