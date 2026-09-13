package utils

import (
	"crypto/sha256"
	"crypto/subtle"
	"fmt"
)

// hash password using sha256
func HashPassword(password string) (string, error) {
	// SHA-256 doesn't actually return an error on Write, but for clean code:
	h := sha256.Sum256([]byte(password))
	return fmt.Sprintf("%x", h), nil
}

// switch to bcrypt
//
//	func HashPassword(password string) (string, error) {
//		bytes, err := bcrypt.GenerateFromPassword([]byte(password), bcrypt.DefaultCost)
//		return string(bytes), err
//	}
//
// verify if password correct
// func VerifyPassword(password, hash string) error {
// 	return bcrypt.CompareHashAndPassword([]byte(hash), []byte(password))
// }

// FIX: Verify password by hashing input and comparing hex strings
func VerifyPassword(password, storedHash string) error {
	// 1. Hash the password provided during login
	currentHash, _ := HashPassword(password)

	// 2. Use ConstantTimeCompare to prevent timing attacks
	// It returns 1 if they match, 0 if they don't
	if subtle.ConstantTimeCompare([]byte(currentHash), []byte(storedHash)) == 1 {
		return nil
	}

	// 3. Return an error if they don't match to satisfy your existing logic
	return fmt.Errorf("invalid credentials")
}
