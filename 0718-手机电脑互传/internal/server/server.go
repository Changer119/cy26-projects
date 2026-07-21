package server

import (
	"encoding/json"
	"io/fs"
	"net"
	"net/http"
	"strings"

	"phone2computer/internal/auth"
	"phone2computer/internal/upload"
)

type Config struct {
	Session         *auth.Session
	Uploads         *upload.Manager
	PublicURL       string
	OutputDirectory string
	Assets          fs.FS
}

func New(config Config) http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", func(response http.ResponseWriter, request *http.Request) {
		response.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(response).Encode(healthResponse{Status: "ok"})
	})
	mux.HandleFunc("GET /api/admin/config", func(response http.ResponseWriter, request *http.Request) {
		if !isLoopback(request.RemoteAddr) {
			http.Error(response, "管理页面仅允许本机访问", http.StatusForbidden)
			return
		}
		if config.Session == nil {
			http.Error(response, "服务未配置", http.StatusInternalServerError)
			return
		}
		response.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(response).Encode(adminConfigResponse{
			UploadURL:       config.PublicURL + "/?token=" + config.Session.Token(),
			OutputDirectory: config.OutputDirectory,
		})
	})
	tusHandler := http.HandlerFunc(func(response http.ResponseWriter, request *http.Request) {
		handleTus(config.Uploads, response, request)
	})
	mux.Handle("/api/files/", tusAccess(config.Session, tusHandler))
	mux.Handle("/", staticHandler(config.Assets))
	return mux
}

func staticHandler(assets fs.FS) http.Handler {
	if assets == nil {
		return http.NotFoundHandler()
	}
	fileServer := http.FileServerFS(assets)
	return http.HandlerFunc(func(response http.ResponseWriter, request *http.Request) {
		name := strings.TrimPrefix(request.URL.Path, "/")
		if name == "" {
			name = "index.html"
		}
		if _, err := fs.Stat(assets, name); err != nil {
			name = "index.html"
		}
		cloned := request.Clone(request.Context())
		urlCopy := *request.URL
		urlCopy.Path = "/" + name
		if name == "index.html" {
			urlCopy.Path = "/"
		}
		cloned.URL = &urlCopy
		fileServer.ServeHTTP(response, cloned)
	})
}

func isLoopback(remoteAddress string) bool {
	host, _, err := net.SplitHostPort(remoteAddress)
	if err != nil {
		return false
	}
	address := net.ParseIP(host)
	return address != nil && address.IsLoopback()
}

type healthResponse struct {
	Status string `json:"status"`
}

type adminConfigResponse struct {
	UploadURL       string `json:"upload_url"`
	OutputDirectory string `json:"output_directory"`
}

func tusAccess(session *auth.Session, next http.Handler) http.Handler {
	secured := requireAuth(session, next)
	return http.HandlerFunc(func(response http.ResponseWriter, request *http.Request) {
		if request.Method == http.MethodOptions {
			next.ServeHTTP(response, request)
			return
		}
		secured.ServeHTTP(response, request)
	})
}

func requireAuth(session *auth.Session, next http.Handler) http.Handler {
	return http.HandlerFunc(func(response http.ResponseWriter, request *http.Request) {
		if session == nil || !session.Authorize(request.Header.Get("Authorization")) {
			http.Error(response, "未授权", http.StatusUnauthorized)
			return
		}
		next.ServeHTTP(response, request)
	})
}
