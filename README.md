# registry-cache

Deploy an container Registry as a pull through cache with cleaner to control the max size.

The deployment has 1 containers which running 3 proccess with supervisord

- `registry`: based on official registry v2 with an starting script to generate registry config with quay.io cache enabled. Credential are extracted from `pull-secret.json`
- `logger`: which takes the container images requests and update the access time of the layers (blobs) and the manifests, in order to control the aging of them.
- `cleaner`: sort blobs by access time an remove oldest blobs until used size of registry was between limits.


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

### 4.- Generate TLS certificates
```
# openssl req -newkey rsa:4096 -nodes -sha256 -keyout /opt/registry/certs/domain.key -x509 -days 365 -out /opt/registry/certs/domain.crt
```

> Enter the respective options for your certificate. The CN= value is the hostname of your host. The host's hostname should be resolvable by DNS or the /etc/hosts file.

The certificate will also have to be trusted by your hosts and clients:
```
# cp /opt/registry/certs/domain.crt /etc/pki/ca-trust/source/anchors/
# update-ca-trust
# trust list | grep -i "<hostname>"
```

### 5.- Start registry

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
  -e REGISTRY_HTTP_TLS_CERTIFICATE=/certs/domain2.crt \
  -e REGISTRY_HTTP_TLS_KEY=/certs/domain2.key \
  -v /opt/registry/auth:/auth:z  
  -e "REGISTRY_AUTH=htpasswd" \
  -e "REGISTRY_AUTH_HTPASSWD_REALM=Registry Realm" \
  -e REGISTRY_AUTH_HTPASSWD_PATH=/auth/htpasswd \  
  -p 5000:5000 -p 5001:5001 \
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

## Firewall config

If a firewall is running on the hosts, the exposed ports (5000 and 5001) will need to be permitted.

```
# # Registry port
# firewall-cmd --add-port=5000/tcp --zone=internal --permanent
# firewall-cmd --add-port=5000/tcp --zone=public --permanent
# # Metrics port
# firewall-cmd --add-port=5001/tcp --zone=internal --permanent
# firewall-cmd --add-port=5001/tcp --zone=public --permanent
# firewall-cmd --reload
```

## Verify

We will try to pull `podman pull quay.io/podman/hello` image through our registry

```
# podman login <hostname>:5000
Enter Username:xxxxxxxx
Enter Password:yyyyyyyy
Login Succeeded!

# podman pull <hostname>:5000/podman/hello
Trying to pull <hostname>:5000/podman/hello:latest...
Getting image source signatures
Copying blob 6cabff02f88a done  
Copying config aa50a552cd done  
Writing manifest to image destination
Storing signatures
aa50a552cd5be7fa8772f3be53db149827dd8a42294030543012261836ce8cdb
```
## Image

Images is building by Quay.io. You can find it in https://quay.io/repository/mvalledi/registry-cache


## References:

- [Red Hat Blog - How to implement a simple personal/private Linux container image registry for internal use](https://www.redhat.com/sysadmin/simple-container-registry)
