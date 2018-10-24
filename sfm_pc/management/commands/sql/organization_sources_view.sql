CREATE MATERIALIZED VIEW organization_sources AS
  SELECT
    oo.uuid AS id,
    oon.value AS name_value,
    MAX(oon.confidence) AS name_confidence,
    json_agg(DISTINCT oonss.*) AS name_source,
    ooa.value AS alias_value,
    MAX(ooa.confidence) AS alias_confidence,
    json_agg(DISTINCT ooass.*) AS alias_source,
    ooc.value AS classification_value,
    MAX(ooc.confidence) AS classification_confidence,
    json_agg(DISTINCT oocss.*)
      FILTER (WHERE oocss.uuid IS NOT NULL) AS classification_source,
    MAX(ood.value) AS division_id
  FROM organization_organization AS oo
  LEFT JOIN organization_organizationname AS oon
    ON oo.id = oon.object_ref_id
  LEFT JOIN organization_organizationname_sources AS oons
    ON oon.id = oons.organizationname_id
  LEFT JOIN source_source AS oonss
    ON oons.source_id = oonss.uuid
  LEFT JOIN organization_organizationalias AS ooa
    ON oo.id = ooa.object_ref_id
  LEFT JOIN organization_organizationalias_sources AS ooas
    ON ooa.id = ooas.organizationalias_id
  LEFT JOIN source_source AS ooass
    ON ooas.source_id = ooass.uuid
  LEFT JOIN organization_organizationclassification AS ooc
    ON oo.id = ooc.object_ref_id
  LEFT JOIN organization_organizationclassification_sources AS oocs
    ON ooc.id = oocs.organizationclassification_id
  LEFT JOIN source_source AS oocss
    ON oocs.source_id = oocss.uuid
  LEFT JOIN organization_organizationdivisionid AS ood
    ON oo.id = ood.object_ref_id
  GROUP BY oo.uuid,
           oon.value,
           ooa.value,
           ooc.value;
CREATE UNIQUE INDEX organization_src_id_index ON organization_sources (id, alias_value, classification_value)
