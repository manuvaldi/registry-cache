LIMIT="${CLEANER_MAXSIZE:-1000000}"
THRESHOLD="${CLEANER_THRESHOLD_PERCENTAGE:-20}"
thlimit=$(echo $LIMIT $THRESHOLD | awk '{printf "%4.0f\n",$1*(1+($2/100))}')

DOCKERDIR=/var/lib/registry/docker

echo " * LIMIT           : $LIMIT"
echo " * LIMIT THRESHOLD : ${THRESHOLD}%"
echo " * LIMIT TH SIZE   : $thlimit"
while true; do
  size=$(du -s $DOCKERDIR | awk '{print $1}')
  sizeh=$(du -hs $DOCKERDIR | awk '{print $1}')
  echo " ** SIZE: $size (${sizeh})"
  if [ $size -gt $thlimit ]; then
    while [ $size -gt $LIMIT ]; do
      echo " ** Cleaning ($size > $thlimit)"
      du -hs /var/lib/registry
      ls -lu -tu -r $DOCKERDIR/registry/v2/blobs/sha256/*/*  | grep blobs | head -n 1 | tr -d ":" | xargs rm -Rf
      size=$(du -s $DOCKERDIR | awk '{print $1}')
      sizeh=$(du -hs $DOCKERDIR | awk '{print $1}')
    done
    registry garbage-collect /etc/docker/registry/config.yml &>/dev/null
    echo " ** NEW SIZE: $size ( ${sizeh} )"
  fi
  sleep 30
done
