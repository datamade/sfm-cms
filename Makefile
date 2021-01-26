SHELL := /bin/bash
USER=datamade
DB=sfm
IMPORT_DB=importer

.PHONY : import_directory
import_directory :
	[[ "$$PWD" =~ sfm-importer ]]

import_db : import_directory
	- dropdb $(IMPORT_DB)
	psql -U postgres -c "CREATE DATABASE $(IMPORT_DB) WITH TEMPLATE $(DB) OWNER $(USER)"


auth_models.json : import_directory
	python manage.py dumpdata auth.User > $@

.PHONY : flush_db
flush_db : import_directory auth_models.json
	python manage.py flush

.PHONY : link_locations
link_locations: import_directory flush_db
	python manage.py link_locations

.PHONY : update_db
update_db : import_directory import_db auth_models.json flush_db link_locations import_google_docs
	python manage.py loaddata auth_models.json
	python manage.py make_materialized_views --recreate
	python manage.py update_countries_plus
	python manage.py rebuild_index --noinput
	python manage.py update_composition_index --recreate
	# psql importer < sfm_pc/management/commands/flush/rename.sql

%_import :
	python manage.py import_google_doc --source_doc_id 1IL4yJMG7KBpOdGZbFsAcGFjSPpVVSNbKLMsRdKC3-XM --doc_id $(GOOGLE_DOC_ID)
	- mv events-errors.csv $*_events-errors.csv
	- mv orgs-errors.csv $*-orgs-errors.csv
	- mv people-errors.csv $*-people-errors.csv

	touch $@

bgd_import : GOOGLE_DOC_ID = 1I5OlOxB_wNdmdQXB6VlV10oz3DDKN2OwXNbcTvtuuXQ
eg_import : GOOGLE_DOC_ID = 12ZYTaP55MZdMBzsH4W3uBwCT6HTKyiUg6110Q5aV4Ck
mx_import : GOOGLE_DOC_ID = 1i5Yd1OVuEFaHDHP_dCXGFeZm0n2lV_HlkaR3fXo-8Ro
my_import : GOOGLE_DOC_ID = 1Txk7_4W3f-c441x0ABKaYHEXGyuro3kasXCQJzlmd8A
ng_import : GOOGLE_DOC_ID = 1HCljLKFgGwMYdDK9YcOSYmLiTXiXBuXs-qaFEU7o3BM
ph_import : GOOGLE_DOC_ID = 1yQ37fGr4FrULKN3Iw1p4UOS00_jxCy3Dox19yOrtNto
rwa_import : GOOGLE_DOC_ID = 150zJztdYScI1wnEcIdrhsh8TZ6tkgPZM9j3k6O_2nBU
sa_import : GOOGLE_DOC_ID = 1jv_tsPjeovxAd6yPdQ0TuTVzPRRNFDwCu51cv66etXk
ug_import : GOOGLE_DOC_ID = 14HykmygxEriywmgJDzzZAj-jY9z2bLoDrPOieRvpprE

# Get files from https://drive.google.com/drive/u/1/folders/1WCeodk3DZ5zzNkIrJ7h_a9lBb5THUDsu
.PHONY : import_google_docs
import_google_docs : bgd_import mx_import	\
	             ng_import ph_import rwa_import sa_import	\
	             ug_import eg_import my_import


.PHONY : clean
clean :
	- rm auth_models.json
	rm bgd_import eg_import mx_import my_import ng_import	\
           ph_import rwa_import sa_import ug_import

.PHONY : search
search : 
	python manage.py rebuild_index --noinput
	python manage.py update_composition_index --recreate


osm :
	python manage.py import_osm --download_only
	python manage.py import_osm --import_only
	python manage.py link_locations


make_search_index : import_google_docs
