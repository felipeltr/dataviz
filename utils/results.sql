drop table if exists results;

create table results as
with joined as (
	select
		*,
		to_tsvector(program) as program_ts
	from scraped s
	inner join college c
		on regexp_replace(s.institution, '([^a-zA-Z0-9\-\(\)]+)|\s','','g') = regexp_replace(c.name, '\s','','g')
)	
select
	canonical as institution,
	'Computer Science' as program,
	(case
		when program_ts @@ to_tsquery('master') then 'MS'
		when program_ts @@ to_tsquery('ms') then 'MS'
	 	when program_ts @@ to_tsquery('meng') then 'MS'
	 	when program_ts @@ to_tsquery('phd') then 'PhD'
	 	else null
	 end) as degree,
	(case
		when program_ts @@ to_tsquery('s19') then 'S19'
	 	when program_ts @@ to_tsquery('f19') then 'F19'
		when program_ts @@ to_tsquery('s18') then 'S18'
	 	when program_ts @@ to_tsquery('f18') then 'F18'
		when program_ts @@ to_tsquery('s17') then 'S17'
	 	when program_ts @@ to_tsquery('f17') then 'F17'
	 	when program_ts @@ to_tsquery('s16') then 'S16'
	 	when program_ts @@ to_tsquery('f16') then 'F16'
	 	when program_ts @@ to_tsquery('s15') then 'S15'
	 	when program_ts @@ to_tsquery('f15') then 'F15'
	 	else null
	end) as term,
	program as program_old,
	decision, status, date, gpa, v, q, w, notes
from joined
