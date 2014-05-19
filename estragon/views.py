# vim: sts=4 sw=4 et
from estragon import app, sited
import os
from datetime import datetime, timedelta
from flask import render_template, send_from_directory, request, url_for, abort, g, redirect
import random
import pytz


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
                      filename=site.no_image) if site.no_image else None
    # TODO: look just pass 'site' in.
    return render_template(site.yes_template or 'yes.html',
        haircut=haircut,
        pugs=pugs,
        title=site.title,
        answer=site.yes_answer,
        arrival=site.arrival,
        name=site.name,
        fireworks=site.fireworks,
        deets=site.deets)


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


@app.route('/', subdomain='www')
def www():
    return redirect(url_for('.index'), 301)


@app.route('/sites/<subdomain>/img/<path:filename>')
@sited
def img(site, filename):
    # site.subdomain is trusted, so using plain os.path.join is safe.
    return send_from_directory(os.path.join(app.instance_path,
                                            'sites',
                                            site.subdomain,
                                            'img'),
                               filename)
