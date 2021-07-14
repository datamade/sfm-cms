from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.backends import ModelBackend
from django.utils import translation

from haystack import connections
from haystack.backends.solr_backend import SolrEngine, SolrSearchBackend, SolrSearchQuery
from haystack.constants import DEFAULT_ALIAS


class EmailAuthBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None):

        try:
            user = User.objects.get(email=username)
        except User.DoesNotExist:
            return None

        if user.check_password(password):
            return user

        return None


def get_using(language, alias=DEFAULT_ALIAS):
    new_using = alias + "_" + language
    using = new_using if new_using in settings.HAYSTACK_CONNECTIONS else alias
    return using


class MultilingualSolrSearchBackend(SolrSearchBackend):

    def update(self, index, iterable, commit=True, multilingual=True):
        '''
        ar is being updated twice

        Indexing 13 persons
          indexed 1 - 13 of 13 (worker PID: 1).
        default_ar
        en
        en
        en
        en
        en
        en
        en
        en
        en
        en
        en
        en
        en
        Indexing 13 persons
          indexed 1 - 13 of 13 (worker PID: 1).
        default
        en
        en
        en
        en
        en
        en
        en
        en
        en
        en
        en
        en
        en
        default_ar
        ar
        ar
        ar
        ar
        ar
        ar
        ar
        ar
        ar
        ar
        ar
        ar
        ar
        '''
        if multilingual:
            initial_language = translation.get_language()[:2] if translation.get_language() else 'en'
            # retrieve unique backend name
            backends = []
            for language, __ in settings.LANGUAGES:
                using = get_using(language, alias=self.connection_alias)
                # Ensure each backend is called only once
                if using in backends:
                    continue
                else:
                    backends.append(using)
                translation.activate(language)
                backend = connections[using].get_backend()
                backend.update(index, iterable, commit, multilingual=False)
            translation.activate(initial_language)
        else:
            print(self.connection_alias)
            super(MultilingualSolrSearchBackend, self).update(index, iterable, commit)


class MultilingualSolrSearchQuery(SolrSearchQuery):
    def __init__(self, using=DEFAULT_ALIAS):
        language = translation.get_language()[:2] if translation.get_language() else 'en'
        using = get_using(language)
        super(MultilingualSolrSearchQuery, self).__init__(using)


class MultilingualSolrEngine(SolrEngine):
    backend = MultilingualSolrSearchBackend
    query = MultilingualSolrSearchQuery
