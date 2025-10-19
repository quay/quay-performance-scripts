#!/bin/bash

START=${START:-1}
END=${END:-10000}
RATE=${RATE:-16}
LAYERS=${LAYERS:-5}
LAYER_SUFFIX=$LAYERS
LAYERS=$((18 + ${LAYER_SUFFIX}))
LOAD_REPO=${LOAD_REPO:-"quay.io/vchalla/clair-load-test"}
IMAGES=${IMAGES:-"quay.io/clair-load-test/mysql:8.0.25"}

unique_id=$(cat /proc/sys/kernel/random/uuid)

for image in ${IMAGES//,/ }; do
  tag_prefix=$(basename "$image")
  lastword=${tag_prefix##*/}
  lastword=${lastword/:/_}

  seq $START $END | xargs -I {} -P $RATE bash -c '
    i="$1"
    base_image="$2"
    tag_prefix="$3"
    unique_id="$4"
    layers="$5"
    layers_suffix="$6"

    tag_name="${LOAD_REPO}:$(basename "${base_image}" | tr : _)_layers_${layers_suffix}_tag_${i}"

    dockerfile_tmp=$(mktemp)

    # Go builder stage
    cat >> "$dockerfile_tmp" <<EOF
FROM registry.access.redhat.com/ubi8/go-toolset:latest as gobuilder$i
WORKDIR /app$i
RUN echo -e "package main\nimport \"fmt\"\nfunc main() { fmt.Println(\"Hello, Docker!\") }" > main.go
RUN go mod init my_app$i
RUN go build -o my_app$i
EOF

    # Java builder stage
    cat >> "$dockerfile_tmp" <<EOF
FROM registry.access.redhat.com/ubi8/openjdk-8:1.3 as javabuilder$i
WORKDIR /app$i
RUN echo "public class HelloWorld { public static void main(String[] args) { System.out.println(\"Hello, Docker!\"); } }" > HelloWorld.java
RUN javac HelloWorld.java && jar cfe my_app$i.jar HelloWorld HelloWorld.class
EOF

    # Shell builder stage
    cat >> "$dockerfile_tmp" <<EOF
FROM registry.access.redhat.com/ubi8:latest AS shellbuilder$i
WORKDIR /app$i
RUN echo "#!/bin/sh" > myscript$i.sh && echo "echo \"Hello, world!\"" >> myscript$i.sh
EOF

    # Final stage (base + copied builders)
    cat >> "$dockerfile_tmp" <<EOF
FROM $base_image
WORKDIR /app$i
COPY --from=gobuilder$i /app$i/my_app$i /app$i/
COPY --from=javabuilder$i /app$i/my_app$i.jar /app$i/
COPY --from=shellbuilder$i /app$i/myscript$i.sh /app$i/
EOF

    # Generate dynamic N layers outside of cat <<EOF
    for ((l=1; l<=layers_suffix; l++)); do
      rand=$(uuidgen)
      echo "RUN echo \"This is layer $l for image $i with UUID $rand\" > layer_${l}_$i.txt" >> "$dockerfile_tmp"
    done

    echo "RUN chmod +x /app$i/*" >> "$dockerfile_tmp"

    # Build, push, remove
    podman build -f "$dockerfile_tmp" --tag "$tag_name" --storage-opt "overlay.mount_program=/usr/bin/fuse-overlayfs" --storage-driver overlay -
    podman push "$tag_name" --tls-verify=false --storage-opt "overlay.mount_program=/usr/bin/fuse-overlayfs" --storage-driver overlay
    podman rmi "$tag_name"

    rm -f "$dockerfile_tmp"
  ' _ {} "$image" "$lastword" "$unique_id" "$LAYERS" "$LAYER_SUFFIX" &
done
# Note: Use the below command to kill this process.
# sudo pkill -f 'podman.*--tag'
# Sample execution: START=1 END=10000 LAYERS=5 IMAGES="quay.io/clair-load-test/mysql:8.0.25" LOAD_REPO="quay.io/vchalla/clair-load-test" RATE=20 bash image_load.sh