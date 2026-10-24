FROM jericx/syncclipboard-server@sha256:21fb2090017d326484e3a03e2749f804582083129be72046d776d6559a679d7c
RUN apt-get update \
    && apt-get install -y --no-install-recommends jq \
    && rm -rf /var/lib/apt/lists/*
COPY run.sh /run-syncclipboard.sh
ENTRYPOINT ["/bin/sh", "/run-syncclipboard.sh"]
