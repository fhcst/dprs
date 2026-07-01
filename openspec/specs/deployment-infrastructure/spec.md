# deployment-infrastructure Specification

## Purpose

TBD - created by archiving change 'productionize-deployment'. Update Purpose after archive.

## Requirements

### Requirement: Cloudflare Tunnel as the sole public ingress

The deployment SHALL provide a `cloudflared` service in `docker-compose.yml` under `profiles: [tunnel]`. The service SHALL use image `cloudflare/cloudflared:latest`, run `command: tunnel --no-autoupdate run` (a token-based, remotely-managed tunnel whose ingress route is configured in the Cloudflare dashboard to point at `http://app:8000`), set `restart: unless-stopped`, and depend on the `app` service. The tunnel SHALL reach the application over the compose network by service name `app:8000`; no `config.yml` or credentials file SHALL be required in the repository.

The `TUNNEL_TOKEN` and `TUNNEL_TRANSPORT_PROTOCOL` values SHALL be supplied from `.env` and injected into the `cloudflared` service environment.

#### Scenario: Tunnel service runs under the tunnel profile

- **WHEN** the operator runs `docker compose --profile tunnel up`
- **THEN** the `cloudflared` service SHALL start with image `cloudflare/cloudflared:latest` and command `tunnel --no-autoupdate run`
- **THEN** the tunnel SHALL connect to the application at `http://app:8000` over the compose network using the configured `TUNNEL_TOKEN`

#### Scenario: No tunnel config or credentials committed to the repository

- **WHEN** the repository is inspected
- **THEN** there SHALL be no `config.yml` or tunnel credentials file
- **THEN** the tunnel route SHALL be configured entirely via the Cloudflare dashboard and the `TUNNEL_TOKEN` from `.env`


<!-- @trace
source: productionize-deployment
updated: 2026-07-01
code:
  - .understand-anything/knowledge-graph.json
  - .understand-anything/.understandignore
  - .understand-anything/fingerprints.json
  - .understand-anything/meta.json
  - .understand-anything/intermediate/scan-result.json
  - .understand-anything/config.json
-->

---
### Requirement: Application not publicly reachable on host port 8000 in tunnel mode

The default `app` service in `docker-compose.yml` SHALL NOT publish host port 8000. When running the tunnel profile, the only external ingress SHALL be the Cloudflare Tunnel, and the host SHALL expose no application port.

A separate, non-auto-merged development overlay file `docker-compose.dev.yml` SHALL re-publish the application on `127.0.0.1:8000` for local development, and SHALL be applied explicitly via `docker compose -f docker-compose.yml -f docker-compose.dev.yml up`. Because this overlay is NOT auto-merged (unlike `docker-compose.override.yml`, which compose would merge into every `-f`-less invocation regardless of profile), it SHALL NOT affect `docker compose --profile tunnel up`, which therefore publishes no host port. This mechanism SHALL be documented.

#### Scenario: Tunnel-profile bring-up exposes nothing on the host

- **WHEN** the operator runs `docker compose --profile tunnel up`
- **THEN** no host port SHALL be published for the `app` service
- **THEN** the application SHALL be reachable only through the Cloudflare Tunnel

#### Scenario: Local development re-publishes the app on loopback

- **WHEN** the developer runs `docker compose -f docker-compose.yml -f docker-compose.dev.yml up`
- **THEN** the application SHALL be reachable on `127.0.0.1:8000` of the host for local development
- **THEN** because `docker-compose.dev.yml` is NOT auto-merged, `docker compose --profile tunnel up` SHALL remain portless and unaffected by this overlay


<!-- @trace
source: productionize-deployment
updated: 2026-07-01
code:
  - .understand-anything/knowledge-graph.json
  - .understand-anything/.understandignore
  - .understand-anything/fingerprints.json
  - .understand-anything/meta.json
  - .understand-anything/intermediate/scan-result.json
  - .understand-anything/config.json
-->

---
### Requirement: Trusted reverse proxy forwarding for end-to-end Secure cookies

The deployment SHALL set `FORWARDED_ALLOW_IPS` for the `app` service so the application trusts the `X-Forwarded-Proto: https` header sent by `cloudflared`. The trusted value SHALL be a documented compose-network value (e.g. the docker bridge CIDR), supplied via `.env` and wired into the existing uvicorn `--forwarded-allow-ips` mechanism. This setting is required so that scheme detection and Secure cookies work correctly behind the tunnel.

The documentation SHALL state that a tunnel/production deployment MUST set `FASTAPI_APP_ENVIRONMENT=prod` so that Secure cookies and the secret guard engage, given that TLS is terminated at the Cloudflare edge (browser-to-edge is HTTPS).

#### Scenario: App trusts cloudflared forwarded scheme

- **WHEN** `cloudflared` forwards a request with header `X-Forwarded-Proto: https` from a compose-network address within the trusted `FORWARDED_ALLOW_IPS` range
- **THEN** the application SHALL treat the request scheme as `https`
- **THEN** Secure cookies SHALL be honored end-to-end behind the tunnel

#### Scenario: Production environment required for Secure cookies

- **WHEN** the deployment runs behind the Cloudflare Tunnel
- **THEN** the documentation SHALL require `FASTAPI_APP_ENVIRONMENT=prod`
- **THEN** with `FASTAPI_APP_ENVIRONMENT=prod`, the application SHALL emit Secure cookies and enforce the SESSION_SECRET guard


<!-- @trace
source: productionize-deployment
updated: 2026-07-01
code:
  - .understand-anything/knowledge-graph.json
  - .understand-anything/.understandignore
  - .understand-anything/fingerprints.json
  - .understand-anything/meta.json
  - .understand-anything/intermediate/scan-result.json
  - .understand-anything/config.json
-->

---
### Requirement: CSRF and SameSite strategy unchanged by tunnel introduction

Introducing the Cloudflare Tunnel SHALL NOT change the CSRF protection strategy or the cookie `SameSite` setting. Per `docs/security-notes.md` SEC-DESIGN-001, JSON-API CSRF protection relies on CORS preflight (because `application/json` is a non-simple content type) plus the `SameSite=Lax` cookie. The tunnel only adds a trusted reverse proxy in front of the application; `FORWARDED_ALLOW_IPS` affects scheme detection only and SHALL NOT alter the `SameSite` or CORS policy.

#### Scenario: Cookie SameSite and CSRF policy remain as documented

- **WHEN** this change is applied
- **THEN** the cookie `SameSite=Lax` setting SHALL remain unchanged
- **THEN** the JSON-API CSRF protection SHALL still rely on CORS preflight plus the SameSite cookie, consistent with SEC-DESIGN-001


<!-- @trace
source: productionize-deployment
updated: 2026-07-01
code:
  - .understand-anything/knowledge-graph.json
  - .understand-anything/.understandignore
  - .understand-anything/fingerprints.json
  - .understand-anything/meta.json
  - .understand-anything/intermediate/scan-result.json
  - .understand-anything/config.json
-->

---
### Requirement: MongoDB backup via mongodump with credentials from environment

The deployment SHALL provide `scripts/backup.sh` that runs `mongodump` using the same MongoDB credentials as docker-compose (`MONGO_ROOT_USERNAME`, `MONGO_ROOT_PASSWORD`, `MONGO_DB_NAME`) read from the environment, and writes a timestamped, gzip-compressed archive into a host-mounted `./backups/` directory. The script SHALL be idempotent (repeated runs produce additional timestamped files without overwriting prior backups), SHALL create `./backups/` if absent, and SHALL NOT hardcode the MongoDB password. The script header or documentation SHALL include a `mongorestore` restore note.

The `./backups/` directory SHALL be added to `.gitignore`, and no dump files SHALL be committed.

#### Scenario: Backup produces a timestamped archive

- **WHEN** the operator runs `scripts/backup.sh` against a running mongo service
- **THEN** a gzip-compressed dump SHALL be written under `./backups/` with a filename containing a timestamp
- **THEN** the MongoDB password SHALL be read from the environment and SHALL NOT appear hardcoded in the script

#### Scenario: Repeated backups do not overwrite

- **WHEN** `scripts/backup.sh` is run twice
- **THEN** two distinct timestamped archive files SHALL exist under `./backups/`

#### Scenario: Backups are git-ignored

- **WHEN** the repository is inspected
- **THEN** `./backups/` SHALL be listed in `.gitignore`
- **THEN** no dump files SHALL be tracked by git

<!-- @trace
source: productionize-deployment
updated: 2026-07-01
code:
  - .understand-anything/knowledge-graph.json
  - .understand-anything/.understandignore
  - .understand-anything/fingerprints.json
  - .understand-anything/meta.json
  - .understand-anything/intermediate/scan-result.json
  - .understand-anything/config.json
-->