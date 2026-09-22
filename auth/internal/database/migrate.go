package database

import (
	"database/sql"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

// RunMigrations applies any pending .sql files from the migrations/ directory.
// It tracks applied migrations in a schema_migrations table, mirroring the
// Python API's migrate.py behaviour.
func RunMigrations(db *sql.DB) error {
	// Create the tracker table if it doesn't exist yet
	_, err := db.Exec(`
		CREATE TABLE IF NOT EXISTS schema_migrations (
			version    TEXT PRIMARY KEY,
			applied_at TIMESTAMP NOT NULL DEFAULT NOW()
		)
	`)
	if err != nil {
		return fmt.Errorf("creating schema_migrations table: %w", err)
	}

	// Collect already-applied versions
	rows, err := db.Query(`SELECT version FROM schema_migrations`)
	if err != nil {
		return fmt.Errorf("querying schema_migrations: %w", err)
	}
	applied := make(map[string]bool)
	for rows.Next() {
		var v string
		if err := rows.Scan(&v); err != nil {
			rows.Close()
			return fmt.Errorf("scanning migration version: %w", err)
		}
		applied[v] = true
	}
	rows.Close()
	if err := rows.Err(); err != nil {
		return fmt.Errorf("iterating schema_migrations: %w", err)
	}

	// Resolve migrations/ relative to the working directory (where go run / the
	// binary is invoked from). When run as "go run ./cmd/main.go" from the auth/
	// directory, cwd is auth/ and migrations/ sits right next to cmd/.
	cwd, err := os.Getwd()
	if err != nil {
		return fmt.Errorf("getting working directory: %w", err)
	}
	migrationsDir := filepath.Join(cwd, "migrations")

	entries, err := os.ReadDir(migrationsDir)
	if err != nil {
		return fmt.Errorf("reading migrations directory %q: %w", migrationsDir, err)
	}

	// Collect and sort .sql files
	var files []string
	for _, e := range entries {
		if !e.IsDir() && strings.HasSuffix(e.Name(), ".sql") {
			files = append(files, e.Name())
		}
	}
	sort.Strings(files)

	for _, name := range files {
		if applied[name] {
			fmt.Printf("[migrations] skipping already applied: %s\n", name)
			continue
		}

		content, err := os.ReadFile(filepath.Join(migrationsDir, name))
		if err != nil {
			return fmt.Errorf("reading migration %q: %w", name, err)
		}

		fmt.Printf("[migrations] applying: %s\n", name)
		if _, err := db.Exec(string(content)); err != nil {
			return fmt.Errorf("executing migration %q: %w", name, err)
		}

		if _, err := db.Exec(
			`INSERT INTO schema_migrations (version) VALUES ($1)`, name,
		); err != nil {
			return fmt.Errorf("recording migration %q: %w", name, err)
		}

		fmt.Printf("[migrations] applied:  %s\n", name)
	}

	fmt.Println("[migrations] all migrations are up to date.")
	return nil
}
