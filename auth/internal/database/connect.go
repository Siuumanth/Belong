package database

import (
	"database/sql"

	_ "github.com/lib/pq"
)

// url is sent from main
func Connect(url string) (*sql.DB, error) {
	db, err := sql.Open("postgres", url)
	if err != nil {
		return nil, err
	}

	// ping db to see if connectin secure
	if err := db.Ping(); err != nil {
		return nil, err
	}

	return db, nil
}
