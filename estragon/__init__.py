import os
from flask import Flask, url_for
import warnings
import functools


app = Flask(__name__)
app.config.from_envvar('ESTRAGON_SETTINGS', silent=True)


def sited(f):
    def _f(subdomain, **kwargs):
        if subdomain is None:
            site = None
        else:
            site = db.Site.query.filter_by(subdomain=subdomain).first_or_404()
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
