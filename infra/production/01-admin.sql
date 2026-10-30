-- Production database bootstrap, part 1. Run once, as the database's admin
-- user (on Neon, the default owner role), before the first deploy:
--
--   psql "$ADMIN_DATABASE_URL" \
--     -v owner_password="..." -v app_password="..." -v verifier_password="..." \
--     -f infra/production/01-admin.sql
--
-- This mirrors infra/postgres-init.sql with real passwords. The three roles stay
-- separate for the same reasons given there: bharosa_owner runs migrations and
-- owns every table, bharosa_app is the tenant-scoped runtime role held to
-- row-level security, and bharosa_verifier backs public verification only.

CREATE EXTENSION IF NOT EXISTS postgis;

CREATE ROLE bharosa_owner WITH LOGIN PASSWORD :'owner_password'
    NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
CREATE ROLE bharosa_app WITH LOGIN PASSWORD :'app_password'
    NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
CREATE ROLE bharosa_verifier WITH LOGIN PASSWORD :'verifier_password'
    NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;

SELECT format('GRANT CONNECT ON DATABASE %I TO bharosa_owner, bharosa_app, bharosa_verifier',
              current_database()) \gexec

GRANT USAGE, CREATE ON SCHEMA public TO bharosa_owner;
GRANT USAGE ON SCHEMA public TO bharosa_app, bharosa_verifier;
