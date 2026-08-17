CREATE EXTENSION IF NOT EXISTS postgis;

-- bharosa_owner owns all application tables and runs all schema migrations.
-- It is never used by the application runtime and must never be granted to
-- bharosa_app, so that a compromised bharosa_app credential can never
-- escalate via SET ROLE / membership.
CREATE ROLE bharosa_owner WITH LOGIN PASSWORD 'bharosa_owner' NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;

-- bharosa_app is the tenant-scoped runtime application role. It receives its
-- privileges on each table via ALTER DEFAULT PRIVILEGES FOR ROLE bharosa_owner
-- below, and individual migrations may further narrow those privileges (see
-- the append-only event table migrations) for specific tables. bharosa_app
-- does not own any table it operates on, so it can never ALTER or DROP those
-- tables, and it holds no GRANT OPTION, so it can never grant itself
-- privileges it was not given. Row-level security policies restrict it to the
-- manufacturer named by the bharosa.manufacturer_id session setting.
CREATE ROLE bharosa_app WITH LOGIN PASSWORD 'bharosa_app' NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;

-- bharosa_verifier backs the public verification endpoint only. Public
-- verification is inherently cross-tenant: a scanned code does not name its
-- manufacturer until the serial has been resolved. Rather than weakening
-- bharosa_app's tenant isolation to accommodate that, the public path runs as
-- a separate role that is granted the narrowest possible set of tables and
-- holds no privilege at all on manufacturer business data. It receives no
-- default privileges; every grant is made explicitly by the migration that
-- creates the table concerned.
CREATE ROLE bharosa_verifier WITH LOGIN PASSWORD 'bharosa_verifier' NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;

GRANT CONNECT ON DATABASE bharosa TO bharosa_owner;
GRANT CONNECT ON DATABASE bharosa TO bharosa_app;
GRANT CONNECT ON DATABASE bharosa TO bharosa_verifier;

GRANT USAGE, CREATE ON SCHEMA public TO bharosa_owner;
GRANT USAGE ON SCHEMA public TO bharosa_app;
GRANT USAGE ON SCHEMA public TO bharosa_verifier;

ALTER DEFAULT PRIVILEGES FOR ROLE bharosa_owner IN SCHEMA public
    GRANT ALL PRIVILEGES ON TABLES TO bharosa_app;
ALTER DEFAULT PRIVILEGES FOR ROLE bharosa_owner IN SCHEMA public
    GRANT ALL PRIVILEGES ON SEQUENCES TO bharosa_app;
