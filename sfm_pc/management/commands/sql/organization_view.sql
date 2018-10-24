CREATE MATERIALIZED VIEW organization AS
  SELECT DISTINCT ON (
    oo.uuid,
    oon.value,
    ooa.value,
    ooc.value,
    oofcd.value,
    oors.value,
    oolcd.value,
    oooo.value,
    ood.value,
    oohq.value
  )
    oo.uuid AS id,
    oon.value AS name,
    ooa.value AS alias,
    ooc.value AS classification,
    oofcd.value AS first_cited,
    oors.value AS real_start,
    oolcd.value AS last_cited,
    oooo.value AS open_ended,
    ood.value AS division_id,
    oohq.value AS headquarters
  FROM organization_organization AS oo
  LEFT JOIN organization_organizationname AS oon
    ON oo.id = oon.object_ref_id
  LEFT JOIN organization_organizationalias AS ooa
    ON oo.id = ooa.object_ref_id
  LEFT JOIN organization_organizationclassification AS ooc
    ON oo.id = ooc.object_ref_id
  LEFT JOIN organization_organizationfirstciteddate AS oofcd
    ON oo.id = oofcd.object_ref_id
  LEFT JOIN organization_organizationrealstart AS oors
    ON oo.id = oors.object_ref_id
  LEFT JOIN organization_organizationlastciteddate AS oolcd
    ON oo.id = oolcd.object_ref_id
  LEFT JOIN organization_organizationopenended AS oooo
    ON oo.id = oooo.object_ref_id
  LEFT JOIN organization_organizationdivisionid AS ood
    ON oo.id = ood.object_ref_id
  LEFT JOIN organization_organizationheadquarters AS oohq
    ON oo.id = oohq.object_ref_id;
CREATE UNIQUE INDEX organization_id_index ON organization (
  id,
  alias,
  headquarters,
  classification,
  first_cited,
  real_start,
  last_cited,
  open_ended
)
