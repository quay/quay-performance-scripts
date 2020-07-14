#!/usr/bin/bash -u
if [ "$#" -ne 1 ]; then
  echo "Usage: "
  echo "        ./script <user>"
  exit 1
fi

function create_tag() {
  repo=$1
  echo ""
  echo " Capture Token "
  echo " Run ${repo} - Iteration ${iter}"
  echo ""
  tag=$(dbus-uuidgen)
  target_token=$(curl -k -L --user ${prefix}_user_${pick}:password "https://${quay}/v2/auth?service=${quay}&scope=repository:${prefix}_user_${pick}/repo_${repo}:pull,push" | jq '.token' | sed -e 's/"//g')
  curl -k -L -X GET -H "Authorization: Bearer $target_token" "https://${quay}/v2/${prefix}_user_${pick}/repo_${repo}/manifests/latest" > /tmp/repo_manifest_${pick}_1_$tag
  content=$(jq '.tag="'"${tag}"'"' /tmp/repo_manifest_${pick}_1_$tag)
  echo $content > /tmp/repo_$tag.json
  start=$(date +%s)
  curl -k --data @/tmp/repo_$tag.json -L -X PUT -H "Authorization: Bearer $target_token" "https://${quay}/v2/${prefix}_user_${pick}/repo_${repo}/manifests/${tag}" -H "Content-Type: application/json"
  echo Tag : $(($(date +%s) - ${start})) >> /tmp/push-performance.log
}

prefix=${PREFIX:-perf-test}
quay=${QUAY_URL}
repos="10_tags 100_tags 500_tags 1000_tags 10000_tags 100000_tags"
pick=$1
quay=$QUAY_URL
max_concurrent=20

cat > /tmp/Dockerfile <<EOF
FROM quay.io/jitesoft/alpine:latest

EOF

for repo in $repos; do

  cd /tmp
  podman login ${quay} --tls-verify=false -u ${prefix}_user_${pick} -p password
  podman build --layers --force-rm --storage-driver overlay --storage-opt "overlay.mount_program=/usr/bin/fuse-overlayfs"  --tag ${pick} -f /tmp/Dockerfile
  podman tag ${pick} ${quay}/${prefix}_user_${pick}/repo_${repo} --storage-driver overlay --storage-opt "overlay.mount_program=/usr/bin/fuse-overlayfs"

  echo Pushing image
  start=$(date +%s)
  if podman push --tls-verify=false ${quay}/${prefix}_user_${pick}/repo_${repo} --storage-driver overlay --storage-opt "overlay.mount_program=/usr/bin/fuse-overlayfs"; then
    echo Init : $(($(date +%s) - ${start})) >> /tmp/push-performance.log
  else
    sleep 10
    podman push --tls-verify=false ${quay}/${prefix}_user_${pick}/repo_${repo} --storage-driver overlay --storage-opt "overlay.mount_program=/usr/bin/fuse-overlayfs"
    echo Init with Retry: $(($(date +%s) - ${start})) >> /tmp/push-performance.log
  fi

  sleep 60

  num_tags=$(echo ${repo} | awk -F_ '{print $1}')

  if [[ $num_tags -gt 0 ]]; then
    count=0
    echo $count
    echo $max_concurrent
    for iter in $(seq 1 $num_tags); do
      if [[ $count -gt $max_concurrent ]] ; then
        sleep 5
        count=0
      else
       create_tag $repo &
       echo "Running ${count}"
       count=$((count+1))
      fi
    done

  fi
done

cat /tmp/push-performance.log

