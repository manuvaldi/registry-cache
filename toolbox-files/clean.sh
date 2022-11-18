LIMIT="${CLEANER_MAXSIZE:-1000000}"
THRESHOLD="${CLEANER_THRESHOLD_PERCENTAGE:-20}"
RUNEVERYSECONDS="${CLEANER_RUNEVERY_SECONDS:-300}"

THLIMIT=$(echo $LIMIT $THRESHOLD | awk '{printf "%4.0f\n",$1*(1+($2/100))}')
DOCKERDIR=/var/lib/registry/docker

echo " * LIMIT           : $LIMIT"
echo " * LIMIT THRESHOLD : ${THRESHOLD}%"
echo " * LIMIT TH SIZE   : $THLIMIT"
echo " * RUNNING EVERY   : ${RUNEVERYSECONDS} seconds"

while true; do
  size=$(du -s $DOCKERDIR | awk '{print $1}')
  sizeh=$(du -hs $DOCKERDIR | awk '{print $1}')
  echo " ** CURRENT SIZE: $size (${sizeh})"
  if [ $size -gt $THLIMIT ]; then
    while [ $size -gt $LIMIT ]; do
      echo " ** Cleaning ($size > $THLIMIT)"
      du -hs /var/lib/registry
      ls -lu -tu -r $DOCKERDIR/registry/v2/blobs/sha256/*/*  | grep blobs | head -n 1 | tr -d ":" | xargs rm -Rf
      size=$(du -s $DOCKERDIR | awk '{print $1}')
      sizeh=$(du -hs $DOCKERDIR | awk '{print $1}')
    done
    registry garbage-collect /etc/docker/registry/config.yml &>/dev/null
    echo " ** AFTER CLEAN SIZE: $size ( ${sizeh} )"
  fi
  sleep $RUNEVERYSECONDS
done
