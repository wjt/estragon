import os
import simplejson
import pytz
from datetime import datetime

from estragon import app, site_images

from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.security import Security, SQLAlchemyUserDatastore, \
    UserMixin, RoleMixin
from sqlalchemy_utils.types.timezone import TimezoneType


# Create database connection object
db = SQLAlchemy(app)


# Define models
roles_users = db.Table('roles_users',
        db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
        db.Column('role_id', db.Integer(), db.ForeignKey('role.id')))


class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True)
    password = db.Column(db.String(255))
    active = db.Column(db.Boolean())
    confirmed_at = db.Column(db.DateTime())
    roles = db.relationship('Role', secondary=roles_users,
                            backref=db.backref('users', lazy='dynamic'))
    foursquare_access_token = db.Column(db.String(255))

    def can_edit(self, site):
        return self.has_role('admin') or \
            self.has_role('edit:' + site.subdomain)


class Site(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subdomain = db.Column(db.String(255), unique=True, nullable=False)
    title = db.Column(db.String(255), nullable=False)

    # TODO: store UTC in the database! What was I thinking, storing local times
    # in the JSON? More human-editable but not a good idea.
    arrival_local = db.Column(db.DateTime, nullable=True)
    arrival_zone = db.Column(TimezoneType(backend='pytz'), nullable=True)

    no_image = db.Column(db.String(255), nullable=True)
    no_answer = db.Column(db.String(255), nullable=True)
    yes_template = db.Column(db.String(255), nullable=True)
    yes_answer = db.Column(db.String(255), nullable=True)
    favicon_name = db.Column(db.String(255), nullable=True)
    fireworks = db.Column(db.Boolean, nullable=False, default=False)

    baby_id = db.Column(db.Integer, db.ForeignKey('baby.id'), nullable=True)
    baby = db.relationship('Baby', uselist=False)

    @property
    def arrival(self):
        if self.arrival_local and self.arrival_zone:
            return self.arrival_zone.localize(self.arrival_local)
        else:
            return None

    @property
    def no_image_url(self):
        return site_images.url(self.no_image) if self.no_image is not None else None

    @property
    def yes_image_urls(self):
        return [ site_images.url(y.filename) for y in self.yes_images ]

    def is_here_yet(self):
        return self.arrival is not None and \
               pytz.UTC.localize(datetime.utcnow()) >= self.arrival


class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)

    site_id = db.Column(db.Integer, db.ForeignKey('site.id'), nullable=False)
    site = db.relationship("Site", backref=db.backref('yes_images', order_by=id))


class Baby(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    weight = db.Column(db.String(255))
    announcement_url = db.Column(db.String(255))


def import_json_site(site_dict):
    if not isinstance(site_dict, dict):
        app.logger.warn("Malformed site in sites.json: %s", site_dict)
        return

    try:
        subdomain = site_dict['subdomain']
        arrival = site_dict.get('arrival')

        def img_filename(basename):
            return os.path.join(subdomain, 'img', basename) if basename else None

        site = Site(
            subdomain=subdomain,
            title=site_dict['title'],
            arrival_local=datetime(*arrival) if arrival is not None else None,
            arrival_zone=site_dict.get('arrival_zone'),
            no_image=img_filename(site_dict.get('no_image')),
            no_answer=site_dict.get('no_answer'),
            yes_template=site_dict.get('yes_template'),
            yes_answer=site_dict.get('yes_answer'),
            favicon_name=site_dict.get('favicon_name'),
            fireworks=site_dict.get('fireworks', False),
        )

        if 'deets' in site_dict:
            deets = site_dict['deets']
            baby = Baby(
                name=deets.get('name'), 
                weight=deets.get('weight'),
                announcement_url=deets.get('announcement_url'),
            )
            db.session.add(baby)
            site.baby = baby

        for yes_image in site_dict.get('yes_images', []):
            img = Image(filename=img_filename(yes_image), site=site)
            db.session.add(img)

        db.session.add(site)
        db.session.commit()
    except KeyError as e:
        app.logger.warn("KeyError when processing '%s': %s", site_dict, e)


@app.before_first_request
def before_first_request():
    """TODO: ugh migrations?"""
    db.create_all()

    if not Site.query.limit(1).all():
        sites_json = os.path.join(app.instance_path, 'sites.json')
        app.logger.debug("Importing sites from {}".format(sites_json))
        try:
            with app.open_resource(sites_json, 'r') as f:
                for site_dict in simplejson.load(f):
                    import_json_site(site_dict)
        except (simplejson.JSONDecodeError, IOError) as e:
            app.logger.warn("Couldn't load sites.json: %s", e)


user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(app, user_datastore)
