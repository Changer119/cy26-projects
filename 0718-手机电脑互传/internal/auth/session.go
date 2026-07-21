package auth

import (
	"crypto/rand"
	"crypto/subtle"
	"encoding/base64"
	"strings"
)

type Session struct {
	token string
}

func NewSession() (*Session, error) {
	randomBytes := make([]byte, 32)
	if _, err := rand.Read(randomBytes); err != nil {
		return nil, err
	}
	return &Session{token: base64.RawURLEncoding.EncodeToString(randomBytes)}, nil
}

func (session *Session) Token() string {
	return session.token
}

func (session *Session) Authorize(header string) bool {
	const prefix = "Bearer "
	if !strings.HasPrefix(header, prefix) {
		return false
	}
	candidate := strings.TrimPrefix(header, prefix)
	if len(candidate) != len(session.token) {
		return false
	}
	return subtle.ConstantTimeCompare([]byte(candidate), []byte(session.token)) == 1
}
