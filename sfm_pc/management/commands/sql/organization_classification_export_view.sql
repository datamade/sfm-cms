CREATE MATERIALIZED VIEW organization_classification_export AS
  SELECT
    oo.uuid AS organization_id,
    ooc.value AS classification,
    ooc.confidence AS classification_confidence,
    oocss.uuid AS source_id
  FROM organization_organization AS oo
  LEFT JOIN organization_organizationclassification AS ooc
    ON oo.id = ooc.object_ref_id
  LEFT JOIN organization_organizationclassification_sources AS oocs
    ON ooc.id = oocs.organizationclassification_id
  LEFT JOIN source_source AS oocss
    ON oocs.source_id = oocss.uuid
  GROUP BY oo.uuid, ooc.value, ooc.confidence, oocss.uuid
