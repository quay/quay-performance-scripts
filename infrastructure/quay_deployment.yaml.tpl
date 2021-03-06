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
#            - secret:
#                name: quay-config-tls
        - name: extra-ca-certs
          configMap:
            name: cluster-service-ca
      containers:
        - name: quay-app
          image: ${quay_image}
          env:
            - name: QE_K8S_CONFIG_SECRET
              # FIXME: Using `vars` is kinda ugly because it's basically templating, but this needs to be the generated `Secret` name...
              value: $(QE_K8S_CONFIG_SECRET)
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
  selector:
    quay-component: quay-app
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
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: quay-route
  namespace: perftest1-quay
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
    ALLOW_PULLS_WITHOUT_STRICT_LOGGING: false
    AUTHENTICATION_TYPE: Database
    BUILDLOGS_REDIS:
      host: ${redis_host}
      port: ${redis_port}
      ssl: false
    DATABASE_SECRET_KEY: db-secret-key
    DB_CONNECTION_ARGS:
      autorollback: true
      threadlocals: true
    DB_URI: mysql+pymysql://${db_user}:${db_password}@${db_host}:${db_port}/quay
    DEFAULT_TAG_EXPIRATION: 2w
    DISTRIBUTED_STORAGE_CONFIG:
      s3_us_west_1:
      - CloudFrontedS3Storage
      - cloudfront_distribution_domain: ${cloudfront_distribution_domain}
        cloudfront_key_id: ${cloudfront_key_id}
        cloudfront_privatekey_filename: default-cloudfront-signing-key.pem
        s3_access_key: ${s3_access_key_id}
        s3_secret_key: ${s3_secret_key}
        s3_bucket: ${s3_bucket_name}
        storage_path: "/images"
    DISTRIBUTED_STORAGE_DEFAULT_LOCATIONS:
    - s3_us_west_1
    DISTRIBUTED_STORAGE_PREFERENCE:
    - s3_us_west_1
    ENTERPRISE_LOGO_URL: /static/img/quay-horizontal-color.svg
    EXTERNAL_TLS_TERMINATION: false
    FEATURE_BUILD_SUPPORT: false
    FEATURE_DIRECT_LOGIN: true
    FEATURE_MAILING: false
    FEATURE_PROXY_STORAGE: false
    FEATURE_SECURITY_NOTIFICATIONS: true
    FEATURE_SECURITY_SCANNER: true
    FEATURE_STORAGE_REPLICATION: false
    PREFERRED_URL_SCHEME: https
    REGISTRY_TITLE: Quay
    REGISTRY_TITLE_SHORT: Quay
    SECRET_KEY: odokjFBbOqQkg-lhiHwE0ZNcUIT46VfONf8uLfLTUW-Vj2vphWLjpxjxCrKA3OTY-iO802SJiMSb0B63
    SECURITY_SCANNER_INDEXING_INTERVAL: 30
    SECURITY_SCANNER_V4_ENDPOINT: http://clair-app:80
    SECURITY_SCANNER_V4_NAMESPACE_WHITELIST:
    - admin
    SECURITY_SCANNER_V4_PSK: ${clair_auth_psk}
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
