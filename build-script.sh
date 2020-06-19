#!/usr/bin/bash -u

prefix=perf-test
user_prefix=perf-test
num_users=${NUM_USERS:-500}
num_images=${NUM_IMAGES:-100}
num_tags=${NUM_TAGS:-10}
quay=${QUAY_URL}
token=${TOKEN}
pick=$((1 + RANDOM % ${num_users}))


user=${prefix}_user_${pick}

echo "Logging with user ${user}"
podman login ${quay} --tls-verify=false -u ${user} -p password
for i in `seq 1 ${num_images}`; do
  image=${quay}/${user}/${prefix}_${RANDOM}-${i}
  touch file${i}
  echo -e "FROM scratch\nCOPY file${i} myfile" | podman build  -f - . -t ${image}:latest
  rm file${i}
  for tag in `seq 1 ${num_tags}`; do
    podman tag ${image}:latest ${image}:tag${tag}
    echo Pushing ${image}:tag${tag}
    start=$(date +%s)
    podman push --tls-verify=false ${image}:tag${tag}
    echo $(($(date +%s) - ${start})) >> push-performance.log
  done
done

cat push-performance.log
