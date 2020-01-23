-- 
SELECT
	name AS disease,
	dtype AS source,
	COUNT(protein_id) as count_protein
FROM
	disease
GROUP BY name, dtype
ORDER BY count_protein DESC
	;
-- LIMIT 100
