# Who Was In Command [![Build Status](https://github.com/security-force-monitor/sfm-cms/actions/workflows/main.yml/badge.svg?branch=master)](https://github.com/security-force-monitor/sfm-cms/actions?query=branch%3Amaster)

- [Dependencies](#dependencies)
- [Development](#development)
- [Translations](#translations)
- [Tests](#tests)
- [Using the Google Drive import script](#using-the-google-drive-import-script)

**See also:**

- [Who Was In Command: Getting started with development](DEVELOPMENT.md)
- [Security Force Monitor: Research Handbook](https://help.securityforcemonitor.org/en/latest/index.html)

## Dependencies

* [Docker](https://www.docker.com/get-started)

## Development

### Basic setup

Clone the repo:

    git clone git@github.com:security-force-monitor/sfm-cms.git
    cd sfm-cms

Next, create a local `.env` file.

    cp .env.example .env

The example `.env` file does not contain values for third-party integrations
with AWS, Google Maps, or Sentry. If you're indoctrinated into the DataMade
LastPass, you can find working values for these settings under `WWIC .env Secrets`.
Otherwise, you'll need to create your own AWS credentials, Google Maps key,
and/or Sentry DSN to enable these services in local development.

Finally, build the application:

    docker-compose build

### Load data

Once you've built the app, there are two ways that you can load data into your database.

#### Option 1: Load a database dump

The standard data loading process for the app can take many hours to complete. If you're working with a developer who already has a database set up, you can save time by having them make a dump of their database for you:

    docker-compose run --rm app pg_dump -Fc -h postgres -U postgres -d sfm -O > sfm_empty.dump

Then, load this dump into your own database:

    docker-compose run --rm app pg_restore -h postgres -U postgres -d sfm -O sfm.dump

Once the dump has been restored, move on to the step `Set up the search index` below.

#### Option 2: Load data via management commands

##### Location data

The standard way to load data into the app is to use the app's management commands for loading data. Start by updating the `Countries` models:

    docker-compose run --rm app ./manage.py update_countries_plus

OSM data is provided by the SFM team in a special GeoJSON format. You can import
location data from a local file by running the `import_locations` command
directly –

    # import fixtures/locations.geojson
    docker-compose run --rm app ./manage.py import_locations

    # import geojson file from arbitrary path
    docker-compose run --rm app .manage.py import_locations --location_file path/to/your/file

– or, you can pass an optional `--location_file_id` argument to `import_google_docs`
to retrieve the specified file from Google Drive and import it before importing
entity data. (Read on for instructions!)

##### Entity data

The `import_google_docs` expects to find credentials for the Google
Sheets and Google Drive APIs in `sfm_pc/management/commands/credentials.json`.

If a file exists at that path, the script will use it. Otherwise, it will
attempt to retrieve a remote copy of our API credentials from S3. Obviously,
these credentials are not publicly accessible. `boto3` checks for the `AWS_*`
environment variables to authenticate requests. If you're indoctrinated into
the DataMade LastPass, you can find working values for these settings under
`WWIC .env Secrets`. Simply paste them into your `.env` file.

If you are not on the team, enable the Google Sheets and Google Drive APIs in
[the Google API Console](https://console.developers.google.com/apis/library), then
create a service account to access them. [This blog post](https://www.twilio.com/blog/2017/02/an-easy-way-to-read-and-write-to-a-google-spreadsheet-in-python.html)
provides a helpful walkthrough! Be sure to save your credentials in
`sfm_pc/management/commands/credentials.json` and give your service account
access to the correct files before you run `import_google_docs`.

Finally, import entity data from Google Drive:

    # Import entity data from default files
    docker-compose run --rm app make import_google_docs

    # Import entity data from specified files
    docker-compose run --rm app python manage.py import_google_doc --doc_id ${SOME_ID} --source_doc_id ${SOME_ID} --location_doc_id ${SOME_ID}

See [Using the Google Drive import script](#using-the-google-drive-import-script)
for more detailed information about these management commands.

### Set up the search index

Build and start the Docker image for the Solr server:

    docker-compose up --build solr

Open up another shell and create the search index:

    docker-compose run --rm app ./manage.py update_index
    docker-compose run --rm app ./manage.py update_composition_index

### Run the app

    docker-compose up

Open http://localhost:8000/ to browse your shiny new website! New to WWIC
development? See [Getting started with development](DEVELOPMENT.md)
for helpful information about how the app is organized, as well as tips and tricks.

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
docker-compose run --rm app ./manage.py makemessages -l es
docker-compose run --rm app ./manage.py makemessages -l fr
```

This command generates a `.po` file for each language. Rosetta facilitates the editing and compiling of these files. Go to `/rosetta/`, and view the snippets of code, requiring translation, organized by language. Then, translate some text, click "Save and translate next block," and Rosetta compiles the code into Django-friendly translations.

## Tests

Run all tests from the root folder:

```
docker-compose -f docker-compose.yml -f tests/docker-compose.yml run --rm app
```

You can also run a collection of tests, like so:

```
docker-compose -f docker-compose.yml -f tests/docker-compose.yml run --rm app pytest tests/test_person.py
```

Or run a single test, like so:

```
docker-compose -f docker-compose.yml -f tests/docker-compose.yml run --rm app pytest tests/test_person.py::test_no_existing_sources
```

## Using the Google Drive import script

The script to import data from Google Drive exists as a management command
within the `sfm_pc` directory of this project predictably called
`import_google_doc`. As of February 2021, spreadsheets to be imported must follow
this format: https://docs.google.com/spreadsheets/d/1-U_pVNDWFIlG8jLZLVujmV_FZ0H4IsbtfCeRiM8HeNQ/edit?usp=sharing

### Import data from Google Drive

The data that powers WWIC is imported from three key documents:

1. A "sources" spreadsheet applicable to the entire import
2. A "locations" GeoJSON file containing all implicated OSM data for entities
in a particular country
3. A "data" spreadsheet containing organization, person, and event entity data
for a particular country

An import involves running the import command against a set of source, location,
and data documents that represent either data for a new country, or updated data
for an existing country.

The following sections explain our process for running these imports locally
and on live instances of WWIC.

#### Local import

When performing an import of new data, the first step should always be to
test the import in your development environment using the `import_google_doc`
management command.

This management command relies upon a [Service
Account](https://cloud.google.com/iam/docs/understanding-service-accounts)
having access to the spreadsheet. This service account is managed under the
`SFM - Data Import` project in the Google API Console.

Working credentials for our service account live in S3. Obviously, these
credentials are not publicly accessible. `boto3` checks for the `AWS_*`
environment variables to authenticate requests. If you're indoctrinated into
the DataMade LastPass, you can find working values for these settings under
`WWIC .env Secrets`. Simply paste them into your `.env` file to automatically
retrieve the credentials during import.

If you aren't in the DataMade LastPass, create your own service account,
then copy the credentials to `sfm_pc/management/commands/credentials.json`,
and the import will use the existing file rather than retrieving credentials
from S3.

Next, you will need to share the files to be imported with the `client_email`
email address in your credentials file. (For DataMade, it's
`data-importer@sfm-data-import.iam.gserviceaccount.com`.)
To grant the service account access to the documents, navigate to
the `Share` button on each document and grant the `client_email` of the service
account "Read" access. (You can also select multiple files, e.g., in the same
Drive, and update the sharing settings in one go.)

As of February 2021, SFM has shared with us a CSV file of source, location,
and data document IDs, as well as the country code they pertain to. This CSV
lives at [`fixtures/import_docket.csv`](fixtures/import_docket.csv). If for
some reason you need to retrieve document IDs yourself, you can find the ID by
opening the document in your browser and copying the ID from the URL in your
address bar:

```
https://docs.google.com/spreadsheets/d/<doc id (very long hash looking thing)>/edit
```

The Makefile contains recipes to import all of the data on the docket, import
the first country in the CSV, or import a particular country by its country code.

```bash
# Import everything on the docket
docker-compose --env-file .env.import run --rm app make -e import_docket_import

# Import the first country on the docket
docker-compose --env-file .env.import run --rm app make -e next_import

# Import a particular country or countries
docker-compose --env-file .env.import run --rm app make -e ${COUNTRY_CODE}_cc_import [ ${COUNTRY_CODE}_cc_import ... ]
```

Of course, you can also run the import commands directly:

```bash
docker-compose run --rm app python manage.py import_google_docs \
    --source_doc_id <some id> \
    --location_doc_id <some id> \
    --doc_id <some id>
```

If the importer raises warnings during the import, it will log them to logfiles
following the logfile pattern `${country_code}_${entity_type}_errors`. Once the
import is complete, take a look at your repo to check to see if the importer
generated any of these warning logfiles. If it did, send these logfiles to the
SFM team so they can make necessary adjustments to the data. We typically delete
logfiles between import runs, since the importer will append to a logfile if one
exists already.

Once your import has completed with error, refresh the derived data views and
confirm that nothing breaks:

```
docker-compose run --rm app python manage.py make_materialized_views --recreate
docker-compose run --rm app ./manage.py rebuild_index --noinput
docker-compose run --rm app ./manage.py update_composition_index --recreate
```

#### Importing data to a live site

Once you've tested an import of a new dataset locally, you're ready to run the import
on a live instance.

Since all live instances should already have credentials, you should be ready to run
a live import using the Make recipes:

```
tmux new -s fresh-import
sudo su - datamade
workon sfm
cd ~/sfm-cms

# Import everything on the docket
make import_docket_import

# Import a particular country or countries
make -e ${COUNTRY_CODE}_cc_import [ ${COUNTRY_CODE}_cc_import ... ]

python manage.py make_materialized_views --recreate
python manage.py rebuild_index --noinput
python manage.py update_composition_index --recreate
```

#### Importing all data without disrupting servers

If need to fully rerun the entire WWIC import for all countries without
disrupting a live instance, the Makefile includes a recipe for doing just that.

On every deploy, our build scripts create a separate directory, `sfm-importer`. This
directory is a copy of the app that uses a separate database with the name `importer`.
We'll use this database for our imports, so that the server can keep on serving
data normally during that process (which can take several hours!)

To perform a new import, start by creating a tmux session so your work doesn't
get interrupted. Then, activate the virtualenv for the project, `cd` into the
appropriate directory, and fire the recipe to build a fresh database:

```
tmux new -s fresh-import
sudo su - datamade
workon sfm
cd ~/sfm-importer
make recreate_db
```

Finally, switch the `sfm` and `importer` databases:

```
# Renames the databases in a transaction -- the app doesn't need to stop
psql postgres < sfm_pc/management/commands/flush/rename.sql
```

Presto! A fresh import, with no server downtime.
