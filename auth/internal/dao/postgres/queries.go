package postgres

/*
Only 2 main queries needed
sign up request
login validation
*/

const (
	CreateUserQuery = `INSERT INTO users(email, username, password_hash) VALUES ($1, $2, $3)`

	// never compare passwords in queries,, get hash and compare in backend urself
	GetUserByEmailQuery = `SELECT id, email, username, password_hash FROM users WHERE email = $1`
)
