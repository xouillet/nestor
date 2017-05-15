#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import mimetypes

from bottle import get, post, run, static_file, request, response, template, redirect

mimetypes.init()

#
# Configuration
#

DATA_DIR = 'data'  # Data containing file to be served
URL_PREFIX = ''  # Prefix for routing url, useful when reverse-proxyfing
INDEX = ['index.html']
SECRET = 'veryverysecret'  # Secret for crypting the cookie
BACKGROUND = ''
PASSWORD = ''

#
# Cookie content
#

class Auths(list):
    def check(self, _path):
        for (level, path) in self:
            if path.rsplit('/', level) == _path.rsplit('/', level):
                return True 
        return False

#
# Main route
#

@post(URL_PREFIX+'<path:path>')
def auth(path):
    password = request.forms.get('password')
    cookie = request.get_cookie("nestor", secret=SECRET) or []
    if password == PASSWORD:
        response.set_cookie("nestor", cookie, secret=SECRET)

    return redirect(path)

@get(URL_PREFIX+'<path:path>')
def main(path):

    cookie = request.get_cookie("nestor", secret=SECRET)
    if not (isinstance(cookie, list) and Auths(cookie).check(path)) \
        and path != BACKGROUND:
        return template('login', background=BACKGROUND)

    if path == '/':
        for path in INDEX:
            if os.path.exists(os.path.join(DATA_DIR, path)):
                break
        else:
            raise Exception("File not found")

    mimetype = mimetypes.guess_type(path)
    return static_file(path, root=DATA_DIR, mimetype=mimetype)

if __name__ == '__main__':
    run(reloader=True)
