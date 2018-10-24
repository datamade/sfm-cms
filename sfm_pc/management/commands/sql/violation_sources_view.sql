CREATE MATERIALIZED VIEW violation_sources AS
  SELECT
    vv.uuid AS id,
    vvsd.value AS start_date,
    vved.value AS end_date,
    vvld.value AS location_description,
    vval1.value AS admin_level_1,
    vval2.value AS admin_level_2,
    vvg.value AS osmname,
    vvgi.value AS osm_id,
    vvdi.value AS division_id,
    vvl.value AS location,
    vvd.value AS description,
    pp.uuid AS perpetrator_id,
    oo.uuid AS perpetrator_organization_id,
    vvpc.value AS perpetrator_classification,
    vvt.value AS violation_type,
    MAX(vvd.confidence) AS confidence,
    json_agg(DISTINCT vss.*) AS sources
  FROM violation_violation AS vv
  LEFT JOIN violation_violationstartdate AS vvsd
    ON vv.id = vvsd.object_ref_id
  LEFT JOIN violation_violationenddate AS vved
    ON vv.id = vved.object_ref_id
  LEFT JOIN violation_violationlocationdescription AS vvld
    ON vv.id = vvld.object_ref_id
  LEFT JOIN violation_violationadminlevel1 AS vval1
    ON vv.id = vval1.object_ref_id
  LEFT JOIN violation_violationadminlevel2 AS vval2
    ON vv.id = vval2.object_ref_id
  LEFT JOIN violation_violationosmname AS vvg
    ON vv.id = vvg.object_ref_id
  LEFT JOIN violation_violationosmid AS vvgi
    ON vv.id = vvgi.object_ref_id
  LEFT JOIN violation_violationdivisionid AS vvdi
    ON vv.id = vvdi.object_ref_id
  LEFT JOIN violation_violationlocation AS vvl
    ON vv.id = vvl.object_ref_id
  LEFT JOIN violation_violationdescription AS vvd
    ON vv.id = vvd.object_ref_id
  LEFT JOIN violation_violationdescription_sources AS vs
    ON vvd.id = vs.violationdescription_id
  LEFT JOIN source_source AS vss
    ON vs.source_id = vss.uuid
  LEFT JOIN violation_violationperpetrator AS vvp
    ON vv.id = vvp.object_ref_id
  LEFT JOIN person_person AS pp
    ON vvp.value_id = pp.id
  LEFT JOIN violation_violationperpetratororganization AS vvpo
    ON vv.id = vvpo.object_ref_id
  LEFT JOIN organization_organization AS oo
    ON vvpo.value_id = oo.id
  LEFT JOIN violation_violationperpetratorclassification AS vvpc
    ON vv.id = vvpc.object_ref_id
  LEFT JOIN violation_violationtype AS vvt
    ON vv.id = vvt.object_ref_id
  GROUP BY vv.uuid,
           vvsd.value,
           vved.value,
           vvld.value,
           vval1.value,
           vval2.value,
           vvg.value,
           vvgi.value,
           vvdi.value,
           vvl.value,
           vvd.value,
           pp.uuid,
           oo.uuid,
           vvpc.value,
           vvt.value;
CREATE UNIQUE INDEX violation_src_id_index ON violation_sources (
  id,
  perpetrator_id,
  perpetrator_organization_id,
  perpetrator_classification,
  violation_type
)
