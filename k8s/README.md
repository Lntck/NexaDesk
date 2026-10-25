# NexaDesk on Kubernetes

Application stack (app, PostgreSQL, Redis), Gateway API routing and the observability
stack (logging and alerting). The application is installed with helmfile, gateway and
observability are plain manifests applied with kubectl.

## Layout

* helmfile.yaml: release list, install order, chart versions
* charts/nexadesk-app: umbrella chart with the app-config ConfigMap, the migration job
  and the backend/frontend subcharts
* environments/dev: per-environment values for the app, PostgreSQL and Redis
* secrets: app-secrets.yaml with real credentials (git-ignored), app-secrets.yaml.example
  is the template
* gateway: raw manifests for GatewayClass, Gateway and HTTPRoute (Envoy Gateway)
* observability: raw manifests for VictoriaLogs, vlagent, Grafana, vmalert and Alertmanager

## Prerequisites

* a cluster with kubectl (minikube is enough for development)
* helm and helmfile on the workstation
* Envoy Gateway controller running in the cluster (namespace envoy-gateway-system)
* access to the bitnami chart repository

## Deploy

1. Fill in the secrets and apply them. The secret must exist before the install:
   the PostgreSQL chart reads its passwords from it and the migration hook runs
   against it.

```bash
cd k8s
cp secrets/app-secrets.yaml.example secrets/app-secrets.yaml
kubectl create namespace nexadesk
kubectl apply -f secrets/app-secrets.yaml
```

2. Install the application stack.

```bash
helmfile sync
```

3. Apply gateway and observability manifests.

```bash
kubectl apply -f observability/ -R
kubectl apply -f gateway/
```

Gateway routes reference the app services, so apply it after helmfile sync.
Observability is independent and can be applied at any time.

4. Check the result.

```bash
kubectl get pods -n nexadesk
kubectl get pods -n observability
```

## Releases

* nexadesk-db: bitnami/postgresql, standalone, 1Gi PVC, probes and resource limits,
  passwords from app-secrets (environments/dev/postgres-values.yaml)
* nexadesk-redis: bitnami/redis, password auth from app-secrets
* nexadesk-app: umbrella chart, app-config ConfigMap, alembic migration job, backend
  and frontend deployments with probes and security contexts, backend-metrics Service
  and a NetworkPolicy limiting the metrics port to the monitoring namespaces

Install order is enforced by helmfile needs: db and redis first, then the app.

Outside helm, kubectl apply brings up two more stacks:

* gateway: GatewayClass envoy-gateway, Gateway nexadesk on port 80 and two HTTPRoutes
* observability: logging and alerting stack in the observability namespace

## Migration job

* runs alembic upgrade head as a pre-install and pre-upgrade hook, so the schema is
  ready before the app pods start
* the wait-for-db init container polls pg_isready against the configured host
* the hook reads connection settings from app-secrets (always applied beforehand) and
  takes the app-config ConfigMap as optional, because on a fresh install the ConfigMap
  is created together with the release, after the hook has run
* hook-delete-policy before-hook-creation,hook-succeeded removes the job after success,
  ttlSecondsAfterFinished is a fallback for failed runs

## Gateway routing

* /api/v1/projects/{id}/events: SSE stream, RegularExpression match, request and
  backendRequest timeouts disabled (0s)
* /health: backend probes, 30s request timeout
* /api: backend API, 30s request timeout
* /: frontend SPA, 30s request timeout

Only the SSE stream needs an unlimited timeout, everything else is bounded on purpose.
RegularExpression match precedence over PathPrefix is implementation-specific in the
Gateway API, but Envoy Gateway prioritises regex matches: this was verified with marker
rules on a live cluster. Keep the SSE rule as RegularExpression when editing the routes.

## Metrics

* the backend serves OpenMetrics at /metrics on a dedicated port (METRICS_PORT,
  default 9100) configured through the app-config ConfigMap
* the backend-metrics Service exposes the port inside the cluster and is not
  referenced by the HTTPRoutes, so the gateway never forwards to it
* NetworkPolicy backend keeps port 8000 open for the gateway, probes and in-cluster
  clients and limits port 9100 to metrics.networkPolicy.scrapeNamespaces
  (observability by default). The port carries no authentication, so the policy is
  the only access control
* the monitoring system scrapes backend-metrics.nexadesk.svc:9100 from its own
  namespace; locally Docker Compose publishes the same port for curl and scrapers

When METRICS_PORT is changed, change backend.metrics.port as well: the container
port and the Service targetPort follow it.

On minikube without a cloud load balancer the Gateway shows Programmed=False with
reason AddressNotAssigned and the envoy service stays pending. Traffic still works
through the node port or through minikube tunnel:

```bash
minikube tunnel                       # gives the LoadBalancer an external IP
kubectl get svc -n envoy-gateway-system   # or use the printed node port
curl http://$(minikube ip):<node-port>/health
```

## Logging

* vlagent runs as a DaemonSet on every node, tails /var/log and
  /var/lib/docker/containers, adds kubernetes metadata (pod, namespace, container,
  node) and ships records to VictoriaLogs over /insert/native with an on-disk buffer
* VictoriaLogs is a single-replica StatefulSet with a 10Gi PVC and 30 day retention
* the backend writes structured JSON to stdout, so its fields stay queryable

Example LogsQL queries (VictoriaLogs HTTP API on port 9428 or Grafana Explore):

```
service.name:nexadesk-backend AND level:ERROR | stats by (kubernetes.pod_name) count()
kubernetes.pod_namespace:nexadesk | stats by (kubernetes.container_name) count()
```

## Monitoring and alerting

* Grafana 13 with the victoriametrics-logs-datasource plugin, provisioned from a
  ConfigMap together with log level rules. Credentials are admin/admin, port-forward
  svc/grafana -n observability 3000:3000
* vmalert evaluates the nexadesk-logs rule group (type vlogs) every minute with a 2
  minute pending window: BackendErrors on ERROR records from the backend, DbRoleErrors
  on postgres role errors on nexadesk-db-postgresql-0. Port-forward svc/vmalert
  -n observability 8880:8880 and open /vmalert
* Alertmanager groups and deduplicates fired alerts. The bundled receiver is named
  "null" and drops them: alerts are evaluated and visible in vmalert, but not
  delivered anywhere. Add a real receiver (webhook, mail) in
  observability/monitoring/alertmanager-config.yaml to get deliveries

The stack is log-based today. Metrics (vmagent, VictoriaMetrics, dashboards) are a
planned addition.

## Notes

* gateway and observability manifests are not versioned by helm: after editing them
  run kubectl apply -f on the changed file, delete-and-create is only needed for
  fields that Kubernetes forbids to update
* the Gateway node port changes when the Gateway object is recreated, take the
  current one from kubectl get svc -n envoy-gateway-system
* the storage-provisioner deprecation warning about v1 Endpoints in kube-system comes
  from the minikube addon, not from these manifests, and is harmless
* secrets never go to git: only app-secrets.yaml.example is committed
