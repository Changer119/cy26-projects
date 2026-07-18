package server

import (
	"embed"
	"io/fs"
)

//go:embed static
var embeddedAssets embed.FS

func Assets() (fs.FS, error) {
	return fs.Sub(embeddedAssets, "static")
}
