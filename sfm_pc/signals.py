from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.db import connection
from django.core.management import call_command

from complex_fields.base_models import object_ref_saved

from search import search
from source.models import Source
from organization.models import Organization
from person.models import Person
from violation.models import Violation
from membershipperson.models import MembershipPerson
from composition.models import Composition

'''
TODO: Update signals to use Haystack, where appropriate
'''
def update_index(entity_type, object_id):
    call_command('make_search_index',
                 '--id={}'.format(object_id),
                 '--entity-types={}'.format(entity_type))

#@receiver(object_ref_saved, sender=Organization)
#def update_organization_index(sender, **kwargs):
#    update_index('organizations', kwargs['object_id'])
#
#
#@receiver(object_ref_saved, sender=Person)
#def update_person_index(sender, **kwargs):
#    update_index('people', kwargs['object_id'])
#
#
#@receiver(object_ref_saved, sender=Violation)
#def update_violation_index(sender, **kwargs):
#    update_index('violations', kwargs['object_id'])


@receiver(object_ref_saved, sender=MembershipPerson)
def update_membership_index(sender, **kwargs):
    membership = MembershipPerson.objects.get(id=kwargs['object_id'])

    update_index('compositions', membership.organization.get_value().value.uuid)
    update_index('commanders', membership.member.get_value().value.uuid)


@receiver(object_ref_saved, sender=Composition)
def update_composition_index(sender, **kwargs):
    composition = Composition.objects.get(id=kwargs['object_id'])

    update_index('compositions', composition.parent.get_value().value.uuid)
    update_index('compositions', composition.child.get_value().value.uuid)


#@receiver(post_save, sender=Source)
#def update_source_index(sender, **kwargs):
#    # An instance will always be sent by the post_save receiver. See:
#    # https://docs.djangoproject.com/en/2.2/ref/signals/#django.db.models.signals.pre_save
#    instance = kwargs['instance']
#    update_index('sources', str(instance.uuid))
#
#
#@receiver(post_delete, sender=Organization)
#@receiver(post_delete, sender=Person)
#@receiver(post_delete, sender=Violation)
#@receiver(post_delete, sender=Source)
#def remove_index(sender, **kwargs):
#    searcher = search.Searcher()
#    searcher.delete(id=kwargs['instance'].uuid)
