# Nestor

Nestor is a wsgi app to password-protect a directory served statically over HTTP.
It can be used to protect sites generated from tools such as [sigal](https://github.com/saimn/sigal) or [pelican](https://github.com/getpelican/pelican).

## Prerequisites

Nestor is written in [Python](http://www.python.org) and relies on [bottle](http://www.bottlepy.org)

```
pip install bottle
pip install pyyaml
```

## Configuration

The configuration file is written in YAML. An example configuration is provided in `dist/config.yml`.

See `nestor.py` for detailed configurations directives.

## Usage

Nestor is a wsgi app so it is meant to be used by wsgi server such as [uwsgi](https://github.com/unbit/uwsgi), [gunicorn](http://gunicorn.org/) or
Apache's [mod_wsgi](https://modwsgi.readthedocs.io/en/develop/).

The wsgi app is located in `nestor.py` and accept `NESTOR_CONFIG` environment parameter to specify which configuration to use

An example uwsgi configuration is provided in the `dist/` directory.
