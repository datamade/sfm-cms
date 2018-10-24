CREATE MATERIALIZED VIEW organization_alias_export AS
  SELECT
    oo.uuid AS organization_id,
    ooa.value AS alias,
    ooa.confidence AS alias_confidence,
    ooass.uuid AS source_id
  FROM organization_organization AS oo
  LEFT JOIN organization_organizationalias AS ooa
    ON oo.id = ooa.object_ref_id
  LEFT JOIN organization_organizationalias_sources AS ooas
    ON ooa.id = ooas.organizationalias_id
  LEFT JOIN source_source AS ooass
    ON ooas.source_id = ooass.uuid
  GROUP BY oo.uuid, ooa.value, ooa.confidence, ooass.uuid
