quay=$(cat /pull-secret.json | jq  -r '.auths["quay.io"].auth')
user=$(echo $quay  | base64 -d | awk -F":" '{print $1}')
pass=$(echo $quay  | base64 -d | awk -F":" '{print $2}')

cp /toolbox/config-original.yaml /etc/docker/registry/config.yml
echo 'proxy:' >> /etc/docker/registry/config.yml
echo '  remoteurl: https://quay.io' >> /etc/docker/registry/config.yml
echo "  username: $user" >> /etc/docker/registry/config.yml
echo "  password: $pass" >> /etc/docker/registry/config.yml
