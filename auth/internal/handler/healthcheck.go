package handler

import (
	"fmt"
	"net/http"
)

func (h *AuthHandler) HealthCheckHandler(w http.ResponseWriter, r *http.Request) {
	w.WriteHeader(http.StatusOK)
	w.Write([]byte("Auth service healthy"))
	fmt.Println("Auth service healthy")
}

// func (h *AuthHandler) TestHandler(w http.ResponseWriter, r *http.Request) {
// 	w.Write([]byte("hello world"))
