# Security Force Monitor: Backend

## OS Level dependencies

* Python 3.5
* PostgreSQL 9.4+
* PostGIS
* osm2pgsql

## Development

    mkvirtualenv sfm
    git clone git@github.com:security-force-monitor/sfm-cms.git
    cd sfm-cms

Install the requirements:

    pip install -r requirements.txt

Create a local settings file:

    cp sfm_pc/settings_local.py.example sfm_pc/settings_local.py

Replace OSM_API_Key in `settings_local.py` with a Wambacher cliKey. Generate a key [here](https://wambachers-osm.website/boundaries/) by enabling OAuth, selecting a boundary, checking CLI, hitting Export, and looking at the generated URL.  

Create a database:

    createdb sfm
    psql sfm -c "CREATE EXTENSION postgis;"
    ./manage.py migrate --noinput

Load static data:

```
# Load fixtures for Violation Types, Organization classification types, and countries
./manage.py loaddata violation_types
./manage.py loaddata classification_types
./manage.py update_countries_plus
```

Create Materialized Views for global search, and looking up a Geoname object based upon a geoname id:

    python manage.py import_osm
    python manage.py import_google_doc
    python manage.py make_flattened_views

You're almost done! The last step is to get solr and the search index setup. Start by following the instructions in [SOLR-SETUP.md](https://github.com/security-force-monitor/sfm-cms/blob/master/SOLR-SETUP.md) to get solr installed and running on your machine.

Then, create the search index:

    python manage.py make_search_index

Create an admin user:

    ./manage.py createsuperuser

Start the web server:

    ./manage.py runserver

Open http://127.0.0.1:8000/ and sign in with your email and password.

## Translations

We use [Django translation](https://docs.djangoproject.com/en/1.11/topics/i18n/translation/) together with [Rosetta](https://github.com/mbi/django-rosetta) and [django-complex-fields](https://github.com/security-force-monitor/complex_fields).

Template translations appear inside `trans` tags, like so:

```python
{% trans "Countries" %}
```

Model field and form error translations appear inside `_()` hooks, as such:

```python
from django.utils.translation import ugettext as _

...

field_name = _("End date")
```

This nomenclature signals that the text can be translated into the user's specified language. But first, someone with language expertise must provide the appropriate translation. Happily, Django can extract all translatable strings into a message file:

```bash
django-admin.py makemessages -l es
django-admin.py makemessages -l fr
```

This command generates a `.po` file for each language. Rosetta facilitates the editing and compiling of these files. Go to `/rosetta/`, and view the snippets of code, requiring translation, organized by language. Then, translate some text, click "Save and translate next block," and Rosetta compiles the code into Django-friendly translations.

## Importing new data without disrupting servers

This repo has a system for performing fresh data imports without disrupting
the normal activity of the server.

On every deploy, our build scripts create a separate directory, `sfm-importer`. This
directory is a copy of the app that uses a separate database with the name `importer`.
We'll use this database for our imports, so that the server can keep on serving
data normally during that process (which can take up to 8 hours!)

To perform a new import, start by creating a tmux session so your work doesn't
get interrupted. Then, activate the virtualenv for the project and change to the
`sfm-importer` directory:

```
tmux new -s fresh-import

# remember to switch to the correct user instead of <user>
sudo su - <user>
workon sfm
cd sfm-importer
```

Although the `importer` database should already be a copy of the production
database, you can redo the copy to be safe:

```
dropdb importer

# Add our typical user here instead of <user>
psql -U postgres -c "CREATE DATABASE importer WITH TEMPLATE sfm OWNER <user>"
```

If you want to drop existing tables containing data in the database, you can
use a SQL script that we have for that purpose:

```
psql importer < sfm_pc/management/commands/flush/flush.sql

# Refresh the country data, which gets dropped in flush.sql
python manage.py update_countries_plus
```

Next, perform the import as normal. This can take a long time, so go get some
fresh air.

```
python manage.py import_google_doc
python manage.py make_flattened_vies --recreate
python manage.py update_search_index
```

Finally, switch the `sfm` and `importer` databases:

```
# Renames the databases in a transaction -- the app doesn't need to stop
psql importer < sfm_pc/management/commands/flush/rename.sql
```

Presto! A fresh import, with no server downtime.
