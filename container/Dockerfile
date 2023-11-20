FROM registry.access.redhat.com/ubi8/ubi-minimal:8.9

ENV PATH /usr/local/bin:$PATH

RUN microdnf update \
    && microdnf install \
       python3 wget binutils findutils tar gzip ca-certificates tzdata procps-ng jq gettext \
       haproxy rsyslog \
    && microdnf clean all  \
    && rm -rf /var/cache/yum \
    && rpm -e --nodeps $(rpm -qa '*rpm*' '*dnf*' '*libsolv*' '*hawkey*' 'yum*')

# Python requirements and supervisor installation
COPY requirements.txt /requirements.txt

RUN mkdir -p /var/lib/registry/  \
    && mkdir -p /etc/supervisor/conf.d /var/log/supervisor \
    && pip3 install -U -r /requirements.txt

# Registry binary
RUN wget -O registry.tar.gz https://github.com/distribution/distribution/releases/download/v2.8.3/registry_2.8.3_linux_amd64.tar.gz && \
    tar --extract --verbose --file registry.tar.gz --directory /bin/ registry && \
    rm registry.tar.gz && \
    mkdir -p /etc/docker/registry/

# Logger
COPY logger /logger

# Cleaner
COPY cleaner /cleaner

# Toolbox
COPY toolbox /toolbox

# haproxy
COPY haproxy /haproxy

# Supervisord config
COPY /supervisord/supervisord-base.conf /etc/supervisor/supervisord.conf
COPY /supervisord/supervisord.conf      /etc/supervisor/conf.d/supervisord.conf

# Rsyslog config
COPY /rsyslog/rsyslog.conf /etc/rsyslog.d/

VOLUME ["/var/lib/registry"]
EXPOSE 8000

CMD ["/usr/local/bin/supervisord", "-c", "/etc/supervisor/supervisord.conf"]
