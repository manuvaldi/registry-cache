HLIMIT="${CLEANER_MAXSIZE:-1G}"
THRESHOLD="${CLEANER_THRESHOLD_PERCENTAGE:-20}"
RUNEVERY="${CLEANER_RUNEVERY_TIME:-15m}"


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

## Kudos https://unix.stackexchange.com/a/44087
function bytes2human() {
  echo $1 | awk '
    function human(x) {
        if (x<1000) {return x} else {x/=1024}
        s="MGTEPZY";
        while (x>=1000 && length(s)>1)
            {x/=1024; s=substr(s,2)}
        return int(x+0.5) substr(s,1,1)
    }
    {sub(/^[0-9]+/, human($1)); print}'
}

function human2seconds()
{
  local time="$(echo $1 | sed 's/h/h\n/g' | sed 's/m/m\n/g' | sed 's/s/s\n/g' )"
  local hours=$(echo "$time" | grep h | tr -d 'h' | tr -d ' ')
  local mins=$(echo "$time" | grep m | tr -d 'm' | tr -d ' ')
  local secs=$(echo "$time" | grep s | tr -d 's' | tr -d ' ')
  echo ${hours:-0} ${mins:-0} ${secs:-0} | awk '{printf "%s",$1*60*60+$2*60+$3}'
}
##### Main

LIMIT=$(human2bytes ${HLIMIT})
RUNEVERYSECONDS=$(human2seconds $RUNEVERY)
THLIMIT=$(echo ${LIMIT} $THRESHOLD | awk '{printf "%4.0f\n",$1*(1+($2/100))}')
DOCKERDIR=/var/lib/registry/docker

echo " * LIMIT           : ${LIMIT} (${HLIMIT})"
echo " * LIMIT THRESHOLD : ${THRESHOLD}%"
echo " * LIMIT TH SIZE   : ${THLIMIT} ($(bytes2human ${THLIMIT}))"
echo " * RUNNING EVERY   : ${RUNEVERYSECONDS} seconds ($RUNEVERY)"

while true; do
  size=$(du -s $DOCKERDIR | awk '{print $1}')
  sizeh=$(du -hs $DOCKERDIR | awk '{print $1}')
  echo " ** CURRENT SIZE: $size (${sizeh})"
  if [ $size -gt ${THLIMIT} ]; then
    while [ $size -gt ${LIMIT} ]; do
      echo " ** Cleaning ($size > ${THLIMIT})"
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
