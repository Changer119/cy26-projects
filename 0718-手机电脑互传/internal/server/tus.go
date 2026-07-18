package server

import (
	"encoding/base64"
	"errors"
	"net/http"
	"strconv"
	"strings"
	"time"

	"phone2computer/internal/upload"
)

const tusVersion = "1.0.0"

func handleTus(manager *upload.Manager, response http.ResponseWriter, request *http.Request) {
	response.Header().Set("Tus-Resumable", tusVersion)
	if request.Method == http.MethodOptions {
		response.Header().Set("Tus-Version", tusVersion)
		response.Header().Set("Tus-Extension", "creation")
		response.WriteHeader(http.StatusNoContent)
		return
	}
	if request.Method == http.MethodPost && request.URL.Path == "/api/files/" {
		createUpload(manager, response, request)
		return
	}
	if request.Method == http.MethodHead {
		writeUploadHead(manager, response, strings.TrimPrefix(request.URL.Path, "/api/files/"))
		return
	}
	if request.Method == http.MethodPatch {
		appendUpload(manager, response, request, strings.TrimPrefix(request.URL.Path, "/api/files/"))
		return
	}
	http.Error(response, "方法不支持", http.StatusMethodNotAllowed)
}

func createUpload(manager *upload.Manager, response http.ResponseWriter, request *http.Request) {
	length, err := strconv.ParseInt(request.Header.Get("Upload-Length"), 10, 64)
	if err != nil || length < 0 {
		http.Error(response, "Upload-Length 无效", http.StatusBadRequest)
		return
	}
	metadata, err := decodeMetadata(request.Header.Get("Upload-Metadata"))
	if err != nil || metadata.filename == "" {
		http.Error(response, "Upload-Metadata 无效", http.StatusBadRequest)
		return
	}
	created, err := manager.Create(upload.Metadata{
		Name:       metadata.filename,
		Length:     length,
		ModifiedAt: metadata.modifiedAt,
	})
	if err != nil {
		http.Error(response, err.Error(), http.StatusBadRequest)
		return
	}
	response.Header().Set("Location", "/api/files/"+created.ID)
	response.WriteHeader(http.StatusCreated)
}

type tusMetadata struct {
	filename   string
	modifiedAt time.Time
}

func writeUploadHead(manager *upload.Manager, response http.ResponseWriter, id string) {
	snapshot, err := manager.Get(id)
	if err != nil {
		http.Error(response, "上传任务不存在", http.StatusNotFound)
		return
	}
	response.Header().Set("Upload-Offset", strconv.FormatInt(snapshot.Offset, 10))
	response.Header().Set("Upload-Length", strconv.FormatInt(snapshot.Length, 10))
	response.WriteHeader(http.StatusOK)
}

func appendUpload(manager *upload.Manager, response http.ResponseWriter, request *http.Request, id string) {
	offset, err := strconv.ParseInt(request.Header.Get("Upload-Offset"), 10, 64)
	if err != nil || offset < 0 {
		http.Error(response, "Upload-Offset 无效", http.StatusBadRequest)
		return
	}
	updated, err := manager.Append(id, offset, request.Body)
	if errors.Is(err, upload.ErrUploadNotFound) {
		http.Error(response, err.Error(), http.StatusNotFound)
		return
	}
	if errors.Is(err, upload.ErrOffsetMismatch) {
		http.Error(response, err.Error(), http.StatusConflict)
		return
	}
	if err != nil {
		http.Error(response, err.Error(), http.StatusBadRequest)
		return
	}
	response.Header().Set("Upload-Offset", strconv.FormatInt(updated.Offset, 10))
	response.WriteHeader(http.StatusNoContent)
}

func decodeMetadata(header string) (tusMetadata, error) {
	metadata := tusMetadata{}
	for _, item := range strings.Split(header, ",") {
		parts := strings.SplitN(strings.TrimSpace(item), " ", 2)
		if len(parts) != 2 {
			continue
		}
		decoded, err := base64.StdEncoding.DecodeString(parts[1])
		if err != nil {
			return tusMetadata{}, err
		}
		switch parts[0] {
		case "filename":
			metadata.filename = string(decoded)
		case "lastmodified":
			milliseconds, err := strconv.ParseInt(string(decoded), 10, 64)
			if err != nil {
				return tusMetadata{}, err
			}
			metadata.modifiedAt = time.UnixMilli(milliseconds)
		}
	}
	if metadata.filename == "" {
		return tusMetadata{}, errors.New("缺少 filename")
	}
	return metadata, nil
}
