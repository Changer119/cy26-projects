package upload

import (
	"crypto/rand"
	"encoding/hex"
	"errors"
	"io"
	"os"
	"path/filepath"
	"sync"

	projectfiles "phone2computer/internal/files"
)

var (
	ErrInvalidLength  = errors.New("文件大小无效")
	ErrUploadNotFound = errors.New("上传任务不存在")
	ErrOffsetMismatch = errors.New("上传偏移量不匹配")
	ErrChunkTooLarge  = errors.New("分片超过声明的文件大小")
)

type record struct {
	metadata Metadata
	snapshot Snapshot
	tempPath string
	mutex    sync.Mutex
}

type Manager struct {
	incomingDir string
	batchDir    string
	records     map[string]*record
	mutex       sync.RWMutex
	finalize    sync.Mutex
}

func NewManager(outputRoot string, batchName string) (*Manager, error) {
	batchDir := filepath.Join(outputRoot, batchName)
	incomingDir := filepath.Join(outputRoot, ".phone2computer-incoming")
	if err := os.MkdirAll(incomingDir, 0o750); err != nil {
		return nil, err
	}
	return &Manager{
		incomingDir: incomingDir,
		batchDir:    batchDir,
		records:     make(map[string]*record),
	}, nil
}

func (manager *Manager) Create(metadata Metadata) (Snapshot, error) {
	name, err := projectfiles.SafeName(metadata.Name)
	if err != nil {
		return Snapshot{}, err
	}
	if metadata.Length < 0 {
		return Snapshot{}, ErrInvalidLength
	}
	metadata.Name = name
	id, err := randomID()
	if err != nil {
		return Snapshot{}, err
	}
	tempPath := filepath.Join(manager.incomingDir, id+".part")
	file, err := os.OpenFile(tempPath, os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0o600)
	if err != nil {
		return Snapshot{}, err
	}
	if err := file.Close(); err != nil {
		return Snapshot{}, err
	}
	snapshot := Snapshot{ID: id, Name: name, Length: metadata.Length}
	manager.mutex.Lock()
	manager.records[id] = &record{metadata: metadata, snapshot: snapshot, tempPath: tempPath}
	manager.mutex.Unlock()
	return snapshot, nil
}

func (manager *Manager) Append(id string, expectedOffset int64, reader io.Reader) (Snapshot, error) {
	manager.mutex.RLock()
	uploadRecord, exists := manager.records[id]
	manager.mutex.RUnlock()
	if !exists {
		return Snapshot{}, ErrUploadNotFound
	}

	uploadRecord.mutex.Lock()
	defer uploadRecord.mutex.Unlock()
	if uploadRecord.snapshot.Offset != expectedOffset {
		return Snapshot{}, ErrOffsetMismatch
	}
	file, err := os.OpenFile(uploadRecord.tempPath, os.O_WRONLY, 0o600)
	if err != nil {
		return Snapshot{}, err
	}
	if _, err := file.Seek(expectedOffset, io.SeekStart); err != nil {
		file.Close()
		return Snapshot{}, err
	}
	remaining := uploadRecord.snapshot.Length - expectedOffset
	written, err := io.Copy(file, io.LimitReader(reader, remaining+1))
	if err != nil {
		file.Close()
		return Snapshot{}, err
	}
	if written > remaining {
		if truncateErr := file.Truncate(expectedOffset); truncateErr != nil {
			file.Close()
			return Snapshot{}, truncateErr
		}
		file.Close()
		return Snapshot{}, ErrChunkTooLarge
	}
	if err := file.Close(); err != nil {
		return Snapshot{}, err
	}
	uploadRecord.snapshot.Offset += written
	if uploadRecord.snapshot.Offset == uploadRecord.snapshot.Length {
		manager.finalize.Lock()
		defer manager.finalize.Unlock()
		if err := os.MkdirAll(manager.batchDir, 0o750); err != nil {
			return Snapshot{}, err
		}
		finalPath, err := projectfiles.AvailablePath(manager.batchDir, uploadRecord.snapshot.Name)
		if err != nil {
			return Snapshot{}, err
		}
		if err := os.Rename(uploadRecord.tempPath, finalPath); err != nil {
			return Snapshot{}, err
		}
		if !uploadRecord.metadata.ModifiedAt.IsZero() {
			if err := os.Chtimes(finalPath, uploadRecord.metadata.ModifiedAt, uploadRecord.metadata.ModifiedAt); err != nil {
				return Snapshot{}, err
			}
		}
		uploadRecord.snapshot.Complete = true
		uploadRecord.snapshot.Path = finalPath
	}
	return uploadRecord.snapshot, nil
}

func (manager *Manager) Get(id string) (Snapshot, error) {
	manager.mutex.RLock()
	uploadRecord, exists := manager.records[id]
	manager.mutex.RUnlock()
	if !exists {
		return Snapshot{}, ErrUploadNotFound
	}
	uploadRecord.mutex.Lock()
	defer uploadRecord.mutex.Unlock()
	return uploadRecord.snapshot, nil
}

func randomID() (string, error) {
	randomBytes := make([]byte, 16)
	if _, err := rand.Read(randomBytes); err != nil {
		return "", err
	}
	return hex.EncodeToString(randomBytes), nil
}
