## Create `settings.py`

```python
DEBUG = True
SERVER_NAME = 'hereyt.test:5000'
SQLALCHEMY_DATABASE_URI = 'sqlite:////home/godot/src/estragon/instance/estragon.db'
```

## Create `instance/sites.json`

```json
[
    { "subdomain": "is.godot",
      "title": "Is Godot Here Yet?"
    }
]
```

## Add the top-level domain and subdomains to `/etc/hosts`

```
::1	hereyt.test
::1	is.daniel.hereyt.test
::1	is.skiing.hereyt.test
::1	is.santa.hereyt.test
::1	is.godot.hereyt.test
```

## Run the development server

```bash
ESTRAGON_SETTINGS=$PWD/settings.py ./runserver.py
```

## Hit up <http://hereyt.test:5000/> and away you go.
