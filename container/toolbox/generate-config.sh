PULLSECRETPATH="${PULLSECRETPATH:=/pull-secret.json}"
TOOLBOXPATH="${TOOLBOXPATH:=/toolbox}"
ETCDOCKERPATH="${ETCDOCKERPATH:=/etc/docker/registry}"
SUPERVISORDPATH="${SUPERVISORDPATH:=/etc/supervisor/conf.d}"
INITIALPORT="${INITIALPORT:=5000}"
IGNOREREGISTRYLIST="${IGNOREREGISTRYLIST:=cloud.openshift.com}"

INDEX=0
INITIALPORT=5000

# Check is Lock File exists, if exists exit
if [ -f "/generateconfig.lock" ]; then
  echo " * Lock file exists... not generating nor reloading supervisord config"
  exit
fi

echo " * Generating registries and haproxy config files"
for registry in $(cat $PULLSECRETPATH |  jq -r  '.auths | keys | sort_by(length) | reverse | join(" ")'); do

  # Check if element in ignore_list
  if [[ " ${IGNOREREGISTRYLIST[*]} " =~ " ${registry} " ]]; then
    echo -e " * Ignoring registry $registry\n"
    continue
  fi

  INDEX=$(( INDEX + 1))

  authentry=$(cat $PULLSECRETPATH | jq  -r '.auths["'$registry'"].auth | select (.!=null)')
  user=$(echo $authentry  | base64 -d | awk -F":" '{print $1}')
  pass=$(echo $authentry  | base64 -d | awk -F":" '{print $2}')
  export registry_clean="$(echo $registry | tr '/' '_' | tr ':' '_')"
  export REGISTRY=$registry_clean
  export LISTENPORT=$(( INITIALPORT + INDEX*2 - 2 ))
  export LISTENPORTSTATS=$(( LISTENPORT + 1 ))

  echo " * Registry: $registry"
  echo " * Listen Ports: $LISTENPORT, $LISTENPORTSTATS"

  # Generate registry config
  cat $TOOLBOXPATH/config-base.yaml | envsubst > $ETCDOCKERPATH/config-$registry_clean.yml
  echo 'proxy:' >> $ETCDOCKERPATH/config-$registry_clean.yml
  if [ "$registry" == "docker.io" ]; then # Exception for docker.io
    echo "  remoteurl: https://registry-1.docker.io" >> $ETCDOCKERPATH/config-$registry_clean.yml
  else
    echo "  remoteurl: https://$registry" >> $ETCDOCKERPATH/config-$registry_clean.yml
  fi
  if [ "$user" != "" ]; then # In case no auth string in pullsecret json
    echo "  username: $user" >> $ETCDOCKERPATH/config-$registry_clean.yml
    echo "  password: $pass" >> $ETCDOCKERPATH/config-$registry_clean.yml
  fi

  # Generate config for supervisord for each registry
  export REGISTRYCLEAN=$registry_clean
  export REGISTRYCONFIGFILE=$ETCDOCKERPATH/config-$registry_clean.yml
  cat $TOOLBOXPATH/supervisord-config-registry-base.conf | envsubst > $SUPERVISORDPATH/config-registry-$registry_clean.conf

  # Generating frontend rules for haproxy
  echo -e "\n# Rule for $registry                                          " > /haproxy/config-registry-rule-$INDEX-$registry_clean.cfg
  echo "    use_backend $registry_clean if { path_reg ^(?:/v2)?/$registry }" >> /haproxy/config-registry-rule-$INDEX-$registry_clean.cfg
  # Generating backends for haproxy
  echo -e "\n# Backend for $registry                      " > /haproxy/config-registry-backend-$INDEX-$registry_clean.cfg
  echo "backend $registry_clean                           " >> /haproxy/config-registry-backend-$INDEX-$registry_clean.cfg
  echo "    reqrep ^(.*)/v2/[a-z0-9.]*/(.*)     \1/v2/\2  " >> /haproxy/config-registry-backend-$INDEX-$registry_clean.cfg
  echo "    server registry_backend 127.0.0.1:$LISTENPORT " >> /haproxy/config-registry-backend-$INDEX-$registry_clean.cfg

  echo ""

done


# Composing Haproxy config
echo -e "\n    default_backend $registry_clean\n" > /haproxy/config-registry-default.cfg
cat /haproxy/haproxy.cfg /haproxy/config-registry-rule-*.cfg /haproxy/config-registry-default.cfg /haproxy/config-registry-backend-*.cfg > /haproxy/haproxy-final.cfg

# creating lock file
2>/dev/null > /generateconfig.lock

# Reloading supervisord
echo " * Reloading Supervisord"
supervisorctl reload
