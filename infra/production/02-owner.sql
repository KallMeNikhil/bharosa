-- Production database bootstrap, part 2. Run once, connected as bharosa_owner,
-- after 01-admin.sql and before the first migration:
--
--   psql "postgresql://bharosa_owner:...@host/db?sslmode=require" \
--     -f infra/production/02-owner.sql
--
-- Default privileges are set by the owner itself rather than "FOR ROLE
-- bharosa_owner" from the admin user, because managed Postgres admin users are
-- often not members of the roles they create, which that form requires.

ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO bharosa_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON SEQUENCES TO bharosa_app;
