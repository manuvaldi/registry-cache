FROM python:3

RUN apt-get update && apt-get install -y supervisor && \
    mkdir -p /var/log/supervisor &&  \
    apt-get clean autoclean && apt-get autoremove --yes && rm -rf /var/lib/{apt,dpkg,cache,log}/

# Logger
COPY logger /logger

# Cleaner
COPY cleaner /cleaner/

# Supervisord config
COPY /supervisord/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Python requirements
COPY requirements.txt /requirements.txt
RUN mkdir -p /var/lib/registry/ && \
    pip3 install -U -r /requirements.txt

RUN wget -O registry.tar.gz https://github.com/distribution/distribution/releases/download/v2.8.1/registry_2.8.1_linux_amd64.tar.gz && \
    tar --extract --verbose --file registry.tar.gz --directory /bin/ registry && \
    rm registry.tar.gz

VOLUME ["/var/lib/registry"]
EXPOSE 8000

ENTRYPOINT ["/usr/bin/supervisord"]
