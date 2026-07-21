package server

import (
	"encoding/base64"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"testing/fstest"

	"phone2computer/internal/auth"
	"phone2computer/internal/upload"
)

func TestUploadCreationRequiresBearerToken(t *testing.T) {
	session, err := auth.NewSession()
	if err != nil {
		t.Fatal(err)
	}
	manager, err := upload.NewManager(t.TempDir(), "batch")
	if err != nil {
		t.Fatal(err)
	}
	handler := New(Config{Session: session, Uploads: manager})
	request := httptest.NewRequest(http.MethodPost, "/api/files/", nil)
	response := httptest.NewRecorder()

	handler.ServeHTTP(response, request)

	if response.Code != http.StatusUnauthorized {
		t.Fatalf("状态码 = %d，期望 %d", response.Code, http.StatusUnauthorized)
	}
}

func TestStaticHandlerFallsBackToReactIndex(t *testing.T) {
	handler := New(Config{Assets: fstest.MapFS{
		"index.html": &fstest.MapFile{Data: []byte("<main>Phone2Computer</main>")},
	}})
	request := httptest.NewRequest(http.MethodGet, "/admin", nil)
	response := httptest.NewRecorder()

	handler.ServeHTTP(response, request)

	body, err := io.ReadAll(response.Body)
	if err != nil {
		t.Fatal(err)
	}
	if response.Code != http.StatusOK || !strings.Contains(string(body), "Phone2Computer") {
		t.Fatalf("静态回退失败：code=%d body=%s", response.Code, body)
	}
}

func TestAdminConfigReturnsPairingURLToLocalRequest(t *testing.T) {
	session, err := auth.NewSession()
	if err != nil {
		t.Fatal(err)
	}
	handler := New(Config{
		Session:         session,
		PublicURL:       "http://192.168.1.20:8765",
		OutputDirectory: "/Users/test/Downloads/Phone2Computer",
	})
	request := httptest.NewRequest(http.MethodGet, "/api/admin/config", nil)
	request.RemoteAddr = "127.0.0.1:54321"
	response := httptest.NewRecorder()

	handler.ServeHTTP(response, request)

	if response.Code != http.StatusOK {
		t.Fatalf("状态码 = %d，期望 200", response.Code)
	}
	var payload struct {
		UploadURL       string `json:"upload_url"`
		OutputDirectory string `json:"output_directory"`
	}
	if err := json.NewDecoder(response.Body).Decode(&payload); err != nil {
		t.Fatal(err)
	}
	wantURL := "http://192.168.1.20:8765/?token=" + session.Token()
	if payload.UploadURL != wantURL || payload.OutputDirectory != "/Users/test/Downloads/Phone2Computer" {
		t.Fatalf("管理配置不匹配：%+v", payload)
	}
}

func TestTusOptionsAdvertisesCreationExtension(t *testing.T) {
	session, err := auth.NewSession()
	if err != nil {
		t.Fatal(err)
	}
	manager, err := upload.NewManager(t.TempDir(), "batch")
	if err != nil {
		t.Fatal(err)
	}
	handler := New(Config{Session: session, Uploads: manager})
	request := httptest.NewRequest(http.MethodOptions, "/api/files/", nil)
	response := httptest.NewRecorder()

	handler.ServeHTTP(response, request)

	if response.Code != http.StatusNoContent {
		t.Fatalf("状态码 = %d，期望 204", response.Code)
	}
	if response.Header().Get("Tus-Extension") != "creation" {
		t.Fatalf("Tus-Extension = %q", response.Header().Get("Tus-Extension"))
	}
}

func TestHealthEndpointIsPublic(t *testing.T) {
	handler := New(Config{})
	request := httptest.NewRequest(http.MethodGet, "/health", nil)
	response := httptest.NewRecorder()

	handler.ServeHTTP(response, request)

	if response.Code != http.StatusOK || response.Header().Get("Content-Type") != "application/json" {
		t.Fatalf("健康检查响应不正确：code=%d headers=%v", response.Code, response.Header())
	}
}

func TestAdminConfigRejectsNonLocalRequest(t *testing.T) {
	handler := New(Config{})
	request := httptest.NewRequest(http.MethodGet, "/api/admin/config", nil)
	request.RemoteAddr = "192.168.1.50:54321"
	response := httptest.NewRecorder()

	handler.ServeHTTP(response, request)

	if response.Code != http.StatusForbidden {
		t.Fatalf("状态码 = %d，期望 403", response.Code)
	}
}

func TestTusPatchAppendsAndCompletesUpload(t *testing.T) {
	session, err := auth.NewSession()
	if err != nil {
		t.Fatal(err)
	}
	manager, err := upload.NewManager(t.TempDir(), "batch")
	if err != nil {
		t.Fatal(err)
	}
	created, err := manager.Create(upload.Metadata{Name: "IMG_004.jpg", Length: 5})
	if err != nil {
		t.Fatal(err)
	}
	handler := New(Config{Session: session, Uploads: manager})
	request := httptest.NewRequest(http.MethodPatch, "/api/files/"+created.ID, strings.NewReader("photo"))
	request.Header.Set("Authorization", "Bearer "+session.Token())
	request.Header.Set("Tus-Resumable", "1.0.0")
	request.Header.Set("Upload-Offset", "0")
	request.Header.Set("Content-Type", "application/offset+octet-stream")
	response := httptest.NewRecorder()

	handler.ServeHTTP(response, request)

	if response.Code != http.StatusNoContent {
		t.Fatalf("状态码 = %d，期望 204；响应：%s", response.Code, response.Body.String())
	}
	if response.Header().Get("Upload-Offset") != "5" {
		t.Fatalf("Upload-Offset = %q，期望 5", response.Header().Get("Upload-Offset"))
	}
	completed, err := manager.Get(created.ID)
	if err != nil || !completed.Complete {
		t.Fatalf("任务应完成：%+v，错误：%v", completed, err)
	}
}

func TestTusCreationReturnsUploadLocation(t *testing.T) {
	session, err := auth.NewSession()
	if err != nil {
		t.Fatal(err)
	}
	manager, err := upload.NewManager(t.TempDir(), "batch")
	if err != nil {
		t.Fatal(err)
	}
	handler := New(Config{Session: session, Uploads: manager})
	request := httptest.NewRequest(http.MethodPost, "/api/files/", nil)
	request.Header.Set("Authorization", "Bearer "+session.Token())
	request.Header.Set("Tus-Resumable", "1.0.0")
	request.Header.Set("Upload-Length", "5")
	filename := base64.StdEncoding.EncodeToString([]byte("IMG_001.jpg"))
	modified := base64.StdEncoding.EncodeToString([]byte("1700000000000"))
	request.Header.Set("Upload-Metadata", "filename "+filename+",lastmodified "+modified)
	response := httptest.NewRecorder()

	handler.ServeHTTP(response, request)

	if response.Code != http.StatusCreated {
		t.Fatalf("状态码 = %d，期望 201；响应：%s", response.Code, response.Body.String())
	}
	location := response.Header().Get("Location")
	if location == "" {
		t.Fatal("创建上传后必须返回 Location")
	}
	id := location[len("/api/files/"):]
	created, err := manager.Get(id)
	if err != nil {
		t.Fatalf("无法查询新任务：%v", err)
	}
	if created.Name != "IMG_001.jpg" || created.Length != 5 {
		t.Fatalf("任务元数据不匹配：%+v", created)
	}
}

func TestTusHeadReportsCurrentOffset(t *testing.T) {
	session, err := auth.NewSession()
	if err != nil {
		t.Fatal(err)
	}
	manager, err := upload.NewManager(t.TempDir(), "batch")
	if err != nil {
		t.Fatal(err)
	}
	created, err := manager.Create(upload.Metadata{Name: "VID_001.mp4", Length: 10})
	if err != nil {
		t.Fatal(err)
	}
	handler := New(Config{Session: session, Uploads: manager})
	request := httptest.NewRequest(http.MethodHead, "/api/files/"+created.ID, nil)
	request.Header.Set("Authorization", "Bearer "+session.Token())
	request.Header.Set("Tus-Resumable", "1.0.0")
	response := httptest.NewRecorder()

	handler.ServeHTTP(response, request)

	if response.Code != http.StatusOK {
		t.Fatalf("状态码 = %d，期望 200", response.Code)
	}
	if response.Header().Get("Upload-Offset") != "0" || response.Header().Get("Upload-Length") != "10" {
		t.Fatalf("上传头不匹配：%v", response.Header())
	}
}
