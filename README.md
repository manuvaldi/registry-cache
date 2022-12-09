# registry-cache

Deploy one or many containers registry as a pull through cache with cleaner to control the max size. It allows private registries with credentials.

The deployment is a container which running some proccess running via supervisord:

- `registry`: based on official registry v2 with an starting script to generate registry config with quay.io cache enabled. Credential are extracted from `pull-secret.json`
- `logger`: which takes the container images requests and update the access time of the layers (blobs) and the manifests, in order to control the aging of them.
- `cleaner`: sort blobs by access time an remove oldest blobs until used size of registry was between limits.
- `haproxy`: reverse proxy for differents registries running (haproxy 1.8). Its redirect to the registry cache according to the path.
- `rsyslogd`: to be able to have logs from haproxy
- registries in pull through cache mode: every registry specified in `pull-secret.json` file will be used to run up an registry pull-through cache mode registry.


For example, if you want to cache a quay image instead of pulling `quay.io/podman/hello:latest`, you will pull `yourregistry.local/quay.io/podman/hello:latest`



## Architecture
```
                                ┌───────────────────┐
                                │                   ├─────────┐
┌──────────────────┐    ┌──────►│  Registry cache 1 ├────┐    │             datastore
│    HAProxy       ├────┘       └───────────────────┘    │    │         ┌─────────────────────┐
│                  │                                     │    └────────►│                     │
│ (reverse proxy)  ├───────┐    ┌───────────────────┐    │              │  blobs & manifests  │
└────────┬───────┬─┘       │    │                   ├────┼─────────────►│                     │
         │       │         └───►│  Registry cache 2 │    │              └─────────────────────┘
         │       │              └───────────────────┘    │               ▲    ▲    ▲
         │       │              ....                     │               │    │    │
         │       │              ┌───────────────────┐    │               │    │    │
         │       │              │                   │    │               │    │    │
         │       └─────────────►│  Registry cache n ├────┼───────────────┘    │    │
         │                      └───────────────────┘    │                    │    │
         │                                               │                    │    │
         │                                               │                    │    │
         ▼                                               ▼                    │    │
 ┌─────────────────┐                                ┌───────────────────┐     │    │
 │                 │                                │                   │     │    │
 │  RSYSLOG        │                                │   LOGGER          ├─────┘    │
 │                 │                                │                   │          │
 └─────────────────┘                                └───────────────────┘          │
                                                                                   │
                                                    ┌───────────────────┐          │
                                                    │                   │          │
                                                    │   CLEANER         ├──────────┘
                                                    │                   │
                                                    └───────────────────┘

```

## Deployment

### 1.- Install `podman`

```
# yum install -y podman httpd-tools
```

### 2.- Generate folders
```
# mkdir -p /opt/registry/{auth,certs,data}
```
- The **Auth** subdirectory stores the htpasswd file used for authentication.
- The **Certs** subdirectory stores certificates used by the registry for
authentication.
- The **Data** directory stores the actual images stored in the registry.


### 3.- Generate credentials for the registry (optional)

```
# htpasswd -bBc /opt/registry/auth/htpasswd registryuser registryuserpassword
```

### 4.- Generate TLS certificates and PEM file
```
# openssl req -newkey rsa:4096 -nodes -sha256 -keyout /opt/registry/certs/domain.key -x509 -days 365 -out /opt/registry/certs/domain.crt
```

> Enter the respective options for your certificate. The CN= value is the hostname of your host. The host's hostname should be resolvable by DNS or the /etc/hosts file.

and then build the `.pem` file:

```
cat /opt/registry/certs/domain.crt /opt/registry/certs/domain.key > /certs/certs.pem
```

IMPORTANT: the name of the PEM must be `certs.pem`

The certificate will also have to be trusted by your hosts and clients:
```
# cp /opt/registry/certs/domain.crt /etc/pki/ca-trust/source/anchors/
# update-ca-trust
# trust list | grep -i "<hostname>"
```

### 5.- Create a `pull-secret.json` file

The container and its config process analyze the pull secret JSON file provided and create a registry process per each credential according to it. The format of this JSON file is similar to kubernetes uses. Example:

```
{
   "auths":{
      "docker.io":{
      },     
      "registry.redhat.io":{
         "auth":"b3Blb=",
         "email":"you@example.com"
      },
      "quay.io":{
         "auth":"b3Blb=",
         "email":"you@example.com"
      }
   }
}
```
With this example, the container will cache images from `quay.io` and `registry.redhat.io`.

> It's important you map your pull secret to `/pull-secret.json` into the container.


### 6.- Start registry

There are two ways, with `podman play` feature or just with `podman run`:

#### with `podman play`

Edit variables in `deployment.yaml` and run:
```
podman play kube deployment.yaml

```

#### with `podman`
```
podman run -d --name registry-cache \
  -v /opt/registry/pull-secret.json:/pull-secret.json \
  -v /opt/registry/data:/var/lib/registry:z \
  -e CLEANER_MAXSIZE=10G \
  -e CLEANER_THRESHOLD_PERCENTAGE=20 \
  -e CLEANER_RUNEVERY_TIME=30m \
  -v /opt/registry/certs:/certs:z \
  -v /opt/registry/auth:/auth:z  
  -e "REGISTRY_AUTH=htpasswd" \
  -e "REGISTRY_AUTH_HTPASSWD_REALM=Registry Realm" \
  -e REGISTRY_AUTH_HTPASSWD_PATH=/auth/htpasswd \  
  -p 8443:8443 \
  quay.io/mvalledi/registry-cache:main

```


### Tear Down

```
podman play kube deployment.yaml --down
```
or
```
`podman stop registry-cache
```

## Configuration ENV vars

- `CLEANER_MAXSIZE`: Max Size in human redeable size (M, MB, MiB, G, GB, GiB, ...). By default "10G"
- `CLEANER_THRESHOLD_PERCENTAGE`: Percentage threshold. If cache takes more than `CLEANER_MAXSIZE` + `CLEANER_THRESHOLD_PERCENTAGE%`, then cleaner cleans. By default '20' (== 20%).
- `CLEANER_RUNEVERY_TIME`:Cleaner check every `CLEANER_RUNEVERY_TIME` the cache size. In format "1h2m3s". By default "30m" (== 30 minutes).
- `IGNOREREGISTRYLIST`: Space separated list of registries to be ignored from pull secret. By default 'cloud.openshift.com'.

## Firewall config

If a firewall is running on the hosts, the exposed port (8443) will need to be permitted.

```
# # Registry port
# firewall-cmd --add-port=8443/tcp --zone=internal --permanent
# firewall-cmd --add-port=8443/tcp --zone=public --permanent
# firewall-cmd --reload
```

## Verify

We will try to pull `quay.io/podman/hello` image through our registry

```
# podman login <hostname>:8443
Enter Username:xxxxxxxx
Enter Password:yyyyyyyy
Login Succeeded!

# podman pull <hostname>:8443/quay.io/podman/hello
Trying to pull <hostname>:8443/quay.io/podman/hello:latest...
Getting image source signatures
Copying blob 35e2aab76e8b done  
Copying config 133ff45f55 done  
Writing manifest to image destination
Storing signatures
133ff45f557da063a1f6f301866c7276c22ea07aeda078d00a790ea50516dcbc

```

## Image

Image is building by Quay.io. You can find it in https://quay.io/repository/mvalledi/registry-cache


## References:

- [Red Hat Blog - How to implement a simple personal/private Linux container image registry for internal use](https://www.redhat.com/sysadmin/simple-container-registry)
