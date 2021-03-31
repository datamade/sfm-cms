#!/bin/bash
set -euo pipefail

psql ${DATABASE_URL} -tAX -c "CREATE EXTENSION IF NOT EXISTS postgis"

python manage.py migrate --noinput
python manage.py update_countries_plus
python manage.py collectstatic --noinput
python manage.py makemessages -l fr -l es
python manage.py createcachetable && python manage.py clear_cache

# Load Nigeria data for review apps
if [ "${DO_INITIAL_IMPORT}" = "True" ]; then
    (source .env.import && make -e ng_cc_import) || echo "Failed to do initial import"
fi
