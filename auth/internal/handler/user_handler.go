package handler

import (
	"auth/internal/model"
	"auth/internal/service"
	"encoding/json"
	"net/http"
)

type UserHandlerInterface interface {
	SignupHandler(w http.ResponseWriter, r *http.Request)
	LoginHandler(w http.ResponseWriter, r *http.Request)
	HealthCheckHandler(w http.ResponseWriter, r *http.Request)
	ResolveUserIDsHandler(w http.ResponseWriter, r *http.Request)
}

// to call services
type AuthHandler struct {
	service *service.AuthService
}

func NewAuthHandler(service *service.AuthService) *AuthHandler {
	return &AuthHandler{service: service}
}

func (h *AuthHandler) SignupHandler(w http.ResponseWriter, r *http.Request) {
	// parse json queries, validate and return response
	var user model.SignUpRequest

	if err := json.NewDecoder(r.Body).Decode(&user); err != nil {
		ErrorJSON(w, http.StatusBadRequest, "Invalid request body")
		return
	}

	// validate required fields
	if user.Email == "" || user.Password == "" || user.Username == "" {
		ErrorJSON(w, http.StatusBadRequest, "missing required fields")
		return
	}

	if err := h.service.Signup(r.Context(), user); err != nil {
		ErrorJSON(w, http.StatusBadRequest, err.Error())
		return
	}

	json.NewEncoder(w).Encode(map[string]string{
		"message": "signup successful",
	})
}

func (h *AuthHandler) LoginHandler(w http.ResponseWriter, r *http.Request) {
	var userReq model.LoginRequest

	if err := json.NewDecoder(r.Body).Decode(&userReq); err != nil {
		ErrorJSON(w, http.StatusBadRequest, "Invalid request body")
		return
	}

	if userReq.Email == "" || userReq.Password == "" {
		ErrorJSON(w, http.StatusBadRequest, "missing required fields")
		return
	}

	authResponse, err := h.service.Login(r.Context(), userReq)
	if err != nil {
		ErrorJSON(w, http.StatusBadRequest, err.Error())
		return
	}

	// not using cookie for jwt, we will use authorisation:bearer
	// // set http-only cookie
	// http.SetCookie(w, &http.Cookie{
	// 	Name:     "token",
	// 	Value:    authResponse.Token,
	// 	HttpOnly: true,
	// 	Secure:   true,
	// 	SameSite: http.SameSiteStrictMode,
	// 	Path:     "/",
	// })

	// send JSON response too (username, email, etc.)
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(authResponse)
}
