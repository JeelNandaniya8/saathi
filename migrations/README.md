# Saathi database migrations

Migrations run automatically when the application starts with a configured
`DATABASE_URL`. Each numbered SQL file runs once and is recorded in the
`schema_migrations` table.

Before a production migration:

1. Create a database backup or restore point.
2. Deploy during a low-traffic period.
3. Check `/api/health` after deployment.
4. Review server logs for a migration error.

If a migration fails, its transaction is rolled back and the application does
not continue starting. Restore the previous application version first. Do not
manually mark a failed migration as applied.
