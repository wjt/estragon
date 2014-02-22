import os
from datetime import datetime, timedelta
from flask import Flask, render_template, send_from_directory, request, url_for, abort, g
import simplejson
import random
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
                       'favicon_name', 'fireworks'])):
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

def no(site):
    if request.args.get('test') is not None:
        date = pytz.UTC.localize(datetime.utcnow()) + timedelta(0, 10)
    else:
        date = site.arrival

    return render_template('no.html',
        site=site,
        arrival=date,
        no_image=url_for('img',
                         subdomain=site.subdomain,
                         filename=site.no_image),
        title=site.title,
        answer=site.no_answer,
        )

def yes(site):
    if request.args.get('test') is None and not site.is_here_yet():
        abort(403)

    pugs = [ url_for('img', subdomain=site.subdomain, filename=filename)
             for filename in site.yes_images
           ]
    random.shuffle(pugs)
    haircut = url_for('img',
                      subdomain=site.subdomain,
                      filename=site.no_image)
    return render_template(site.yes_template or 'yes.html',
        haircut=haircut,
        pugs=pugs,
        title=site.title,
        answer=site.yes_answer,
        arrival=site.arrival,
        name=site.name,
        fireworks=site.fireworks)

# By not decorating the functions with @sited directly, root() can pass a Site
# rather than having to go back to a subdomain.
app.add_url_rule('/no', 'no', sited(no), subdomain='<subdomain>')
app.add_url_rule('/yes', 'yes', sited(yes), subdomain='<subdomain>')

@app.route('/', subdomain='<subdomain>')
@sited
def root(site):
    if site.arrival is None and site.no_image is None:
        return render_template(
            'godot.html',
            title=site.title,
            answer=site.no_answer)
    elif site.is_here_yet():
        return yes(site)
    else:
        return no(site)

@app.route('/favicon.ico', subdomain='<subdomain>')
@app.route('/favicon.ico', defaults={'subdomain': None})
@sited
def favicon(site):
    if site is not None and site.favicon_name is not None:
        return img(subdomain=site.subdomain, filename=site.favicon_name)

    return send_from_directory(os.path.join(app.root_path, 'static', 'img'),
                               'stock_appointment-reminder.ico',
                               mimetype='image/vnd.microsoft.icon')

@app.route('/')
def index():
    sites = g.sites.values()
    sites.sort(key=lambda s: s.title)
    return render_template('index.html', sites=sites)

@app.route('/sites/<subdomain>/img/<path:filename>')
@sited
def img(site, filename):
    # site.subdomain is trusted, so using plain os.path.join is safe.
    return send_from_directory(os.path.join(app.instance_path,
                                            'sites',
                                            site.subdomain,
                                            'img'),
                               filename)

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

if __name__ == '__main__':
    app.run()

# vim: sts=4 sw=4 et
