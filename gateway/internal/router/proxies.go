package router

// defining proxies
import (
	"gateway/internal/proxy"
	"net/http"
	"os"
)

type Proxies struct {
	Auth   http.Handler
	Belong http.Handler
}

func NewProxies() *Proxies {
	authURL := os.Getenv("AUTH_SERVICE_URL")
	if authURL == "" {
		authURL = os.Getenv("GOVAULT_AUTH_SERVICE_URL")
	}
	if authURL == "" {
		authURL = "http://belong-auth:9001"
	}

	belongURL := os.Getenv("BELONG_SERVICE_URL")
	if belongURL == "" {
		belongURL = os.Getenv("PYTHON_SERVICE_URL")
	}
	if belongURL == "" {
		belongURL = "http://belong-api:8000"
	}

	return &Proxies{
		Auth:   proxy.NewReverseProxy(authURL, "AUTH_SERVICE"),
		Belong: proxy.NewReverseProxy(belongURL, "BELONG_SERVICE"),
	}
}
