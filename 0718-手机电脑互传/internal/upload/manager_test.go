package upload

import (
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func TestManagerAppendsChunkAtExpectedOffset(t *testing.T) {
	manager, err := NewManager(t.TempDir(), "2026-07-18_华为P40Pro")
	if err != nil {
		t.Fatal(err)
	}
	upload, err := manager.Create(Metadata{
		Name:       "VID_001.mp4",
		Length:     11,
		ModifiedAt: time.Unix(1_700_000_000, 0),
	})
	if err != nil {
		t.Fatal(err)
	}

	updated, err := manager.Append(upload.ID, 0, strings.NewReader("hello"))
	if err != nil {
		t.Fatalf("Append 返回错误：%v", err)
	}
	if updated.Offset != 5 {
		t.Fatalf("偏移量 = %d，期望 5", updated.Offset)
	}
	if updated.Complete {
		t.Fatal("只上传部分内容时不应完成")
	}
}

func TestManagerDoesNotCreateEmptyBatchDirectory(t *testing.T) {
	root := t.TempDir()
	if _, err := NewManager(root, "unused-batch"); err != nil {
		t.Fatal(err)
	}
	_, err := os.Stat(filepath.Join(root, "unused-batch"))
	if !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("没有文件完成时不应创建批次目录：%v", err)
	}
}

func TestManagerRejectsWrongOffset(t *testing.T) {
	manager, err := NewManager(t.TempDir(), "batch")
	if err != nil {
		t.Fatal(err)
	}
	upload, err := manager.Create(Metadata{Name: "VID_002.mp4", Length: 5})
	if err != nil {
		t.Fatal(err)
	}

	_, err = manager.Append(upload.ID, 3, strings.NewReader("x"))
	if !errors.Is(err, ErrOffsetMismatch) {
		t.Fatalf("错误 = %v，期望 ErrOffsetMismatch", err)
	}
}

func TestManagerMovesCompletedUploadIntoBatch(t *testing.T) {
	root := t.TempDir()
	manager, err := NewManager(root, "2026-07-18_华为P40Pro")
	if err != nil {
		t.Fatal(err)
	}
	modifiedAt := time.Unix(1_700_000_000, 0)
	upload, err := manager.Create(Metadata{Name: "IMG_001.jpg", Length: 5, ModifiedAt: modifiedAt})
	if err != nil {
		t.Fatal(err)
	}

	completed, err := manager.Append(upload.ID, 0, strings.NewReader("photo"))
	if err != nil {
		t.Fatal(err)
	}
	if !completed.Complete {
		t.Fatal("上传达到声明长度后应完成")
	}
	wantPath := filepath.Join(root, "2026-07-18_华为P40Pro", "IMG_001.jpg")
	if completed.Path != wantPath {
		t.Fatalf("落盘路径 = %q，期望 %q", completed.Path, wantPath)
	}
	content, err := os.ReadFile(wantPath)
	if err != nil {
		t.Fatal(err)
	}
	if string(content) != "photo" {
		t.Fatalf("文件内容 = %q，期望 photo", content)
	}
}

func TestManagerRejectsChunkBeyondDeclaredLength(t *testing.T) {
	manager, err := NewManager(t.TempDir(), "batch")
	if err != nil {
		t.Fatal(err)
	}
	upload, err := manager.Create(Metadata{Name: "IMG_002.jpg", Length: 3})
	if err != nil {
		t.Fatal(err)
	}

	if _, err := manager.Append(upload.ID, 0, strings.NewReader("four")); err == nil {
		t.Fatal("超过声明长度的分片应被拒绝")
	}
	completed, err := manager.Append(upload.ID, 0, strings.NewReader("yes"))
	if err != nil {
		t.Fatalf("拒绝超长分片后应仍可重试：%v", err)
	}
	if !completed.Complete {
		t.Fatal("重试正确内容后应完成")
	}
}

func TestManagerReturnsUploadSnapshot(t *testing.T) {
	manager, err := NewManager(t.TempDir(), "batch")
	if err != nil {
		t.Fatal(err)
	}
	created, err := manager.Create(Metadata{Name: "IMG_003.jpg", Length: 9})
	if err != nil {
		t.Fatal(err)
	}

	got, err := manager.Get(created.ID)
	if err != nil {
		t.Fatalf("Get 返回错误：%v", err)
	}
	if got.ID != created.ID || got.Name != "IMG_003.jpg" || got.Length != 9 {
		t.Fatalf("快照不匹配：%+v", got)
	}
	if _, err := manager.Get("missing"); !errors.Is(err, ErrUploadNotFound) {
		t.Fatalf("未知任务错误 = %v", err)
	}
}
