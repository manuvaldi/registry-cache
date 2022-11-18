LIMIT="${CLEANER_MAXSIZE:-1G}"
THRESHOLD="${CLEANER_THRESHOLD_PERCENTAGE:-20}"
RUNEVERYSECONDS="${CLEANER_RUNEVERY_TIME:-15m}"


##### Functions

## Kudos https://stackoverflow.com/a/31625253
function human2bytes()
{
    echo $1 | awk \
      'BEGIN{IGNORECASE = 1}
       function printpower(n,b,p) {printf "%u\n", n*b^p; next}
       /[0-9]$/{print $1;next};
       /K(iB)?$/{printpower($1,  2, 1)};
       /M(iB)?$/{printpower($1,  2, 10)};
       /G(iB)?$/{printpower($1,  2, 20)};
       /T(iB)?$/{printpower($1,  2, 30)};
       /KB$/{    printpower($1, 10,  1)};
       /MB$/{    printpower($1, 10,  3)};
       /GB$/{    printpower($1, 10,  6)};
       /TB$/{    printpower($1, 10,  9)}'
}

function human2seconds()
{
  echo "$1" | awk -F '[hm.]' '{ print ($1 * 3600) + ($2 * 60) + $3 }'
}
##### Main

LIMIT=$(human2bytes $LIMIT)
RUNEVERYSECONDS=$(human2seconds $$RUNEVERYSECONDS)
THLIMIT=$(echo $LIMIT $THRESHOLD | awk '{printf "%4.0f\n",$1*(1+($2/100))}')
DOCKERDIR=/var/lib/registry/docker

echo " * LIMIT           : $LIMIT"
echo " * LIMIT THRESHOLD : ${THRESHOLD}%"
echo " * LIMIT TH SIZE   : $THLIMIT ($(human2bytes $THLIMIT))"
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
