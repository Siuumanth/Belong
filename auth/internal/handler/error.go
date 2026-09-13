package handler

import (
	"encoding/json"
	"net/http"
)

func ErrorJSON(w http.ResponseWriter, status int, msg string) {
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(map[string]string{
		"error": msg,
	})
}
