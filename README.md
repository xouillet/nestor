# Nestor

Nestor is a wsgi app to password-protect a directory served statically over HTTP.
It can be used to protect sites generated from tools such as [sigal](https://github.com/saimn/sigal) or [pelican](https://github.com/getpelican/pelican).

## Prerequisites

Nestor is written in [Python](https://www.python.org) and relies on [starlette](https://www.starlette.io/) framework

Of course, using virtualenv is recommended

```
virtualenv3 venv
source venv/bin/activate
pip install -r requirements.txt
```

## Configuration

Configuration is done via environment variable or using a `.env` file. Here is a list of options.

### SECRET_KEY

Required. This key is used to sign cookies. It should be private and has not to be remembered. It has no specific format restriction.

### PASSWORD

Required. The password that will be asked to the user

### BG_PATH

Optional. A path to the background image of the login page

### AUTH_MODE

Optional. `http` or `domain` (see below).
Default is `http`.

### AUTH_DOMAIN_URL

Optional. When using domain (SSO) mode, set this to the URL pointing to the authentication container. 

## Usage

Nestor is an ASGI application and should be started via an ASGI server such as `uvicorn`.

```
SECRET_KEY="verysecret" PASSWORD="pipo" uvicorn --root-path /nestor nestor:app
```

### HTTP authentication (Nginx, apache)
Nestor aims to be used via the `ngx_http_auth_request_module` of nginx. Here is an example nginx configuration for nginx

```
    location /protected_folder {
        auth_request /nestor/auth;
        error_page 401 /nestor/login;
    }

    location /nestor/ {
       proxy_pass http://unix:/srv/http/nestor/nestor.sock:/;
       proxy_set_header Host $http_host;
       proxy_set_header X-Original-URI $request_uri;
       proxy_set_header X-Forwarded-Proto $scheme;
    }
```

Nestor should be started via `gunicorn` or `uvicorn`, here is an example `systemd` service

```
# /etc/systemd/system/nestor.service
[Unit]
Description=Nestor
After=network.target

[Service]
User=www-data
LimitNOFILE=4096
WorkingDirectory=/srv/http/nestor/
ExecStart=/srv/http/nestor/venv/bin/uvicorn --proxy-headers --forwarded-allow-ips * --root-path /nestor --uds /srv/http/nestor/nestor.sock nestor:app
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

### Domain authentication (Traefik)
Nestor can also be used as a simplified single sign-on (SSO) authenticator in a containerized environnement. A setup with Traefik's `forwardauth` middleware is presented below :

```yaml
# docker-compose.yml
  nestor:
    build: ./nestor
    container_name: "nestor"
    env_file: ./nestor/nestor.env
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.nestor.rule=Host(`auth.mydomain.com`)"
      - "traefik.http.routers.nestor.tls=true"
      - "traefik.http.routers.nestor.tls.certresolver=letsencrypt"
      - "traefik.http.middlewares.domain-auth.forwardauth.address=http://nestor:8123/auth"

  example-app:
    (...)
    labels:
      - "traefik.http.routers.example-app.middlewares=domain-auth"
```

```sh
# nestor/nestor.env
(...)
AUTH_MODE="domain"
AUTH_DOMAIN_URL="https://auth.mydomain.com"
```

```dockerfile
# nestor/Dockerfile
# with nestor source in the `src` subdirectory
FROM python:3.11-slim
WORKDIR /code
COPY ./src/requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt
COPY ./src/. /code/

EXPOSE 8123
CMD ["uvicorn", "nestor:app", "--proxy-headers", "--host", "0.0.0.0", "--port", "8123", "--forwarded-allow-ips", "*"]
```