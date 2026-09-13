package service

import (
	"auth/internal/dao"
	"auth/internal/model"
	"auth/internal/utils"
	"context"
	"errors"

	"github.com/google/uuid"
)

// intreface for just listing out methods
type AuthServiceMethods interface {
	Signup(user model.SignUpRequest) error
	Login(user model.LoginRequest) (model.AuthResponse, error)
	ResolveUserIDs(emails []string) (map[string]uuid.UUID, error)
}

// we need a dao object to call the DAO methods
type AuthService struct {
	dao dao.UserDAO
}

// now any behaviour can be passed here, pg, mongo, memory
func NewAuthService(p dao.UserDAO) *AuthService {
	return &AuthService{dao: p}
}

// never pass *interface in go

func (p *AuthService) Signup(ctx context.Context, user model.SignUpRequest) error {
	// create user with email, username and password, after hash
	var newUser model.NewUser
	newUser.Username = user.Username
	newUser.Email = user.Email

	hashedPW, err := utils.HashPassword(user.Password)

	if err != nil {
		return err
	}

	newUser.PasswordHash = hashedPW

	// call DAO
	err = p.dao.CreateUser(ctx, newUser)

	if err != nil {
		if err.Error() == "duplicate" {
			return errors.New("user already exists")
		}
		return err
	}

	return nil
}

func (p *AuthService) Login(ctx context.Context, user model.LoginRequest) (model.AuthResponse, error) {
	// Get user from DB, check password, return token
	var domainUser model.DomainUser

	domainUser, err := p.dao.GetUserByEmail(ctx, user.Email)

	if err != nil {
		return model.AuthResponse{}, err
	}

	// user not found
	if domainUser.Email == "" {
		return model.AuthResponse{}, errors.New("invalid credentials")
	}

	// if user exists, check password
	if err := utils.VerifyPassword(user.Password, domainUser.PasswordHash); err != nil {
		return model.AuthResponse{}, errors.New("invalid credentials")
	}

	var token string

	token, err = utils.SignToken(domainUser)

	if err != nil {
		return model.AuthResponse{}, err
	}

	return model.AuthResponse{Token: token, Username: domainUser.Username, Email: domainUser.Email}, nil

}
