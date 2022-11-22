# registry-cache

Deploy an container Registry as a pull through cache with cleaner to control the max size. It's base on podman deployment feature able to deploy Kubernetes YAML files.

The deployment has 2 containers

. `registry`: based on official registry v2 with an starting script to generate registry config.
. `toolbox`: running two process with supervisord:
.. `logger`: which takes the container requests and update the access time of the layers (blobs).
.. `cleaner`: sort blobs by access time an remove blobs until used size of registry was between limits


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
