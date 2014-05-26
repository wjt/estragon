# vim: sts=4 sw=4 et
from estragon import app, sited
import os
from datetime import datetime, timedelta
from flask import render_template, send_from_directory, request, url_for, abort, redirect, flash
import random
import pytz
from flask.ext.security import login_required, current_user, login_user
from flask.ext.security.utils import url_for_security
from estragon.db import Site, user_datastore


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

    pugs = [ url_for('img', subdomain=site.subdomain, filename=img.filename)
             for img in site.yes_images
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
        fireworks=site.fireworks,
        baby=site.baby)


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
    sites = Site.query.order_by(Site.title)
    return render_template('index.html', sites=sites)


@app.route('/you')
@login_required
def you():
    return render_template('you.html', you=current_user)


@app.route('/', subdomain='www')
def www():
    return redirect(url_for('.index'), 301)


@app.route('/login/foursquare')
def foursquare_login():
    import foursquare
    client = foursquare.Foursquare(
        client_id=app.config['FOURSQUARE_CLIENT_ID'],
        client_secret=app.config['FOURSQUARE_CLIENT_SECRET'],
        redirect_uri=url_for('.foursquare_login', _external=True))

    if 'error' in request.args:
        flash('Foursquare login failed: {}'.format(request.args['error']))
        return redirect(url_for_security('login'), 307)
    elif 'code' in request.args:
        access_token = client.oauth.get_token(request.args['code'])
        client.set_access_token(access_token)
        foursquare_user = client.users()

        try:
            email = foursquare_user['user']['contact']['email']
        except KeyError:
            app.logger.debug(
                "Failed to pluck email from {}".format(foursquare_user),
                exc_info=True)
            flash("Couldn't determine your email address from Foursquare")
            return redirect(url_for_security('login'), 307)

        user = user_datastore.find_user(email=email)
        if user is None:
            user = user_datastore.create_user(email=email)
        if user.foursquare_access_token != access_token:
            user.foursquare_access_token = access_token

        user_datastore.commit()
        login_user(user)
        return redirect(url_for('.you'), 307)
    else:
        auth_uri = client.oauth.auth_url()
        return redirect(auth_uri, 307)


@app.route('/sites/<subdomain>/img/<path:filename>')
@sited
def img(site, filename):
    # site.subdomain is trusted, so using plain os.path.join is safe.
    return send_from_directory(os.path.join(app.instance_path,
                                            'sites',
                                            site.subdomain,
                                            'img'),
                               filename)
