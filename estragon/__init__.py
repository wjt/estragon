import os
from datetime import datetime
from flask import Flask, url_for, abort, g
import simplejson
import warnings
from collections import namedtuple
import functools
import pytz


app = Flask(__name__)
app.config.from_envvar('ESTRAGON_SETTINGS', silent=True)


class Site(namedtuple('Site',
                      ['subdomain', 'title', 'arrival',
                       'no_image', 'no_answer',
                       'yes_template', 'name',
                       'yes_images', 'yes_answer',
                       'favicon_name', 'fireworks',
                       'deets',
                      ])):
    def is_here_yet(self):
        return self.arrival is not None and \
               pytz.UTC.localize(datetime.utcnow()) >= self.arrival


@app.before_request
def before_request():
    g.sites = {}

    try:
        sites_json = os.path.join(app.instance_path, 'sites.json')
        with app.open_resource(sites_json, 'r') as f:
            for site_dict in simplejson.load(f):
                if not isinstance(site_dict, dict):
                    warnings.warn("Malformed site in sites.json: %s" % site_dict)
                    continue

                try:
                    arrival_zone = site_dict.get('arrival_zone')
                    arrival = site_dict.get('arrival')

                    if arrival_zone is not None and arrival is not None:
                        tz = pytz.timezone(arrival_zone)
                        dt = tz.localize(datetime(*arrival))
                    else:
                        dt = None

                    site = Site(
                        subdomain=site_dict['subdomain'],
                        title=site_dict['title'],
                        arrival=dt,
                        no_image=site_dict.get('no_image'),
                        no_answer=site_dict.get('no_answer'),
                        yes_template=site_dict.get('yes_template'),
                        name=site_dict.get('name'),
                        yes_images=site_dict.get('yes_images', []),
                        yes_answer=site_dict.get('yes_answer'),
                        favicon_name=site_dict.get('favicon_name'),
                        fireworks=site_dict.get('fireworks', False),
                        deets=site_dict.get('deets', {}),
                    )
                except KeyError as e:
                    warnings.warn("KeyError when processing '%s': %s" % (site_dict, e))
                    continue

                g.sites[site.subdomain] = site
    except (simplejson.JSONDecodeError, IOError) as e:
        warnings.warn("Couldn't load sites.json: %s" % e)


def get_site(subdomain):
    try:
        return g.sites[subdomain]
    except KeyError:
        abort(404)


def sited(f):
    def _f(subdomain, **kwargs):
        if subdomain is None:
            site = None
        else:
            site = get_site(subdomain)
        return f(site=site, **kwargs)
    return functools.update_wrapper(_f, f)


@app.context_processor
def override_url_for():
    return dict(url_for=dated_url_for)


def dated_url_for(endpoint, **values):
    if endpoint == 'static':
        filename = values.get('filename', None)
        if filename:
            file_path = os.path.join(app.root_path,
                                     endpoint, filename)
            try:
                values['q'] = int(os.stat(file_path).st_mtime)
            except OSError as e:
                warnings.warn(e)
    return url_for(endpoint, **values)


import estragon.views
import estragon.db

# vim: sts=4 sw=4 et
