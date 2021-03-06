CREATE MATERIALIZED VIEW person_name_export AS
  SELECT
    pp.uuid AS person_id,
    ppn.value AS name,
    ppn.confidence AS name_confidence,
    ppnss.uuid AS source_id
  FROM person_person AS pp
  LEFT JOIN person_personname AS ppn
    ON pp.id = ppn.object_ref_id
  LEFT JOIN person_personname_sources AS ppns
    ON ppn.id = ppns.personname_id
  LEFT JOIN source_source AS ppnss
    ON ppns.source_id = ppnss.uuid
  GROUP BY pp.uuid, ppn.value, ppn.confidence, ppnss.uuid
