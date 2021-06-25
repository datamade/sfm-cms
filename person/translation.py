from modeltranslation.translator import translator, TranslationOptions
from .models import PersonName


class PersonNameTranslationOptions(TranslationOptions):
    fields = ('value',)


translator.register(PersonName, PersonNameTranslationOptions)
