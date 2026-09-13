package dao

import (
	model "auth/internal/model"
	"context"

	"github.com/google/uuid"
)

type UserDAO interface {
	CreateUser(ctx context.Context, user model.NewUser) error
	GetUserByEmail(ctx context.Context, email string) (model.DomainUser, error)
	ResolveUserIDsByEmails(ctx context.Context, emails []string) (map[string]uuid.UUID, error)
}
