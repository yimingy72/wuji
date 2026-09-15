# Kubernetes Web entry and local registry inventory

| Asset / interface | Runtime owner | Verification state | Scope and implication |
| --- | --- | --- | --- |
| `Deployment/wuji-web` | Kubernetes | verified / 2 of 2 containers Ready | Nginx frontend and browser-session gateway run in one Pod |
| `Service/wuji-web` | Kubernetes | verified / `LoadBalancer`, external hostname `localhost` | Exposes service port 44180 to target port 8080; replaces the former manual port-forward |
| `127.0.0.1:44180` listener | Docker Desktop Kubernetes integration | verified / `com.docker.backend` | No `kubectl port-forward` or host Wuji process owns the listener |
| `GET /healthz` | K8s Web Pod | verified / 200 | Complete HTTP exchange retained |
| `GET /` | K8s Web Pod | verified / 200 and complete HTML | Browser rendered the existing authenticated workbench with zero console errors |
| `wuji-vnext-build-registry` | Docker Desktop infrastructure container | verified / active | `registry:2`, Docker VM host network, registry-selected loopback port 56615. Current K8s image references use `127.0.0.1:56615/...@sha256:...`. It is image build/deployment infrastructure, not a Wuji request-serving component |
| `wuji-vnext-registry` | Docker Desktop infrastructure container | verified / unused legacy | `registry:2`, host mapping `127.0.0.1:62217`, catalog is exactly `{"repositories":[]}`; no current source or Pod image reference uses it. Removal is deferred and was not performed |
| In-cluster registry migration | not implemented | not selected | A ClusterIP registry cannot directly serve the node container runtime or bootstrap itself without a separate node-reachable endpoint and trust configuration; it would not remove the required Docker Desktop infrastructure boundary |

No new product API was discovered. The externally visible application URL remains `http://127.0.0.1:44180/`; its validation state changed from temporary port-forward to Kubernetes-managed LoadBalancer.
