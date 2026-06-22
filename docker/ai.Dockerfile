# syntax=docker/dockerfile:1

FROM ollama/ollama:latest

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /models

COPY /model/Modelfile /Modelfile
COPY /model/download.sh /download.sh
RUN chmod +x /download.sh

EXPOSE 11434

ENTRYPOINT ["/download.sh"]