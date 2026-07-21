package server

import (
	"io/fs"
	"testing"
)

func TestEmbeddedAssetsAreAvailable(t *testing.T) {
	assets, err := Assets()
	if err != nil {
		t.Fatal(err)
	}
	entries, err := fs.ReadDir(assets, ".")
	if err != nil || len(entries) == 0 {
		t.Fatalf("嵌入资源为空：entries=%v err=%v", entries, err)
	}
}
