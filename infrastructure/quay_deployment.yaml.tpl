apiVersion: v1
kind: Namespace
metadata:
   name: ${namespace}
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: cluster-service-ca
  namespace: ${namespace}
  annotations:
    service.beta.openshift.io/inject-cabundle: 'true'
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: quay-app
  namespace: ${namespace}
  labels:
    quay-component: quay-app
spec:
  replicas: ${replicas}
  selector:
    matchLabels:
      quay-component: quay-app
  template:
    metadata:
      labels:
        quay-component: quay-app
    spec:
      serviceAccountName: quay-app
      volumes:
        - name: config
          projected:
            sources:
            - secret:
                name: quay-config-secret
        - name: extra-ca-certs
          configMap:
            name: cluster-service-ca
      containers:
        - name: quay-app
          image: ${quay_image}
          imagePullPolicy: Always
          env:
            - name: QE_K8S_CONFIG_SECRET
              value: quay-config-secret
            - name: QE_K8S_NAMESPACE
              valueFrom:
                fieldRef:
                  fieldPath: metadata.namespace
            - name: DEBUGLOG
              value: "false"
            - name: WORKER_COUNT_WEB
              value: "4"
            - name: WORKER_COUNT_SECSCAN
              value: "2"
            - name: WORKER_COUNT_REGISTRY
              value: "8"
            - name: IGNORE_VALIDATION
              value: "true"

          ports:
            - containerPort: 8443
              protocol: TCP
            - containerPort: 8080
              protocol: TCP
            - containerPort: 8081
              protocol: TCP
            - containerPort: 9091
              protocol: TCP
            - containerPort: 55443
              protocol: TCP
          resources:
            requests:
              cpu: 2000m
              memory: 8Gi
            limits:
              cpu: 2000m
              memory: 8Gi
          startupProbe:
            httpGet:
              path: /health/instance
              port: 8443
              scheme: HTTPS
            timeoutSeconds: 20
            periodSeconds: 15
            failureThreshold: 10
          readinessProbe:
            httpGet:
              path: /health/instance
              port: 8443
              scheme: HTTPS
          livenessProbe:
            httpGet:
              path: /health/instance
              port: 8443
              scheme: HTTPS
          volumeMounts:
            - name: config
              readOnly: false
              mountPath: /conf/stack
            - name: extra-ca-certs
              readOnly: true
              mountPath: /conf/stack/extra_ca_certs
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: quay-app
  namespace: ${namespace}
rules:
- apiGroups:
  - ""
  resources:
  - secrets
  verbs:
  - get
  - patch
  - update
- apiGroups:
  - ""
  resources:
  - namespaces
  verbs:
  - get
- apiGroups:
  - extensions
  - apps
  resources:
  - deployments
  verbs:
  - get
  - list
  - patch
  - update
  - watch
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: quay-app
  namespace: ${namespace}
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: quay-app
  namespace: ${namespace}
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: quay-app
subjects:
- kind: ServiceAccount
  name: quay-app
---
apiVersion: v1
kind: Service
metadata:
  name: quay-app
  namespace: ${namespace}
  labels:
    quay-component: quay-app
spec:
  type: ClusterIP
  ports:
    - protocol: TCP
      name: https
      port: 443
      targetPort: 8443
    - protocol: TCP
      name: http
      port: 80
      targetPort: 8080
    - name: jwtproxy
      protocol: TCP
      port: 8081
      targetPort: 8081
    - name: grpc
      protocol: TCP
      port: 55443
      targetPort: 55443
    - name: metrics
      protocol: TCP
      port: 9091
      targetPort: 9091
  selector:
    quay-component: quay-app
---
apiVersion: v1
kind: Service
metadata:
  name: quay-app-lb
  namespace: ${namespace}
  labels:
    quay-component: quay-app
spec:
  type: LoadBalancer
  ports:
    - protocol: TCP
      name: https
      port: 443
      targetPort: 8443
    - protocol: TCP
      name: http
      port: 80
      targetPort: 8080
    - name: jwtproxy
      protocol: TCP
      port: 8081
      targetPort: 8081
    - name: grpc
      protocol: TCP
      port: 55443
      targetPort: 55443
    - name: metrics
      protocol: TCP
      port: 9091
      targetPort: 9091
  selector:
    quay-component: quay-app
---
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: quay-route
  namespace: ${namespace}
spec:
  host: ${quay_route_host}
  port:
    targetPort: https
  tls:
    insecureEdgeTerminationPolicy: Redirect
    termination: passthrough
  to:
    kind: Service
    name: quay-app
    weight: 100
  wildcardPolicy: None
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: quay-app
  namespace: ${namespace}
---
apiVersion: v1
kind: Secret
metadata:
  name: quay-config-secret
  namespace: ${namespace}
stringData:
  default-cloudfront-signing-key.pem : |
    ${cloudfront_signing_key_pem}
  ssl.cert : |
    ${ssl_cert}
  ssl.key : |
    ${ssl_key}

  config.yaml: |

    REGISTRY_STATE: ${registry_state}
    ALLOW_PULLS_WITHOUT_STRICT_LOGGING: false
    AUTHENTICATION_TYPE: Database
    DATABASE_SECRET_KEY: db-secret-key
    DB_CONNECTION_ARGS:
      autorollback: true
      threadlocals: true
    DB_URI: postgresql://${db_user}:${db_password}@${db_host}:${db_port}/quay
    DEFAULT_TAG_EXPIRATION: 2w
    DISTRIBUTED_STORAGE_CONFIG:
      s3_us_east_1:
      - CloudFrontedS3Storage
      - cloudfront_distribution_domain: ${cloudfront_distribution_domain}
        cloudfront_key_id: ${cloudfront_key_id}
        cloudfront_privatekey_filename: default-cloudfront-signing-key.pem
        s3_access_key: ${s3_access_key_id}
        s3_secret_key: ${s3_secret_key}
        s3_bucket: ${s3_bucket_name}
        s3_region: us-east-1
        cloudfront_distribution_org_overrides: {}
        storage_path: "/images"
    DISTRIBUTED_STORAGE_DEFAULT_LOCATIONS:
    - s3_us_east_1
    DISTRIBUTED_STORAGE_PREFERENCE:
    - s3_us_east_1
    ENTERPRISE_LOGO_URL: /static/img/quay-horizontal-color.svg
    EXTERNAL_TLS_TERMINATION: false
    FEATURE_DIRECT_LOGIN: true
    FEATURE_MAILING: false
    FEATURE_PROXY_STORAGE: false
    FEATURE_SECURITY_NOTIFICATIONS: true
    FEATURE_SECURITY_SCANNER: ${enable_clair}
    FEATURE_STORAGE_REPLICATION: false
    PREFERRED_URL_SCHEME: https
    REGISTRY_TITLE: Quay
    REGISTRY_TITLE_SHORT: Quay
    SECRET_KEY: odokjFBbOqQkg-lhiHwE0ZNcUIT46VfONf8uLfLTUW-Vj2vphWLjpxjxCrKA3OTY-iO802SJiMSb0B63
    %{ if enable_clair } 
    SECURITY_SCANNER_INDEXING_INTERVAL: 30
    SECURITY_SCANNER_V4_ENDPOINT: http://clair-app:80
    SECURITY_SCANNER_V4_NAMESPACE_WHITELIST:
    - admin
    SECURITY_SCANNER_V4_PSK: ${clair_auth_psk}
    %{ endif }
    SERVER_HOSTNAME: ${quay_route_host}
    SETUP_COMPLETE: true
    TAG_EXPIRATION_OPTIONS:
    - 2w
    TEAM_RESYNC_STALE_TIME: 60m
    TESTING: false
    USER_EVENTS_REDIS:
      host: ${redis_host}
      port: ${redis_port}
      ssl: false

    FEATURE_BUILD_SUPPORT: True
    BUILDLOGS_REDIS:
      host: ${redis_host}
      port: ${redis_port}
      ssl: false

    USERFILES_LOCATION: s3_us_east_1
    LOG_ARCHIVE_LOCATION: s3_us_east_1
    ACTION_LOG_ARCHIVE_LOCATION: s3_us_east_1
    BUILDMAN_HOSTNAME: ${quay_route_host}:55443

    BUILD_MANAGER:
    - ephemeral
    - ALLOWED_WORKER_COUNT: 5
      ORCHESTRATOR_PREFIX: buildman/dev/
      ORCHESTRATOR:
        REDIS_HOST: ${redis_host}
        REDIS_SSL: false
        REDIS_SKIP_KEYSPACE_EVENT_SETUP: true

      EXECUTORS:
      - EXECUTOR: ec2
        DEBUG: True
        EC2_REGION: ${region}
        COREOS_AMI: ami-04a183f7a13130882
        AWS_ACCESS_KEY: ${builder_access_key}
        AWS_SECRET_KEY: ${builder_secret_key}
        EC2_INSTANCE_TYPE: t2.large
        EC2_VPC_SUBNET_ID: ${builder_subnet_id}
        EC2_SECURITY_GROUP_IDS:
        - ${builder_security_group_id}
        EC2_KEY_NAME: ${builder_ssh_keypair}
        WORKER_IMAGE: quay.io/projectquay/quay-builder
        WORKER_TAG: master
        VOLUME_SIZE: 52G # Size in truncate notation for the BTRFS volume
        BLOCK_DEVICE_SIZE: 58
        SETUP_TIME: 180
        MAX_LIFETIME_S: 3600

%{ if  enable_clair }    
---
apiVersion: apps/v1
kind: Deployment
metadata:
  labels:
    quay-component: clair-app
  name: clair-app
  namespace: ${namespace}
spec:
  replicas: ${clair_replicas}
  selector:
    matchLabels:
      quay-component: clair-app
  template:
    metadata:
      labels:
        quay-component: clair-app
    spec:
      serviceAccountName: clair-app
      containers:
        - image: ${clair_image}
          imagePullPolicy: Always
          name: clair-app
          env:
            - name: CLAIR_CONF
              value: /clair/config.yaml
            - name: CLAIR_MODE
              value: combo
          ports:
            - containerPort: 8080
              name: clair-http
              protocol: TCP
            - containerPort: 8089
              name: clair-intro
              protocol: TCP
          volumeMounts:
            - mountPath: /clair/
              name: config
#            - mountPath: /var/run/certs
#              name: certs
          startupProbe:
            tcpSocket:
              port: clair-intro
            periodSeconds: 10
            failureThreshold: 300
          readinessProbe:
            tcpSocket:
              port: 8080
          livenessProbe:
            httpGet:
              port: clair-intro
              path: /healthz
      restartPolicy: Always
      volumes:
        - name: config
          secret:
            secretName: clair-config-secret
#        - name: certs
#          secret:
#            secretName: quay-config-tls
#            # Mount just the public certificate because we are using storage proxying.
#            items:
#              - key: ssl.cert
#                path: quay-ssl.cert
---
apiVersion: v1
kind: Service
metadata:
  name: clair-app
  namespace: ${namespace}
  labels:
    quay-component: clair-app
spec:
  ports:
    - name: clair-http
      port: 80
      protocol: TCP
      targetPort: 8080
    - name: clair-introspection
      port: 8089
      protocol: TCP
      targetPort: 8089
  selector:
    quay-component: clair-app
  type: ClusterIP
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: clair-app
---
apiVersion: v1
kind: Service
metadata:
  name: clair-app
  labels:
    quay-component: clair-app
spec:
  ports:
    - name: clair-http
      port: 80
      protocol: TCP
      targetPort: 8080
    - name: clair-introspection
      port: 8089
      protocol: TCP
      targetPort: 8089
  selector:
    quay-component: clair-app
  type: ClusterIP
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: quay-app
  namespace: ${namespace}
---
apiVersion: v1
kind: Secret
metadata:
  name: clair-config-secret
  namespace: ${namespace}
stringData:
  config.yaml: |
    http_listen_addr: :8080
    introspection_addr: ""
    log_level: info
    indexer:
        connstring: host=${clair_db_host} port=${clair_db_port} dbname=clair user=${clair_db_user} password=${clair_db_password} sslmode=disable
        scanlock_retry: 10
        layer_scan_concurrency: 5
        migrations: true
        scanner:
            package: {}
            dist: {}
            repo: {}
        airgap: false
    matcher:
        connstring: host=${clair_db_host} port=${clair_db_port} dbname=clair user=${clair_db_user} password=${clair_db_password} sslmode=disable
        max_conn_pool: 100
        indexer_addr: ""
        migrations: true
        period: null
        disable_updaters: false  
  
    notifier:
      connstring: host=${clair_db_host} port=${clair_db_port} dbname=clair user=${clair_db_user} password=${clair_db_password} sslmode=disable
      migrations: true
      indexer_addr: ""
      matcher_addr: ""
      poll_interval: 5m
      delivery_interval: 1m
      webhook:
        target: https://quay-app/secscan/notification
        callback: http://quay-app/notifier/api/v1/notifications
        headers: {}
        signed: false
      amqp: null
      stomp: null

    auth:
        psk:
            key: ${clair_auth_psk}
            iss:
                - quay
                - clairctl

    metrics:
        name: prometheus
        prometheus:
            endpoint: null
        dogstatsd:
            url: ""

%{ endif }

%{ if enable_monitoring}
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
  namespace: ${namespace}
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
      evaluation_interval: 15s
    scrape_configs:
      - job_name: 'quay'
        static_configs:
          - targets: ["${quay_route_host}:9091"]
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: prometheus
  namespace: ${namespace}
  labels:
    app: prometheus-app
spec: 
  replicas: 1
  selector:
    matchLabels:
      app: prometheus-app
  template:
    metadata:
      labels:
        app: prometheus-app
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "9090"
    spec:
      containers:
      - name: prometheus
        image: ${prometheus_image}
        args:
          - '--storage.tsdb.retention=6h'
          - '--storage.tsdb.path=/prometheus'
          - '--config.file=/etc/prometheus/prometheus.yml'
        ports:
          - name: web
            containerPort: 9090
        volumeMounts:
          - name: prometheus-config-volume
            mountPath: /etc/prometheus
          - name: prometheus-storage-volume
            mountPath: /prometheus/
      restartPolicy: Always
      volumes:
      - name: prometheus-config-volume
        configMap:
          defaultMode: 420
          name: prometheus-config
      - name: prometheus-storage-volume
        emptyDir: {}
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-datasources
  namespace: "${namespace}"
data:
  prometheus.yaml: |-
    {
        "apiVersion": 1,
        "datasources": [
            {
                "access": "proxy",
                "editable": true,
                "name": quay-prometheus,
                "orgId": 1,
                "type": prometheus,
                "url": "http://${prometheus_host}:9090",
                "version": 1
            }
        ]
    }
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: grafana
  namespace: "${namespace}"
spec:
  replicas: 1
  selector:
    matchLabels:
      app: grafana-app
  template:
    metadata:
      name: grafana-app
      labels:
        app: grafana-app
    spec:
      containers:
      - name: grafana
        image: ${grafana_image}
        ports:
          - name: grafana
            containerPort: 3000
        volumeMounts:
          - mountPath: /var/lib/grafana
            name: grafana-storage
          - mountPath: /etc/grafana/provisioning/datasources
            name: grafana-datasources
            readOnly: false
      volumes:
        - name: grafana-storage
          emptyDir: {}
        - name: grafana-datasources
          configMap:
            defaultMode: 420
            name: grafana-datasources
%{ endif }
