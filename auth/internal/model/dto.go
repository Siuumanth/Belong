package model

/*
List of Data Transfer Objects to create:
- Sign up request
- login request

- auth response
- error response

*/

type SignUpRequest struct {
	Username string `json:"username"`
	Email    string `json:"email"`
	Password string `json:"password"`
}

type LoginRequest struct {
	Email    string `json:"email"`
	Password string `json:"password"`
}

// response from login
type AuthResponse struct {
	Token    string `json:"token"`
	Username string `json:"username"`
	Email    string `json:"email"`
}

type ErrorResponse struct {
	Message   string `json:"message"`
	ErrorCode int    `json:"errorCode"`
}

// used to create token
type TokenClaims struct {
	ID    string `json:"id"`
	Email string `json:"email"`
	Iat   int64  `json:"iat"`
	Exp   int64  `json:"exp"`
}
