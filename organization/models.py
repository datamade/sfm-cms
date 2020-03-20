import uuid

import reversion

from django.db import models
from django.db.models.functions import Coalesce
from django.utils.translation import ugettext as _
from django.conf import settings
from django.core.urlresolvers import reverse
from django.template.defaultfilters import truncatewords

from complex_fields.model_decorators import (versioned, translated, sourced,
                                             sourced_optional)
from complex_fields.models import ComplexField, ComplexFieldContainer, ComplexFieldListContainer
from complex_fields.base_models import BaseModel
from django_date_extensions.fields import ApproximateDateField

from sfm_pc.utils import VersionsMixin
from sfm_pc.fields import GetComplexFieldNameMixin

VERSION_RELATED_FIELDS = [
    'associationorganization_set',
    'emplacementorganization_set',
    'organizationalias_set',
    'organizationclassification_set',
    'organizationdivisionid_set',
    'organizationfirstciteddate_set',
    'organizationheadquarters_set',
    'organizationlastciteddate_set',
    'organizationname_set',
    'organizationopenended_set',
    'organizationrealstart_set',
    'membershiporganizationmember_set',
    'membershiporganizationorganization_set',
    'membershippersonorganization_set',
    'violationperpetratororganization_set',
]


@reversion.register(follow=VERSION_RELATED_FIELDS)
class Organization(models.Model, BaseModel, VersionsMixin, GetComplexFieldNameMixin):

    uuid = models.UUIDField(default=uuid.uuid4,
                            editable=False,
                            db_index=True)

    published = models.BooleanField(default=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = ComplexFieldContainer(self, OrganizationName)
        self.aliases = ComplexFieldListContainer(self, OrganizationAlias)
        self.classification = ComplexFieldListContainer(self, OrganizationClassification)
        self.division_id = ComplexFieldContainer(self, OrganizationDivisionId)
        self.headquarters = ComplexFieldContainer(self, OrganizationHeadquarters)
        self.firstciteddate = ComplexFieldContainer(self, OrganizationFirstCitedDate)
        self.lastciteddate = ComplexFieldContainer(self, OrganizationLastCitedDate)
        self.realstart = ComplexFieldContainer(self, OrganizationRealStart)
        self.open_ended = ComplexFieldContainer(self, OrganizationOpenEnded)

        self.complex_fields = [self.name, self.division_id, self.firstciteddate,
                               self.lastciteddate, self.realstart, self.open_ended,
                               self.headquarters]

        self.complex_lists = [self.aliases, self.classification]

        self.required_fields = [
            "Organization_OrganizationName",
        ]

    def get_value(self):
        return self.name.get_value()

    def __str__(self):
        return str(self.name)

    @property
    def associations(self):
        '''
        Return all of this organization's associations, in a custom sorting order.

        Order by first cited date descending, then last cited date descending,
        with nulls last.
        '''
        assocs = self.associationorganization_set\
                     .annotate(lcd=Coalesce('object_ref__associationstartdate__value',
                                            'object_ref__associationenddate__value',
                                            models.Value('1000-0-0')))\
                     .order_by('-lcd')

        return assocs

    @property
    def emplacements(self):
        '''
        Return all of this organization's emplacements, in a custom sorting order.

        Order by first cited date descending, then last cited date descending,
        with nulls last.
        '''
        empls = self.emplacementorganization_set\
                    .annotate(lcd=Coalesce('object_ref__emplacementstartdate__value',
                                           'object_ref__emplacementenddate__value',
                                           models.Value('1000-0-0')))\
                    .order_by('-lcd')

        return empls

    @property
    def personnel(self):
        '''
        Returns all personnel ever assigned to a unit

        Objects returned are MembershipPerson objects
        '''
        return [o.object_ref for o in self.membershippersonorganization_set.all()]

    @property
    def alias_list(self):
        return ', '.join(a.get_value().value for a in self.aliases.get_list())

    @property
    def related_entities(self):
        """
        Return a list of dicts with metadata for all of the entities linked to
        this Organization.

        Metadata dicts must have the following keys:
            - name
            - entity_type
            - start_date
            - end_date
            - open_ended
            - url (a link to edit the entity)
        """
        related_entities = []

        # People that are posted to this organization.
        for membershipperson in self.membershippersonorganization_set.all():
            membership = membershipperson.object_ref
            person = membership.member.get_value().value
            related_entities.append({
                'name': person.name.get_value().value,
                'entity_type': _('MembershipPerson'),
                'start_date': membership.firstciteddate.get_value(),
                'end_date': membership.lastciteddate.get_value(),
                'open_ended': membership.realend.get_value(),
                'url': reverse(
                    'edit-organization-personnel',
                    kwargs={
                        'organization_id': self.uuid,
                        'pk': membership.pk
                    }
                ),
            })

        # Organizations that are children of this org.
        for compositionparent in self.child_organization.all():
            composition = compositionparent.object_ref
            child = composition.child.get_value().value
            related_entities.append({
                'name': child.name.get_value().value,
                'entity_type': _('Composition'),
                'start_date': composition.startdate.get_value(),
                'end_date': composition.enddate.get_value(),
                'open_ended': composition.open_ended.get_value(),
                'url': reverse(
                    'edit-organization-composition',
                    kwargs={
                        'organization_id': self.uuid,
                        'pk': composition.pk
                    }
                ),
            })

        # Organizations that are parents of this org.
        for compositionchild in self.parent_organization.all():
            composition = compositionchild.object_ref
            parent = composition.parent.get_value().value
            related_entities.append({
                'name': parent.name.get_value().value,
                'entity_type': _('Composition'),
                'start_date': composition.startdate.get_value(),
                'end_date': composition.enddate.get_value(),
                'open_ended': composition.open_ended.get_value(),
                'url': reverse(
                    'edit-organization-composition',
                    kwargs={
                        'organization_id': self.uuid,
                        'pk': composition.pk
                    }
                ),
            })

        # Organizations that this org is a member of.
        for membershiporganizationmember in self.membershiporganizationmember_set.all():
            membership = membershiporganizationmember.object_ref
            member_org = membership.organization.get_value().value
            related_entities.append({
                'name': member_org.name.get_value().value,
                'entity_type': _('MembershipOrganization'),
                'start_date': membership.firstciteddate.get_value(),
                'end_date': membership.lastciteddate.get_value(),
                'open_ended': membership.realend.get_value(),
                'url': reverse(
                    'edit-organization-membership',
                    kwargs={
                        'organization_id': self.uuid,
                        'pk': membership.pk
                    }
                ),
            })

        # Organizations that are members of this org.
        for membershiporganizationorganization in self.membershiporganizationorganization_set.all():
            membership = membershiporganizationorganization.object_ref
            member_org = membership.member.get_value().value
            related_entities.append({
                'name': member_org.name.get_value().value,
                'entity_type': _('MembershipOrganization'),
                'start_date': membership.firstciteddate.get_value(),
                'end_date': membership.lastciteddate.get_value(),
                'open_ended': membership.realend.get_value(),
                'url': reverse(
                    'edit-organization-membership',
                    kwargs={
                        'organization_id': self.uuid,
                        'pk': membership.pk
                    }
                ),
            })

        # Areas of operation.
        for associationorganization in self.associationorganization_set.all():
            association = associationorganization.object_ref
            location = association.area.get_value().value
            related_entities.append({
                'name': location.name,
                'entity_type': _('Association'),
                'start_date': association.startdate.get_value(),
                'end_date': association.enddate.get_value(),
                'open_ended': association.open_ended.get_value(),
                'url': reverse(
                    'edit-organization-association',
                    kwargs={
                        'organization_id': self.uuid,
                        'pk': association.pk
                    }
                ),
            })

        # Organization sites.
        for emplacementorganization in self.emplacementorganization_set.all():
            emplacement = emplacementorganization.object_ref
            location = emplacement.site.get_value().value
            related_entities.append({
                'name': location.name,
                'entity_type': _('Emplacement'),
                'start_date': emplacement.startdate.get_value(),
                'end_date': emplacement.enddate.get_value(),
                'open_ended': emplacement.open_ended.get_value(),
                'url': reverse(
                    'edit-organization-emplacement',
                    kwargs={
                        'organization_id': self.uuid,
                        'pk': emplacement.pk
                    }
                ),
            })

        # Violations where this org was a perpetrator.
        for violationperpetrator in self.violationperpetratororganization_set.all():
            violation = violationperpetrator.object_ref
            related_entities.append({
                'name': truncatewords(violation.description.get_value(), 10),
                'entity_type': _('Violation'),
                'start_date': violation.startdate.get_value(),
                'end_date': violation.enddate.get_value(),
                'open_ended': '',
                'url': reverse('edit-violation', kwargs={'slug': violation.uuid}),
            })

        return related_entities


@translated
@versioned
@sourced
class OrganizationName(ComplexField):
    object_ref = models.ForeignKey('Organization')
    value = models.TextField(default=None, blank=True, null=True)
    field_name = _("Name")
    shortcode = 'u_n'
    spreadsheet_field_name = 'unit:name'


@translated
@versioned
@sourced
class OrganizationAlias(ComplexField):
    object_ref = models.ForeignKey('Organization')
    value = models.TextField(blank=True, null=True)
    field_name = _("Other Names")
    shortcode = 'u_on'
    spreadsheet_field_name = 'unit:other_names'


@versioned
@sourced
class OrganizationClassification(ComplexField):
    object_ref = models.ForeignKey('Organization')
    value = models.TextField(blank=True, null=True)
    field_name = _("Classification")
    shortcode = 'u_cl'
    spreadsheet_field_name = 'unit:classification'


@versioned
@sourced
class OrganizationDivisionId(ComplexField):
    object_ref = models.ForeignKey('Organization')
    value = models.TextField(default=None, blank=True, null=True)
    field_name = _("Country")
    shortcode = 'u_c'
    spreadsheet_field_name = 'unit:country'

    def __str__(self):
        return self.value


@versioned
@sourced
class OrganizationHeadquarters(ComplexField):
    object_ref = models.ForeignKey('Organization')
    value = models.TextField(default=None, blank=True, null=True)
    field_name = _("Base Name")
    shortcode = 'u_bn'
    spreadsheet_field_name = 'unit:base_name'


@versioned
@sourced
class OrganizationFirstCitedDate(ComplexField):
    object_ref = models.ForeignKey('Organization')
    value = ApproximateDateField()
    field_name = _("First Cited Date")
    shortcode = 'u_fcd'
    spreadsheet_field_name = 'unit:first_cited_date'


@versioned
@sourced
class OrganizationLastCitedDate(ComplexField):
    object_ref = models.ForeignKey('Organization')
    value = ApproximateDateField()
    field_name = _("Last Cited Date")
    shortcode = 'u_lcd'
    spreadsheet_field_name = 'unit:last_cited_date'


@versioned
@sourced_optional
class OrganizationRealStart(ComplexField):
    object_ref = models.ForeignKey('Organization')
    value = models.NullBooleanField(default=None)
    field_name = _("Start Date?")
    shortcode = 'u_fcds'
    spreadsheet_field_name = 'unit:first_cited_date_start'


@versioned
@sourced_optional
class OrganizationOpenEnded(ComplexField):
    object_ref = models.ForeignKey('Organization')
    value = models.CharField(default='N', max_length=1, choices=settings.OPEN_ENDED_CHOICES)
    field_name = _("Is Open Ended?")
    shortcode = 'u_lcdo'
    spreadsheet_field_name = 'unit:last_cited_date_open'
