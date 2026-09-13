package utils

import (
	"context"
	"time"
)

type contextKey string

const (
	AuthContextKey contextKey = "auth"
	RequestIDKey   contextKey = "request_id"
)

// this is for claiming from the JWt
const (
	ClaimsUidKey      string = "user_id"
	ClaimsExpKey      string = "exp"
	ClaimsEmailKey    string = "email"
	ClaimsUsernameKey string = "username"
)

type AuthContext struct {
	UserID   string
	Username string
	Email    string
	Expires  time.Time
}

func GetAuthContext(ctx context.Context) (*AuthContext, bool) {
	//	fmt.Println("temp: ", ctx.Value(AuthContextKey))
	authCtx, ok := ctx.Value(AuthContextKey).(*AuthContext)
	//	fmt.Println("authCtx: ", authCtx, "ok: ", ok)
	return authCtx, ok
}
