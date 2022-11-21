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

RUN mkdir -p /var/lib/registry/ && \
    pip3 install -U -r /logger/requirements.txt

EXPOSE 8000

CMD ["/usr/bin/supervisord"]
