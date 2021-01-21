import re

from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()


@register.filter
@stringfilter
def short_title(text_blob):
    if len(text_blob) > 28:
        blurb = text_blob[:24]
        blurb = blurb[:blurb.rfind(' ')] + ' ...'
        return blurb
    else:
        return text_blob

@register.filter
@stringfilter
def violation(text_blob):
    '''
    Shorten the names of violation type facets.
    '''
    blob = text_blob.lower()
    if 'right' in blob:
        start = len(blob.split('right')[0])
        blurb = text_blob[start:]
        return blurb

    elif 'personal integrity' in blob:
        start = len(blob.split('personal integrity')[0])
        blurb = text_blob[start:]
        return blurb

    else:
        return text_blob

@register.filter
def get_item(dict, item):
    return dict[item]
