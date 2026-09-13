package router

import (
	"gateway/internal/health"
	MW "gateway/internal/middleware"
	"net/http"

	"github.com/go-chi/chi/v5"
)

// DONE: Refactor router to allow for different implementatoins of router

// the router is also just an http handler with some middlewares

type Router interface {
	http.Handler
	ConfigureRoutes(proxies *Proxies, authz MW.Middleware)
}

/*
.
.
.
.
MAKING CHI ROUTER:
.
.
.
.
*/

// container for holding a chi router
type ChiRouter struct {
	mux *chi.Mux // type of http handler
}

func NewChiRouter() *ChiRouter {
	return &ChiRouter{
		mux: chi.NewRouter(),
	}
}

// implement ServeHTTP to implement http.Handler
func (r *ChiRouter) ServeHTTP(w http.ResponseWriter, req *http.Request) {
	r.mux.ServeHTTP(w, req)
}

func (r ChiRouter) ConfigureRoutes(proxies *Proxies, authz MW.Middleware) {
	// Health check
	r.mux.Get("/health", health.HealthCheckHandler)

	//	r.mux.Handle("/metrics", promhttp.Handler())
	// Public routes (no JWT)
	r.mux.Route("/auth", func(r chi.Router) {
		r.Mount("/", http.StripPrefix("/auth", proxies.Auth))
	})

	r.mux.Route("/api", func(r chi.Router) {
		// ---------- PUBLIC ----------
		r.Mount("/files", http.StripPrefix("/api/files", proxies.Files))

		// ---------- PROTECTED ----------
		r.Group(func(r chi.Router) {
			r.Use(authz.Handle)
			r.Mount("/upload", http.StripPrefix("/api/upload", proxies.Upload))
		})
	})
}
