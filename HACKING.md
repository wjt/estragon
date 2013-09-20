## Create `settings.py`

```python
DEBUG = True
SERVER_NAME = 'hereyt.test:5000'
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
127.0.0.1	hereyt.test
127.0.0.1	is.daniel.hereyt.test
127.0.0.1	is.skiing.hereyt.test
127.0.0.1	is.santa.hereyt.test
127.0.0.1	is.godot.hereyt.test
```

## Run the development server

```bash
ESTRAGON_SETTINGS=settings.py python estragon.py
```

## Hit up <http://hereyt.test:5000/> and away you go.
