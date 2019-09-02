# first, login with psql
psql -U USERNAME -d databasename

# set output for all queries
\o FILENAME.sql

# run this query
select 'drop table ' || tablename || ' cascade;' from pg_tables;

# logout from psql
\q

# run sql script from commandline
psql -U USERNAME -d databasename -f FILENAME.sql