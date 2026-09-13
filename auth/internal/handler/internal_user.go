package handler

import (
	"encoding/json"
	"fmt"
	"net/http"
)

// handler/internal_user.go
func (h *AuthHandler) ResolveUserIDsHandler(w http.ResponseWriter, r *http.Request) {
	var emails []string
	if err := json.NewDecoder(r.Body).Decode(&emails); err != nil {
		http.Error(w, "bad request", http.StatusBadRequest)
		return
	}
	//log.Println("ResolveUserIDsHandler started... good request")
	//	fmt.Println("emails: ", emails)

	result, err := h.service.ResolveUserIDs(r.Context(), emails)
	fmt.Println("result: ", result)
	if err != nil {
		http.Error(w, "failed, error : "+err.Error(), http.StatusInternalServerError)
		return
	}

	//log.Println("ResolveUserIDsHandler finished...")

	json.NewEncoder(w).Encode(result)
}
