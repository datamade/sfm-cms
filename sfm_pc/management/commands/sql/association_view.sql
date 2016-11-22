CREATE OR REPLACE VIEW association AS 
  SELECT 
    aa.id,
    aasd.value AS start_date,
    aaed.value AS end_date,
    oo.uuid AS organization_id,
    aaa.value_id AS area_id
  FROM association_association AS aa
  LEFT JOIN association_associationstartdate AS aasd
    ON aa.id = aasd.object_ref_id
  LEFT JOIN association_associationenddate AS aaed
    ON aa.id = aaed.object_ref_id
  LEFT JOIN association_associationorganization AS aao
    ON aa.id = aao.object_ref_id
  LEFT JOIN organization_organization AS oo
    ON aao.value_id = oo.id
  LEFT JOIN association_associationarea AS aaa
    ON aa.id = aaa.object_ref_id
