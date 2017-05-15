#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import mimetypes

from bottle import default_app, run, \
                   get, post, \
                   static_file, template, redirect, \
                   request, response

mimetypes.init()
mimetypes.add_type('text/css', '.css') 

#
# Configuration
#

DATA_DIR = os.environ.get('NESTOR_DATADIR', 'data')  # Data containing file to be served
URL_PREFIX =  os.environ.get('NESTOR_PREFIX', '')  # Prefix for routing url, useful when reverse-proxyfing
INDEX = ['index.html']
SECRET = 'seikaGh7eeK4satuFae0yohbnai4pieYAhH1thai'  # Secret for crypting the cookie
BACKGROUND = os.environ.get('NESTOR_BACKGROUND', '')
PASSWORD = os.environ.get('NESTOR_PASSWORD')

#
# Cookie content
#
def truncate_path(path, level):
    return '/'.join(path.split('/')[:level])

class Auths(list):
    def check(self, _path):
        for (level, path) in self:
            if truncate_path(path, level) == truncate_path(_path, level):
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
        cookie.append((0, '/'))
        response.set_cookie("nestor", cookie, secret=SECRET)

    return redirect(URL_PREFIX+path)

@get(URL_PREFIX+'<path:path>')
def main(path):

    cookie = request.get_cookie("nestor", secret=SECRET)
    if not (isinstance(cookie, list) and Auths(cookie).check(path)) \
        and URL_PREFIX+path != BACKGROUND:
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
else :
    app = application = default_app()
