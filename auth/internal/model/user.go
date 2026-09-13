package model

type NewUser struct {
	Username     string `json:"username"`
	Email        string `json:"email"`
	PasswordHash string `json:"password_hash"`
}

type DomainUser struct {
	ID           string `json:"user_id"`
	Username     string `json:"username"`
	Email        string `json:"email"`
	PasswordHash string `json:"password_hash"`
}
