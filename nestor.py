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
BG_URL = config("BG_URL", default=None)

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


def check_login(request):
    """Helper that returns whether cookie allows current path"""

    try:
        paths = decode_authkey(request.cookies.get("nestor"))
        logger.debug(f"Found cookie with paths: {paths}")
        assert isinstance(paths, list)
    except Exception as e:
        logger.debug(f"Unable to decode cookie : {e}")
        return False

    return Auths(paths).check(request.headers['X-Original-URI'])


class NestorCookieResponse(RedirectResponse):
    def __init__(self, paths, redir):
        super().__init__(url=redir, status_code=302)
        self.set_cookie("nestor", encode_authkey(paths), path="/")


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
    return NestorCookieResponse(
        paths=paths,
        redir=request.query_params.get("redir", default=paths[0]),
    )


async def login(request):
    """POST view: Check for login"""

    redir = None
    if request.method == "POST":
        form = await request.form()
        password = form.get("password")
        redir = form.get("next", "/")

        if password == str(PASSWORD):
            logging.info("Allowed access")
            return NestorCookieResponse(["/"], redir)  # Default is full access

    if check_login(request):
        return RedirectResponse(url=redir or "/", status_code=302)

    return templates.TemplateResponse(
        "login.html", context={"request": request, "redir": redir, "bg_url": BG_URL}
    )


async def auth(request):
    """Auth check view, that will be called by ngx_http_auth_request_module"""

    if check_login(request):
        return Response("", status_code=200)
    else:
        return Response("", status_code=401)


routes = [
    Route("/login", login, methods=["GET", "POST"]),
    Route("/auth", auth),
    Route("/admin", admin, methods=["POST"]),
    Route("/link", link),
]

app = Starlette(debug=DEBUG, routes=routes)
