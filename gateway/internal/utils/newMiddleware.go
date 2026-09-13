package utils

import "net/http"

/*
Goal:

Replicate handlerFunc with my middleware functions

// The HandlerFunc type is an adapter to allow the use of
// ordinary functions as HTTP handlers. If f is a function
// with the appropriate signature, HandlerFunc(f) is a
// [Handler] that calls f.

type HandlerFunc func(ResponseWriter, *Request)

// ServeHTTP calls f(w, r).
func (f HandlerFunc) ServeHTTP(w ResponseWriter, r *Request) {
    f(w, r)
}

-------------
type Middleware interface {
	Handle(http.Handler) http.Handler
}

similar to how each handle function has serveHTTP

*/

type MiddlewareFunc func(http.Handler) http.Handler // return handler

func (m MiddlewareFunc) Handle(next http.Handler) http.Handler {
	return m(next)
}
