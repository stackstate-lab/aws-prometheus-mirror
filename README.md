# StackState Prometheus Mirror

Prometheus mirror is a gateway between StackState and Prometheus that enables Prometheus telemetry in StackState.
Supports also AWS Managed Prometheus.

## Prerequisites
The Prometheus Mirror has the following prerequisites:

- The mirror must be reachable from StackState
- Authentication Support
  - Full authentication support for AWS Managed Prometheus
  - Currently, no authentication method supported for self-hosted Prometheus

## Mirror configuration
The Prometheus mirror is configured using the following parameters:

- global.apiKey - the API key used to authenticate communication between the mirror and StackState
- workers - number of workers processes (default: 20)
- port - the port the mirror is listening on (default: 9900)

## StackState configuration

In order to start using Prometheus mirror in StackState one has to create Mirror Datasource

### Configure Mirror Datasource

Create a new Mirror datasource:

- **DataSourceUrl** - points to the Prometheus mirror endpoint, for example http://prometheusmirror.stackstate.svc.cluster.local:9900/
- **API Key** - should be the same key as specified by global.apiKey mirror configuration
- **Connection Details JSON** - the mirror configuration json, for example:
```json
{
    "url": "<prometheus host>",
    "request_timeout_seconds": 30,
    "nan_interpretation": "ZERO",
    "aws": {
      "role_arn": "Required when no aws_session_token",
      "external_id": "Required when no aws_session_token",
      "aws_access_key_id": "Optional[str]",
      "aws_secret_access_key": "Optional[str]",
      "aws_session_token": "Optional[str]",
      "region_name": "eu-west-1",
      "role_session_name": "StackState-Prometheus-Mirror"
    }
}
```
Prometheus `url` refers to the actual Prometheus `url` (not the mirror).

## Query Configuration

### Prometheus Counter
Counter queries fetch counter metrics from Prometheus. The retrieved counter values are transformed to a rate.

The following are sample parameters for a counter query:

- __counter__ = go_memstats_lookups_total
- job = payment-service
- name = payment
- instance = 127.0.0.1:80

### Prometheus Gauge
Gauge queries fetch gauge metrics from Prometheus.

The following are sample parameters for a gauge query:

- __gauge__ = go_gc_duration_seconds
- job = payment-service
- name = payment
- instance = 127.0.0.1:80

### Prometheus Histogram and Summary
Prometheus histogram and summary queries are not supported from the query interface. They still can be configured using tilda-query.

### Tilde query ~
The query allows arbitrary Prometheus queries, for example:

`~ = histogram_quantile(0.95, sum(rate(request_duration_seconds_bucket{instance='127.0.0.1:80', name='payment-service'}[1m])) by (name, le)) * 1000`





## Development

---
### Prerequisites:

- Python v.3.11.x See [Python installation guide](https://docs.python-guide.org/starting/installation/)
- [PDM](https://pdm.fming.dev/latest/#recommended-installation-method)
- [Docker](https://www.docker.com/get-started)
---

### Setup local code repository

```bash 
git clone git@github.com:stackstate-lab/aws-prometheus-mirror.git
cd aws-prometheus-mirror
pdm install 
```
The `pdm install` command sets up all the projects required dependencies using 
[PEP 582](https://peps.python.org/pep-0582/) instead of virtual environments.

### Prepare local _.env_ file

The `.env` file is used to define aws credentials that can be used to connect to prometheus. 

```bash

cat <<EOF > ./.env
prometheus_url=https://aps-workspaces.eu-west-1.amazonaws.com/workspaces/ws-43e5c1ec-b45c-42cc-a165-aa023b5dd70b/
aws_access_key_id=ASIA2BOTXQ5ZXAEAVFXG
aws_secret_access_key=v9dkHCVlWCGZTP/kmZfJBJJMJVjVLi8n9P1a/RPK
aws_session_token=IQoJb3JpZ2luX2VjEFkaDGV1LWNlbnRyYWwtMSJHMEUCIFjzXD4GNZ9JrlT+pL5KvnK5boiBNACtgzh3wpw8BF8fAiEA70rVLg
EOF
```

### Code styling and linting


- [Black](https://black.readthedocs.io/en/stable/) for formatting
- [isort](https://pycqa.github.io/isort/) to sort imports
- [Flakehell](https://flakehell.readthedocs.io/) for linting
- [mypy](https://mypy.readthedocs.io/en/stable/) for static type checking

```bash
pdm format
```

### Running unit tests

```bash
pdm test
```

### Build

```bash
pdm build
```

### Starting the mirror

```bash
pdm serve
```
---
### Building the AWS Prometheus Mirror container

---



