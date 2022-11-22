# registry-cache

Deploy an container Registry as a pull through cache with cleaner to control the max size.

The deployment has 1 containers which running 3 proccess with supervisord

. `registry`: based on official registry v2 with an starting script to generate registry config.
. `logger`: which takes the container requests and update the access time of the layers (blobs).
. `cleaner`: sort blobs by access time an remove blobs until used size of registry was between limits


## Quick start

Edit `deployment.yaml` and run:

```
podman play kube deployment.yaml

```

## Tear Down

```
podman play kube deployment.yaml --down
```

## Config
