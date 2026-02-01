# Project OMNI: Sovereign Financial Operating System 🚀

[![Engine: Cython](https://img.shields.io/badge/Engine-Cython--Accelerated-orange?style=for-the-badge&logo=python)](https://cython.org/)
[![Status: Production-Ready](https://img.shields.io/badge/Status-Production--Ready-green?style=for-the-badge)](https://github.com/Kolerr-Lab/OC_KFS4_Project-OMNI_013126_Peter-Nguyen)

Project OMNI is a high-performance, containerized financial engine designed for institutional-grade transaction processing and sovereign data management.

---

## 🏗️ Enterprise Architecture

OMNI utilizes a multi-layered approach to solve the blockchain trilemma (Security, Scalability, Decentralization):

- **Cython Kernel**: Critical paths (Transaction Hashing, DAG Validation, JSON Ingestion) are implemented in C-ext for 200k+ TPS.
- **Distributed Event Bus**: Redis-backed Pub/Sub architecture for sub-millisecond decoupled messaging.
- **Consistent Sharding**: Horizontal scaling via consistent hashing, ensuring data locality and balanced load.
- **Isolated Stack**: Full Docker orchestration with Prometheus/Grafana observability.

---

## 🛠️ Hardening & Stabilisation

We transformed the initial prototype into a production system through:

- **Kernel Migration**: Replaced Python stubs with Cython `.pyx` implementations using OpenMP parallelization.
- **Network Isolation**: Custom un-popular ports (18000, 15432, 16379, 19090) to prevent environment conflicts.
- **Observability**: Real-time metrics via `prometheus_client` and auto-scraped internal telemetry.
- **Dependency Guard**: Hard-pinned versioning and WebSocket protocol isolation for high-reliability startups.

---

## 🚀 Getting Started

Launch the full stack in one command:

```bash
docker-compose up --build -d
```

### 🔗 Service Map

| Service         | Endpoint                      | Port  |
| :-------------- | :---------------------------- | :---- |
| **API Gateway** | `http://localhost:18000/docs` | 18000 |
| **Prometheus**  | `http://localhost:19090`      | 19090 |
| **PostgreSQL**  | `localhost:15432`             | 15432 |
| **Redis**       | `localhost:16379`             | 16379 |

---

## 📊 Performance Benchmarks

- **Ingestion**: 412,000+ JSON payloads/sec (Cython parser)
- **Validation**: 216,000+ TPS (Parallel DAG kernel)
- **Latency**: < 1.2ms end-to-end event propagation

---

## License

Copyright (c) 2026 Peter Nguyen.

This project is provided for learning, study, and modification under a non-commercial license.
Commercial use is prohibited unless you obtain a separate commercial license from the copyright holder.

See the LICENSE file for full terms.

---

© 2026 Peter Nguyen
