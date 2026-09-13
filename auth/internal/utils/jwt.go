package utils

import (
	"auth/internal/model"
	"os"
	"time"

	"github.com/golang-jwt/jwt/v5"
)

// SIGN JWT Token
func SignToken(user model.DomainUser) (string, error) {
	jwtSecret := os.Getenv("JWT_SECRET")
	jwtExpiresIn := os.Getenv("JWT_EXPIRES_IN")

	// map claims
	claims := jwt.MapClaims{
		"user_id":  user.ID,
		"username": user.Username,
		"email":    user.Email,
	}

	if jwtExpiresIn != "" {
		duration, err := time.ParseDuration(jwtExpiresIn)
		if err != nil {
			return "", err
		}
		claims["exp"] = jwt.NewNumericDate(time.Now().Add(duration))
	} else {
		claims["exp"] = jwt.NewNumericDate(time.Now().Add(15 * time.Minute))
	}

	// finally create the token
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)

	// sign the token
	signedToken, err := token.SignedString([]byte(jwtSecret))
	if err != nil {
		return "", err
	}

	return signedToken, nil
}
