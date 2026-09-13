package service

import (
	"context"
	"fmt"

	"github.com/google/uuid"
)

// internal
func (p *AuthService) ResolveUserIDs(ctx context.Context, emails []string) (map[string]uuid.UUID, error) {
	result, err := p.dao.ResolveUserIDsByEmails(ctx, emails)
	if err != nil {
		return nil, err
	}

	// Check if every requested email was actually found
	if len(result) != len(emails) {
		return nil, fmt.Errorf("some users could not be found")
	}

	return result, nil
}
