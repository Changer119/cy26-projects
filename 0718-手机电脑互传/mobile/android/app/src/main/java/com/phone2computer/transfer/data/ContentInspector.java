package com.phone2computer.transfer.data;

import android.content.ContentResolver;
import android.database.Cursor;
import android.net.Uri;
import android.provider.OpenableColumns;
import com.phone2computer.transfer.core.UploadTask;
import java.io.IOException;
import java.util.UUID;

public final class ContentInspector {
    private final ContentResolver resolver;

    public ContentInspector(ContentResolver resolver) {
        this.resolver = resolver;
    }

    public UploadTask inspect(Uri uri) throws IOException {
        String filename = uri.getLastPathSegment();
        long length = -1L;
        try (
            Cursor cursor = resolver.query(
                uri,
                new String[] {OpenableColumns.DISPLAY_NAME, OpenableColumns.SIZE},
                null,
                null,
                null
            )
        ) {
            if (cursor != null && cursor.moveToFirst()) {
                int nameColumn = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME);
                int sizeColumn = cursor.getColumnIndex(OpenableColumns.SIZE);
                if (nameColumn >= 0 && !cursor.isNull(nameColumn)) {
                    filename = cursor.getString(nameColumn);
                }
                if (sizeColumn >= 0 && !cursor.isNull(sizeColumn)) {
                    length = cursor.getLong(sizeColumn);
                }
            }
        }
        if (filename == null || filename.isBlank() || length < 0L) {
            throw new IOException("无法读取所选文件的信息");
        }
        return UploadTask.pending(
            UUID.randomUUID().toString(),
            uri.toString(),
            filename,
            length,
            System.currentTimeMillis()
        );
    }
}
