#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import base64
import hashlib
import hmac
import json
import logging
import urllib.parse

from starlette.applications import Starlette
from starlette.config import Config
from starlette.datastructures import Secret
from starlette.responses import RedirectResponse, Response, JSONResponse
from starlette.routing import Route
from starlette.templating import Jinja2Templates


templates = Jinja2Templates(directory="views")

# Config

config = Config(".env")
DEBUG = config("DEBUG", default=False)
SECRET_KEY = config("SECRET_KEY").encode("utf8")
PASSWORD = config("PASSWORD", cast=Secret)
ADMIN_PASSWORD = config("ADMIN_PASSWORD", cast=Secret)
AUTH_MODE = config("AUTH_MODE", default="http")
AUTH_DOMAIN_URL = config("AUTH_DOMAIN_URL", default="")
LOGIN_URL = config("LOGIN_URL", default=None)
BG_URL = config("BG_URL", default=None)
OVERLAY_PATH = config("OVERLAY_PATH", default="/_nestor")
COOKIE_NAME = config("COOKIE_NAME", default="_nestor_token")

# Logging

logger = logging.getLogger("uvicorn")
logger.setLevel(logging.DEBUG if DEBUG else logging.INFO)

#
# Cookie content and helpers
#


class Auths(list):
    """This class herits from list to add the check method
    A typical auth list contains paths.
    When a path is allowed, all its subfolder also are

    For example:
     * '/': Whole site is allowed
     * '/album/subalbum': Only subalbum is allowed
    """

    def check(self, _path):
        """ " Checks that _path is allowed with current auth list"""
        for path in self:
            logger.debug(f"Checking {_path} against {path}")
            if _path.startswith(path):
                return True
        return False


def decode_authkey(authkey):
    """Decode authkey content and check digest"""

    digest, data = base64.b64decode(authkey.encode("utf8")).split(b"|", 1)
    assert digest == hmac.new(SECRET_KEY, data, digestmod=hashlib.sha256).digest()
    return json.loads(data.decode("utf-8"))


def encode_authkey(paths):
    """Encode authkey with json inside base64 and add digest"""

    data = json.dumps(paths).encode("utf-8")
    return base64.b64encode(
        hmac.new(SECRET_KEY, data, digestmod=hashlib.sha256).digest() + b"|" + data
    ).decode("utf8")


def check_login(request, path):
    """Helper that returns whether cookie allows current path"""

    logger.debug("checking login...")

    try:
        paths = decode_authkey(request.cookies.get(COOKIE_NAME))
        logger.debug(f"Found cookie with paths: {paths}")
        assert isinstance(paths, list)
    except Exception as e:
        logger.debug(f"Unable to decode cookie : {e}")
        return False

    if AUTH_MODE == "http":
        return Auths(paths).check(path)
    else:
        return True


def nestor_cookie(paths, redir, overlay):
    token = encode_authkey(paths)
    url = redir
    if overlay:
        params = {"redir": redir, "token": token}
        redirect_params = urllib.parse.urlencode(params, safe="")
        url = f"{overlay}?{redirect_params}"

    resp = RedirectResponse(status_code=302, url=url)
    resp.set_cookie(COOKIE_NAME, token, path="/")
    return resp


#
# Routes
#


async def admin(request):
    """POST view, returns url for auth paths from json body
    Need ADMIN_PASSWORD as Auth: header
    Body: ['<path1>', '<path2>', ...]
    """

    if request.method == "POST":
        assert request.headers["X-NESTOR-ADMIN"] == str(ADMIN_PASSWORD)

        urls = await request.json()
        assert isinstance(urls, list)
        authkey = encode_authkey(urls)
        return JSONResponse(
            {
                "authkey": authkey,
                "url": f"/nestor/link?authkey={urllib.parse.quote_plus(authkey)}",
            }
        )


async def link(request):
    """GET view, with autkey as args, and optionally redir"""

    assert "authkey" in request.query_params
    paths = decode_authkey(request.query_params["authkey"])
    return nestor_cookie(
        paths=paths,
        redir=request.query_params.get("redir", default=paths[0]),
        overlay=None,
    )


async def login(request):
    """POST view: Check for login"""

    logger.debug("login request")
    logger.debug("headers : {}".format(request.headers))

    if AUTH_MODE == "http":
        redir = request.headers.get("x-original-uri")
        overlay = None
    else:
        redir = request.query_params.get("redir")
        overlay = request.query_params.get("overlay")
    if request.method == "POST":
        form = await request.form()
        password = form.get("password")
        redir = form.get("redir", redir)
        overlay = form.get("overlay", overlay)

        if password == str(PASSWORD):
            logger.info("allowed access")
            return nestor_cookie(
                ["/"], redir=redir, overlay=overlay
            )  # Default is full access

    if redir and check_login(request, redir):
        return nestor_cookie(["/"], redir=redir, overlay=overlay)

    return templates.TemplateResponse(
        "login.html",
        context={
            "request": request,
            "redir": redir,
            "overlay": overlay,
            "bg_url": BG_URL,
            "login_url": LOGIN_URL,
        },
    )


async def auth_http(request):
    """Auth check view, that will be called by ngx_http_auth_request_module"""
    logger.debug("auth request")
    logger.debug("headers : {}".format(request.headers))

    path = request.headers.get("x-original-uri")
    if path and check_login(request, path):
        return Response("", status_code=200)
    else:
        return Response("", status_code=401)


async def auth_domain(request):
    """Auth check view, that will be called by Traefik forward-auth middleware"""

    logger.debug("auth request")
    logger.debug("headers : {}".format(request.headers))
    logger.debug(
        f"check overlay : {request.headers.get('x-forwarded-uri')} == {OVERLAY_PATH}"
    )

    if check_login(request, None):
        return Response("", status_code=200)
    elif request.headers.get("x-forwarded-uri").split("?")[0] == OVERLAY_PATH:
        url = urllib.parse.urlparse(request.headers.get("x-forwarded-uri"))
        params = urllib.parse.parse_qs(url.query)
        redir = params.get("redir")
        token = params.get("token")
        if redir and token:
            resp = RedirectResponse(url=redir[0], status_code=302)
            resp.set_cookie(COOKIE_NAME, token[0], path="/")
            return resp
        else:
            return "Wrong params"
    else:
        logger.debug("auth : redirect to login")
        proto = request.headers.get("x-forwarded-proto", "")
        host = request.headers.get("x-forwarded-host", "")
        uri = request.headers.get("x-forwarded-uri", "/")
        if proto and host:
            params = {
                "redir": proto + "://" + host + uri,
                "overlay": proto + "://" + host + OVERLAY_PATH,
            }
            redirect_params = "?" + urllib.parse.urlencode(params, safe="")
            return RedirectResponse(
                url=AUTH_DOMAIN_URL + "/login" + redirect_params, status_code=302
            )
        else:
            return "Missing headers"


routes = [
    Route("/login", login, methods=["GET", "POST"]),
]

if AUTH_MODE == "http":
    routes += [
        Route("/auth", auth_http),
        Route("/admin", admin, methods=["POST"]),
        Route("/link", link),
    ]
elif AUTH_MODE == "domain":
    routes += [
        Route("/auth", auth_domain),
    ]

app = Starlette(debug=DEBUG, routes=routes)
