package upload

import "time"

type Metadata struct {
	Name       string
	Length     int64
	ModifiedAt time.Time
}

type Snapshot struct {
	ID       string
	Name     string
	Length   int64
	Offset   int64
	Complete bool
	Path     string
}
