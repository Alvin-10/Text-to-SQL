-- Create the sandboxed read-only MySQL user the executor uses.
-- Run after mysql_chinook.sql, as a user that can GRANT (e.g. root).

CREATE USER IF NOT EXISTS 'readonly'@'%' IDENTIFIED BY 'readonly_pw';

-- SELECT only on the chinook database. No INSERT/UPDATE/DELETE, no DDL.
GRANT SELECT ON chinook.* TO 'readonly'@'%';

FLUSH PRIVILEGES;
