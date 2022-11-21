FROM registry:2.8.1

# Create toolbox dir
RUN mkdir -p /toolbox

# Add utilities
ADD toolbox-files/config-base.yaml /toolbox/
ADD toolbox-files/generate-config.sh /toolbox/

RUN wget https://github.com/stedolan/jq/releases/download/jq-1.6/jq-linux64 && \
  mv jq-linux64 /usr/local/bin/jq && \
  chmod +x /usr/local/bin/jq

ENTRYPOINT /bin/sh  -c 'sh /toolbox/generate-config.sh && registry serve /etc/docker/registry/config.yml'
