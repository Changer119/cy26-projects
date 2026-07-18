package files

import (
	"os"
	"path/filepath"
	"testing"
)

func TestSafeNameRejectsPathTraversal(t *testing.T) {
	unsafeNames := []string{"../secret.jpg", "DCIM/photo.jpg", `DCIM\photo.jpg`, ".", ".."}

	for _, name := range unsafeNames {
		if _, err := SafeName(name); err == nil {
			t.Fatalf("SafeName(%q) 应拒绝危险文件名", name)
		}
	}
}

func TestSafeNameKeepsHuaweiMediaName(t *testing.T) {
	got, err := SafeName(" IMG_20260718_153000.jpg ")
	if err != nil {
		t.Fatalf("SafeName 返回错误：%v", err)
	}
	if got != "IMG_20260718_153000.jpg" {
		t.Fatalf("文件名 = %q，期望去除首尾空格", got)
	}
}

func TestAvailablePathAddsSequenceWithoutOverwriting(t *testing.T) {
	directory := t.TempDir()
	existing := filepath.Join(directory, "VID_001.mp4")
	if err := os.WriteFile(existing, []byte("old"), 0o600); err != nil {
		t.Fatal(err)
	}

	got, err := AvailablePath(directory, "VID_001.mp4")
	if err != nil {
		t.Fatalf("AvailablePath 返回错误：%v", err)
	}
	want := filepath.Join(directory, "VID_001 (1).mp4")
	if got != want {
		t.Fatalf("路径 = %q，期望 %q", got, want)
	}
}
