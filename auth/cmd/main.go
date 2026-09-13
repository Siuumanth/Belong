package main

import (
	"auth/internal/dao/postgres"
	"auth/internal/database"
	"auth/internal/handler"
	"auth/internal/router"
	"auth/internal/service"
	"fmt"
	"net/http"
	"os"

	"github.com/joho/godotenv"
)

/*
Here we have to define all db, dao, service handlers, etc and connect them all
*/
func main() {
	godotenv.Load() // loads .env from root
	fmt.Println("Starting server...")
	dbURL := os.Getenv("AUTH_POSTGRES_URL_DEV")

	fmt.Println("DB URL:", dbURL)

	db, err := database.Connect(dbURL)
	if err != nil {
		fmt.Println("DB connection Erorr ")
		panic(err)
	}
	fmt.Println("Connected to database...")

	authDao := postgres.NewPostgresUserDAO(db)
	authService := service.NewAuthService(authDao)
	authHandler := handler.NewAuthHandler(authService)
	userRouter := router.NewRouter(authHandler)

	err = http.ListenAndServe(":9001", userRouter)
	if err != nil {
		fmt.Println("Error starting server")
		panic(err)
	}

}
