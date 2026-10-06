FROM registry.access.redhat.com/ubi8/ubi-minimal:8.10

ENV PATH /usr/local/bin:$PATH

RUN microdnf update \
    && microdnf install \
       python3.12 python3.12-pip \
       wget binutils findutils tar gzip ca-certificates tzdata procps-ng jq gettext \
       haproxy rsyslog \
       gcc make openssl-devel pcre-devel zlib-devel \
    && wget -O haproxy.tar.gz https://www.haproxy.org/download/2.8/src/haproxy-2.8.15.tar.gz \
    && tar -xzf haproxy.tar.gz \
    && make -C haproxy-2.8.15 -j"$(nproc)" \
         TARGET=linux-glibc USE_OPENSSL=1 USE_ZLIB=1 USE_PCRE=1 USE_THREAD=1 \
    && make -C haproxy-2.8.15 install PREFIX=/usr \
    && rm -rf haproxy.tar.gz haproxy-2.8.15 \
    && microdnf remove -y gcc make openssl-devel pcre-devel zlib-devel \
    && microdnf clean all \
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
EXPOSE 8443

CMD ["/usr/local/bin/supervisord", "-c", "/etc/supervisor/supervisord.conf"]
