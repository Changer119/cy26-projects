package files

import (
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"unicode"
)

var ErrUnsafeName = errors.New("文件名不安全")

func SafeName(raw string) (string, error) {
	name := strings.TrimSpace(raw)
	if name == "" || name == "." || name == ".." || strings.ContainsAny(name, `/\`) {
		return "", ErrUnsafeName
	}
	for _, character := range name {
		if unicode.IsControl(character) {
			return "", ErrUnsafeName
		}
	}
	return name, nil
}

func AvailablePath(directory string, name string) (string, error) {
	base := strings.TrimSuffix(name, filepath.Ext(name))
	extension := filepath.Ext(name)
	for sequence := 0; ; sequence++ {
		candidateName := name
		if sequence > 0 {
			candidateName = fmt.Sprintf("%s (%d)%s", base, sequence, extension)
		}
		candidate := filepath.Join(directory, candidateName)
		_, err := os.Lstat(candidate)
		if errors.Is(err, os.ErrNotExist) {
			return candidate, nil
		}
		if err != nil {
			return "", err
		}
	}
}
