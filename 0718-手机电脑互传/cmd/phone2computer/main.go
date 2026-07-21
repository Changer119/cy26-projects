package main

import (
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"time"

	"phone2computer/internal/auth"
	localnetwork "phone2computer/internal/network"
	"phone2computer/internal/server"
	"phone2computer/internal/upload"
)

func main() {
	homeDirectory, err := os.UserHomeDir()
	if err != nil {
		log.Fatal(err)
	}
	defaultOutput := filepath.Join(homeDirectory, "Downloads", "Phone2Computer")
	outputDirectory := flag.String("output", defaultOutput, "接收文件保存目录")
	port := flag.Int("port", 18765, "监听端口")
	flag.Parse()

	logger := log.New(os.Stdout, "phone2computer ", log.Ldate|log.Ltime|log.Lmicroseconds)
	session, err := auth.NewSession()
	if err != nil {
		logger.Fatal(err)
	}
	batchName := time.Now().Format("2006-01-02_150405") + "_华为P40Pro"
	manager, err := upload.NewManager(*outputDirectory, batchName)
	if err != nil {
		logger.Fatal(err)
	}
	assets, err := server.Assets()
	if err != nil {
		logger.Fatal(err)
	}
	localAddress, err := localnetwork.LocalIPv4()
	if err != nil {
		logger.Fatal(err)
	}
	publicURL := localnetwork.PublicURL(localAddress, *port)
	handler := server.New(server.Config{
		Session:         session,
		Uploads:         manager,
		PublicURL:       publicURL,
		OutputDirectory: *outputDirectory,
		Assets:          assets,
	})
	httpServer := &http.Server{
		Addr:              fmt.Sprintf(":%d", *port),
		Handler:           handler,
		ReadHeaderTimeout: 5 * time.Second,
		IdleTimeout:       2 * time.Minute,
		MaxHeaderBytes:    1 << 20,
	}

	logger.Printf("管理页面：http://127.0.0.1:%d/admin", *port)
	logger.Printf("手机访问：%s", publicURL)
	logger.Printf("接收目录：%s", *outputDirectory)
	if err := httpServer.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		logger.Fatal(err)
	}
}
