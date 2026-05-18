# SRE Final Project — Microservices Platform

A production-ready microservices application deployed on DigitalOcean with full CI/CD automation, monitoring, and infrastructure as code.

## Architecture Overview

The platform consists of 6 backend microservices, a frontend, a PostgreSQL database, and a monitoring stack.

```
┌─────────────┐     ┌──────────────────────────────────────────────┐
│   Frontend  │────▶│  auth · product · order · user · review · audit │
│  (Nginx:80) │     └──────────────────────────────────────────────┘
└─────────────┘                        │
                                       ▼
                               ┌──────────────┐
                               │  PostgreSQL  │
                               └──────────────┘
                                       │
                         ┌─────────────▼──────────────┐
                         │  Prometheus + Grafana       │
                         │  node-exporter              │
                         └────────────────────────────┘
```

Service                Port  Description 

frontend               8080  Nginx-served web UI 
auth-service           3001  JWT authentication 
product-service        3002  Product catalog 
order-service          3003  Order management 
user-profile-service   3004  User profiles 
review-service         3005  Product reviews 
audit-service          3006  Audit logging 
prometheus             9090  Metrics collection 
grafana                3000  Metrics dashboards 
node-exporter          9100  Host metrics 

## Tech Stack

- **Backend**: Python 3.11, FastAPI, Uvicorn
- **Frontend**: HTML/CSS/JS, Nginx
- **Database**: PostgreSQL 15
- **Containerization**: Docker, Docker Compose
- **Orchestration**: Kubernetes (Minikube), Docker Swarm
- **Infrastructure**: Terraform (DigitalOcean)
- **Configuration Management**: Ansible
- **CI/CD**: GitHub Actions
- **Monitoring**: Prometheus, Grafana, Node Exporter

## CI/CD Pipeline

The pipeline is defined in `.github/workflows/ci-cd.yml` and runs automatically on every push to `main`.

```
git push → main
     │
     ▼
[Lint & Test] ──── flake8 for each service (parallel)
     │
     ▼
[Build & Push] ─── builds 7 Docker images → ghcr.io
     │
     ▼
[Deploy] ────────── Ansible connects via SSH to DigitalOcean Droplet,
                    pulls new images, restarts docker-compose
     │
     ▼
[Health Check] ──── curl http://SERVER_IP:8080
```

### Pipeline Jobs

Job                      Description 

Lint & Test            - Runs flake8 on all 6 Python services in parallel |
Build & Push Images    - Builds Docker images and pushes to GitHub Container Registry (ghcr.io) |
Deploy to DigitalOcean - Runs Ansible playbook over SSH to deploy on the server |


## Project Structure

```
Microservices_project/
├── .github/
│   └── workflows/
│       └── ci-cd.yml          # GitHub Actions CI/CD pipeline
├── ansible/
│   ├── inventory.ini          # Server inventory (dynamic in CI)
│   ├── playbook.yml           # Deployment playbook
│   └── roles/
│       ├── app/               # App deployment role
│       ├── docker/            # Docker installation role
│       └── monitoring/        # Monitoring setup role
├── terraform/
│   ├── main.tf                # DigitalOcean Droplet + Firewall
│   ├── variables.tf
│   ├── outputs.tf
│   └── terraform.tfvars       # (not committed — use secrets)
├── k8s/                       # Kubernetes manifests
│   ├── namespace.yml
│   ├── configmap.yml
│   ├── secret.yml
│   ├── postgres-deployment.yml
│   └── *-deployment.yml       # Per-service deployments
├── prometheus/
│   ├── prometheus.yml         # Scrape config
│   └── alert_rules.yml        # Alerting rules
├── auth-service/
├── product-service/
├── order-service/
├── user-profile-service/
├── review-service/
├── audit-service/
├── frontend/
├── docker-compose.yml         # Local / production compose
├── docker-compose.swarm.yml   # Docker Swarm config
└── init-db.sql                # Database initialization
```

## Infrastructure

Provisioned with **Terraform** on **DigitalOcean**:

- Ubuntu 22.04 Droplet
- Firewall rules: ports 22, 80, 8080, 3000, 9090, 9100
- SSH key authentication

cd terraform
terraform init
terraform plan
terraform apply

## Local Development

### Prerequisites

- Docker & Docker Compose
- Python 3.11

### Run locally

git clone https://github.com/bgl96395/SRE_FINAL_PROJECT.git
cd SRE_FINAL_PROJECT

# Copy and configure env files
cp .env.example .env

# Start all services
docker-compose up -d

# Check status
docker-compose ps

Services will be available at:
- Frontend: http://localhost:8080
- Grafana: http://localhost:3000
- Prometheus: http://localhost:9090


## Secrets Configuration

All secrets are stored as **GitHub Actions Secrets** and never committed to the repository.

 `SSH_PRIVATE_KEY` - Private SSH key for DigitalOcean server access 
 `SERVER_IP` - DigitalOcean Droplet IP address 
 `DO_TOKEN` - DigitalOcean Personal Access Token 
 `POSTGRES_USER` - PostgreSQL username 
 `POSTGRES_PASSWORD` - PostgreSQL password 
 `POSTGRES_DB` - PostgreSQL database name 
 `SECRET_KEY` - JWT secret key for auth-service 
 `AUTH_DATABASE_URL` - auth-service database connection string 
 `PRODUCT_DATABASE_URL` - product-service database connection string 
 `ORDER_DATABASE_URL` - order-service database connection string 
 `USER_PROFILE_DATABASE_URL` - user-profile-service database connection string 
 `REVIEW_DATABASE_URL` - review-service database connection string 
 `AUDIT_DATABASE_URL` - audit-service database connection string 

## Monitoring

- **Prometheus** scrapes metrics from all services and node-exporter
- **Grafana** provides dashboards for visualization
- **Alert rules** are defined in `prometheus/alert_rules.yml`

Access:
- Grafana: `http://139.59.133.84:3000` 
- Prometheus: `http://139.59.133.84:9090`

## Kubernetes

Kubernetes manifests are located in `k8s/`. To deploy on Minikube:

minikube start
kubectl apply -f k8s/namespace.yml
kubectl apply -f k8s/configmap.yml
kubectl apply -f k8s/secret.yml
kubectl apply -f k8s/postgres-deployment.yml
kubectl apply -f k8s/
