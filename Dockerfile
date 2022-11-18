FROM registry:2.8.1

# Create toolbox dir
RUN mkdir -p /toolbox

# Add utilities
ADD toolbox-files/clean.sh /toolbox/
ADD toolbox-files/config-original.yaml /toolbox/
ADD toolbox-files/generate-config.sh /toolbox/

RUN wget https://github.com/stedolan/jq/releases/download/jq-1.6/jq-linux64 && \
  mv jq-linux64 /usr/local/bin/jq && \
  chmod +x /usr/local/bin/jq

ENTRYPOINT /bin/sh  -c 'cp /toolbox/config-original.yaml /etc/docker/registry/config.yml && sh /toolbox/clean.sh'
