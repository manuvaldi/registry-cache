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

for registry in $(cat $PULLSECRETPATH |  jq -r  '.auths | keys | join(" ")'); do

  # Check if element in ignore_list
  if [[ " ${IGNOREREGISTRYLIST[*]} " =~ " ${registry} " ]]; then
    # Element in the ignore list
    echo -e " * Ignoring registry $registry\n"
    continue

  fi
  INDEX=$(( INDEX + 1))
  echo " * Registry: $registry"
  authentry=$(cat $PULLSECRETPATH | jq  -r '.auths["'$registry'"].auth')

  user=$(echo $authentry  | base64 -d | awk -F":" '{print $1}')
  pass=$(echo $authentry  | base64 -d | awk -F":" '{print $2}')

  registry_clean="$(echo $registry | tr '/' '_' | tr ':' '_')"

  export REGISTRY=$registry_clean
  export LISTENPORT=$(( INITIALPORT + INDEX*2 - 2 ))
  export LISTENPORTSTATS=$(( LISTENPORT + 1 ))
  echo " * Listen Ports: $LISTENPORT, $LISTENPORTSTATS"

  cat $TOOLBOXPATH/config-base.yaml | envsubst > $ETCDOCKERPATH/config-$registry_clean.yml

  echo 'proxy:' >> $ETCDOCKERPATH/config-$registry_clean.yml
  echo "  remoteurl: https://$registry" >> $ETCDOCKERPATH/config-$registry_clean.yml
  echo "  username: $user" >> $ETCDOCKERPATH/config-$registry_clean.yml
  echo "  password: $pass" >> $ETCDOCKERPATH/config-$registry_clean.yml

  # Generate config for supervisord for each registry
  export REGISTRYCLEAN=$registry_clean
  export REGISTRYCONFIGFILE=$ETCDOCKERPATH/config-$registry_clean.yml
  cat $TOOLBOXPATH/supervisord-config-registry-base.conf | envsubst > $SUPERVISORDPATH/config-registry-$registry_clean.conf

  # Generating frontend rules for haproxy
  echo -e "\n# Rule for $registry " > /haproxy/config-registry-rule-$registry_clean.cfg
  echo "    use_backend $registry_clean if { path_reg (/v2)?/$registry }" >> /haproxy/config-registry-rule-$registry_clean.cfg
  # Generating backends for haproxy
  echo "backend $registry_clean" > /haproxy/config-registry-backend-$registry_clean.cfg
  echo "    reqrep ^(.*)/v2/$registry/(.*)     \1/v2/\2" >> /haproxy/config-registry-backend-$registry_clean.cfg
  echo "    server registry_backend 127.0.0.1:$LISTENPORT check-ssl ssl verify none" >> /haproxy/config-registry-backend-$registry_clean.cfg

  echo ""
done


# Composing Haproxy config
echo "    default_backend $registry_clean" > /haproxy/config-registry-default.cfg
cat /haproxy/haproxy.cfg /haproxy/config-registry-rule-*.cfg /haproxy/config-registry-default.cfg /haproxy/config-registry-backend-*.cfg > /haproxy/haproxy-final.cfg

# creating lock file
2>/dev/null > /generateconfig.lock

# Reloading supervisord
echo " * Reloading Supervisord"
supervisorctl reload
