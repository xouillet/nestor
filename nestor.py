#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import base64
import hashlib
import hmac
import json
import logging

from starlette.applications import Starlette
from starlette.config import Config
from starlette.datastructures import Secret
from starlette.responses import RedirectResponse, Response
from starlette.routing import Route
from starlette.templating import Jinja2Templates


templates = Jinja2Templates(directory="views")

logger = logging.getLogger("uvicorn")
logger.setLevel(logging.DEBUG)

# Config

config = Config(".env")
SECRET_KEY = config("SECRET_KEY").encode("utf8")
PASSWORD = config("PASSWORD", cast=Secret)
BG_URL = config("BG_URL", default=None)

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
        """" Checks that _path is allowed with current auth list """
        for path in self:
            if _path.startswith(path):
                return True
        return False


def decode_cookie(cookie):
    """ Decode cookie content and check digest """

    digest, data = base64.b64decode(cookie.encode("utf8")).split(b"|", 1)
    assert digest == hmac.new(SECRET_KEY, data, digestmod=hashlib.sha256).digest()
    return json.loads(data.decode("utf-8"))


def encode_cookie(cookie):
    """ Encode cookie with json inside base64 and add digest """
    data = json.dumps(cookie).encode("utf-8")
    return base64.b64encode(
        hmac.new(SECRET_KEY, data, digestmod=hashlib.sha256).digest() + b"|" + data
    ).decode("utf8")


def check_login(request):
    """ Helper that returns whether cookie allows current path """

    try:
        cookie = decode_cookie(request.cookies.get("nestor"))
        assert isinstance(cookie, list)
    except Exception as e:
        logger.debug(f"Unable to decode cookie : {e}")
        return False

    return Auths(cookie).check(request.url.path)


#
# Routes
#


async def login(request):
    """ POST view: Check for login """

    redir = None
    if request.method == "POST":
        form = await request.form()
        password = form.get("password")
        redir = form.get("next", "/")
        try:
            cookie = decode_cookie(request.cookies.get("nestor"))
        except Exception:
            cookie = []

        if password == str(PASSWORD):
            logging.info("Allowed access")
            cookie.append("")
            response = RedirectResponse(url=redir, status_code=302)
            response.set_cookie("nestor", encode_cookie(cookie), path="/")
            return response

    if check_login(request):
        return RedirectResponse(url=redir or "/", status_code=302)

    return templates.TemplateResponse(
        "login.html", context={"request": request, "redir": redir, "bg_url": BG_URL}
    )


async def auth(request):
    """ Auth check view, that will be called by ngx_http_auth_request_module """

    if check_login(request):
        return Response("", status_code=200)
    else:
        return Response("", status_code=401)


routes = [
    Route("/login", login, methods=["GET", "POST"]),
    Route("/auth", auth),
]

app = Starlette(debug=True, routes=routes)
