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
