-- Create the sandboxed read-only role the executor uses.
-- Runs after 01_chinook.sql, so all tables already exist.

CREATE ROLE readonly WITH LOGIN PASSWORD 'readonly_pw';

GRANT CONNECT ON DATABASE chinook TO readonly;
GRANT USAGE ON SCHEMA public TO readonly;

-- SELECT only. No INSERT/UPDATE/DELETE/TRUNCATE, no DDL.
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly;

-- Cover any tables added later in the same schema.
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO readonly;

-- Explicitly ensure the role cannot create objects in the schema.
REVOKE CREATE ON SCHEMA public FROM readonly;
