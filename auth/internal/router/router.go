package router

import (
	"auth/internal/handler"
	"net/http"

	"github.com/go-chi/chi/v5"
)

func NewRouter(h handler.UserHandlerInterface) http.Handler {
	r := chi.NewRouter()

	r.Route("/", func(r chi.Router) {
		r.Post("/signup", h.SignupHandler)
		r.Post("/login", h.LoginHandler)
		r.Get("/health", h.HealthCheckHandler)
	})
	// internal
	r.Route("/internal", func(r chi.Router) {
		r.Post("/resolve-users", h.ResolveUserIDsHandler)
	})

	return r
}
