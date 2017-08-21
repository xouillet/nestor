#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import mimetypes
import random
import json
import yaml

from bottle import default_app, run, \
                   get, post, \
                   static_file, template, redirect, \
                   request, response

mimetypes.init()
mimetypes.add_type('text/css', 'css') 

#
# Configuration
#

class ConfigDict(dict):
    def __init__(self, *args, **kwargs):
        super(ConfigDict, self).__init__(*args, **kwargs)
        self.__dict__ = self

# Default config

config = ConfigDict({'data_dir': 'data', # Directory containing files to be served
                     'url_prefix': '', # Prefix for routing url, useful when reverse-proxyfing
                     'secret': None, # Secret for crypting the cookie, should be overwritten in config
                     'index': ['index.html'], # List of files to try when path is a directory
                     'allowed_paths': [], # Always allowed paths, typically static such as js/css
                     'background_path': None, # Path (relative to url_prefix) containing background images to use with login
                     'password': None # Password to access site
                   })

yaml_config_path = os.environ.get('NESTOR_CONFIG')
if yaml_config_path:
    with open(yaml_config_path, 'r') as yaml_config:
        config.update(yaml.load(yaml_config))

config_json = os.environ.get('NESTOR_CONFIG_JSON')
if config_json:
    config.update(config_json)

# If background_path is present, add it to allowed_paths
if config.background_path:
    config.background_path = config.background_path.strip('/')
    config.allowed_paths.append(config.background_path)

# Strip / on url_prefix and background_path
config.url_prefix = config.url_prefix.rstrip('/')

# Some checks
if config.secret is None:
    raise Exception("Please define a secret")

#
# Cookie content
#
class Auths(list):
    """ This class herits from list to add the check method 
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

#
# Main route
#

@post(config.url_prefix+'<path:path>')
def auth(path):
    """ POST view: Check for login """

    password = request.forms.get('password')
    cookie = request.get_cookie("nestor", secret=config.secret) or []
    if password == config.password:
        cookie.append('/')
        response.set_cookie("nestor", cookie, secret=config.secret, path=config.url_prefix+'/')

    return redirect(config.url_prefix+path)

@get(config.url_prefix+'<path:path>')
def main(path):
    """ Main view: Check cookie and serve file """

    cookie = request.get_cookie("nestor", secret=config.secret)

    for allowed_path in config.allowed_paths:
        if path[1:].startswith(allowed_path):
            break
    else:
        if not (isinstance(cookie, list) and Auths(cookie).check(path)):
            if config.background_path:
                background = os.path.join(config.url_prefix, config.background_path, random.choice(os.listdir(os.path.join(config.data_dir, config.background_path))))
            else:
                background=''
            return template('login', background=background)

    if path.endswith('/'):
        for index in config.index:
            if os.path.exists(os.path.join(config.data_dir, path.strip('/'), index)):
                path = path+index
                break
        else:
            raise Exception("File not found")

    mimetype = mimetypes.guess_type(path)[0]
    return static_file(path, root=config.data_dir, mimetype=mimetype)

if __name__ == '__main__':
    run(reloader=True, host='0.0.0.0', port=7666, debug=True)
else :
    app = application = default_app()
