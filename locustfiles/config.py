

class Settings(object):
    # Url Paths
    V2_AUTH = '/v2/auth'
    INITIALIZE_USER = '/api/v1/user/initialize'
    DELETE_USER = '/api/v1/user/'
    V1_CREATE_ORG = '/api/v1/organization/'
    V1_CREATE_REPO = '/api/v1/repository'

    CONTAINER_IMAGES = [
        "quay.io/prometheus/node-exporter",
        "quay.io/projectquay/quay",
        "quay.io/openshift-release-dev/ocp-release:4.11.16-multi",
        "quay.io/jetstack/cert-manager-controller:v1.9.2",
        "quay.io/jetstack/cert-manager-webhook:v1.9.2",
        "quay.io/openshift/origin-oauth-proxy",
        "quay.io/prometheus/prometheus",
        "quay.io/coreos/etcd:v3.5.5",
        "quay.io/oauth2-proxy/oauth2-proxy",
        "quay.io/thanos/thanos:main-2022-11-18-baac7aa",
        "quay.io/prometheus/alertmanager",
        "quay.io/coreos/flannel:v0.15.1",
        "quay.io/k8scsi/csi-node-driver-registrar:canary",
        "quay.io/kubernetes-ingress-controller/nginx-ingress-controller:master",
        "quay.io/coreos/kube-state-metrics",
        "quay.io/external_storage/nfs-client-provisioner",
        "quay.io/openshift/origin-cli",
        "quay.io/parkervcp/pterodactyl-images:ubuntu_source",
    ]

    USER_INIT_METADATA = {
        "username": "quay-perf-tester",
        "password": "password",
        "email": "quay-perf@tester.com",
        "access_token": True,
        "access_token_val": "",
        "container_host": "",
    }

    ORG_COUNTER = 0
