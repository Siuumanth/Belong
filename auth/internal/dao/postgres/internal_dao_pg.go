package postgres

import (
	"context"

	"github.com/google/uuid"
	"github.com/lib/pq"
)

const ResolveUserIDsByEmailsQuery = `SELECT id, email FROM users WHERE email = ANY($1)`

func (r *PGUserDAO) ResolveUserIDsByEmails(
	ctx context.Context,
	emails []string,
) (map[string]uuid.UUID, error) {

	rows, err := r.db.QueryContext(
		ctx,
		ResolveUserIDsByEmailsQuery,
		pq.Array(emails),
	)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	result := make(map[string]uuid.UUID)

	for rows.Next() {
		var id uuid.UUID
		var email string
		if err := rows.Scan(&id, &email); err != nil {
			return nil, err
		}
		result[email] = id
	}

	return result, nil
}
