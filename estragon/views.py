# vim: sts=4 sw=4 et fileencoding=utf-8
from estragon import app, sited, site_images
import os
import re
from datetime import datetime, timedelta
from flask import render_template, send_from_directory, request, url_for, abort, redirect, flash, session
import random
import pytz
from flask.ext.security import login_required, current_user, login_user
from flask.ext.security.utils import url_for_security, get_post_login_redirect
from estragon.db import db, Site, Baby, user_datastore
from flask.ext.wtf import Form
from flask.ext.wtf.file import FileField, FileAllowed
from wtforms.fields import SelectField, StringField
from wtforms.fields.html5 import DateTimeLocalField
from wtforms.validators import InputRequired, Optional, Length, ValidationError
from wtforms_components import Unique, If
from wtforms_alchemy import model_form_factory, ModelFormField
ModelForm = model_form_factory(Form)


def no(site):
    if request.args.get('test') is not None:
        date = pytz.UTC.localize(datetime.utcnow()) + timedelta(0, 10)
    else:
        date = site.arrival

    return render_template('no.html',
        site=site,
        arrival=date,
        no_image=site.no_image_url,
        title=site.title,
        answer=site.no_answer,
        )


def yes(site):
    if request.args.get('test') is None and not site.is_here_yet():
        abort(403)

    pugs = site.yes_image_urls
    random.shuffle(pugs)
    haircut = site.no_image_url
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


class BabbyForm(ModelForm):
    class Meta:
        model = Baby


# Not convinced that ModelForm is a net win
class EditSiteForm(ModelForm):
    class Meta:
        model = Site
        exclude = ['subdomain']

    title = StringField(
        u'Title',
        description=u'Is My Novelty Domain Here Yet?',
        validators=[
            InputRequired(),
            Length(min=1, max=255),
        ])
    # TODO: Optional?
    arrival_local = DateTimeLocalField(
        u'Countdown time',
        format=u'%Y-%m-%dT%H:%M',
        validators=[
            Optional(),
        ])
    # TODO: sensible default, If(arrival_local, required)
    arrival_zone = SelectField(
        u'Countdown timezone',
        validators=[
            If(lambda form, field: form.arrival_local.data,
               InputRequired(),
               message=u'A timezone is required if you specify an arrival time'),
        ],
        choices=[
            ('', u'(n/a)')
        ] + [
            (x, x.replace('_', ' '))
            for x in pytz.common_timezones if x != 'UTC'
        ])
    no_image = FileField(
        u'Image',
        validators=[
            Optional(),
        ])
    no_answer = StringField(
        u'Pre-deadline title',
        description=u'Not yet…',
        validators=[
            Optional(),
            Length(max=255),
        ])
    yes_answer = StringField(
        u'Post-deadline title',
        description=u'Yes!!!',
        validators=[
            Optional(),
            Length(max=255),
        ])
    # baby = ModelFormField(BabbyForm)

    def validate_subdomain(form, field):
        for label in field.data.split(r'.'):
            if len(label) == 0:
                raise ValidationError('no empty labels please')
            if len(label) > 63:
                raise ValidationError('labels cannot be longer than 63 octets')
            if not re.match(r'[-a-zA-Z0-9]+', label):
                raise ValidationError('''labels may only contain alphanumeric characters and
                                      hyphens. do your own punycode please''')
            if label.startswith('-') or label.endswith('-'):
                raise ValidationError('Labels may not start or end with hyphens')

    def populate_obj(self, site):
        del self.no_image
        super(ModelForm, self).populate_obj(site)

        no_image = request.files.get('no_image', None)
        if no_image:
            folder = os.path.join(site.subdomain, 'img')
            filename = site_images.save(no_image, folder=folder)
            site.no_image = filename


class NewSiteForm(EditSiteForm):
    class Meta:
        model = Site
        exclude = []

    subdomain = StringField(
        u'Subdomain',
        description=u'is.my.novelty.domain',
        validators=[
            InputRequired(),
            Length(min=1, max=255 - len('.' + (app.config['SERVER_NAME'] or ''))),
            Unique(Site.subdomain, get_session=lambda: db.session),
        ])


@app.route('/edit/<subdomain>', methods=['GET', 'POST'])
@login_required
@sited
def edit(site):
    if not current_user.can_edit(site):
        abort(403)

    form = EditSiteForm(obj=site)
    if form.validate_on_submit():
        form.populate_obj(site)
        db.session.commit()
        return redirect(url_for('.edit', subdomain=site.subdomain))

    return render_template(
        'edit.html',
        site=site,
        form=form,
        action=url_for('.edit', subdomain=site.subdomain),
    )


@app.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    form = NewSiteForm()
    if form.validate_on_submit():
        site = Site()
        db.session.add(site)
        form.populate_obj(site)
        # FIXME: rate-limit?
        role = user_datastore.find_or_create_role('edit:' + site.subdomain)
        user_datastore.add_role_to_user(current_user, role)
        db.session.commit()
        return redirect(url_for('.edit', subdomain=site.subdomain))

    return render_template(
        'edit.html',
        site=None,
        form=form,
        action=url_for('.new'),
    )



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
        # TODO: stuff next into the session, pull it back out here
        declared = session.pop('FOURSQUARE_POST_LOGIN_NEXT', None)
        redirect_to = get_post_login_redirect(declared=declared)
        return redirect(redirect_to, 307)
    else:
        auth_uri = client.oauth.auth_url()
        session['FOURSQUARE_POST_LOGIN_NEXT'] = request.args.get('next')
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
