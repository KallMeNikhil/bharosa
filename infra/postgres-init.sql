CREATE EXTENSION IF NOT EXISTS postgis;

-- bharosa_owner owns all application tables and runs all schema migrations.
-- It is never used by the application runtime and must never be granted to
-- bharosa_app, so that a compromised bharosa_app credential can never
-- escalate via SET ROLE / membership.
CREATE ROLE bharosa_owner WITH LOGIN PASSWORD 'bharosa_owner' NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;

-- bharosa_app is the runtime application role. It receives its privileges on
-- each table via ALTER DEFAULT PRIVILEGES FOR ROLE bharosa_owner below, and
-- individual migrations may further narrow those privileges (see the
-- append-only event table migrations) for specific tables. bharosa_app does
-- not own any table it operates on, so it can never ALTER or DROP those
-- tables, and it holds no GRANT OPTION, so it can never grant itself
-- privileges it was not given.
CREATE ROLE bharosa_app WITH LOGIN PASSWORD 'bharosa_app' NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;

GRANT CONNECT ON DATABASE bharosa TO bharosa_owner;
GRANT CONNECT ON DATABASE bharosa TO bharosa_app;

GRANT USAGE, CREATE ON SCHEMA public TO bharosa_owner;
GRANT USAGE ON SCHEMA public TO bharosa_app;

ALTER DEFAULT PRIVILEGES FOR ROLE bharosa_owner IN SCHEMA public
    GRANT ALL PRIVILEGES ON TABLES TO bharosa_app;
ALTER DEFAULT PRIVILEGES FOR ROLE bharosa_owner IN SCHEMA public
    GRANT ALL PRIVILEGES ON SEQUENCES TO bharosa_app;
