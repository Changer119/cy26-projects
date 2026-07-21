package com.phone2computer.transfer.ui;

import android.Manifest;
import android.annotation.SuppressLint;
import android.app.Activity;
import android.content.BroadcastReceiver;
import android.content.ClipData;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.provider.Settings;
import android.widget.Button;
import android.widget.EditText;
import android.widget.ListView;
import android.widget.TextView;
import android.widget.Toast;
import com.phone2computer.transfer.R;
import com.phone2computer.transfer.core.PairingConfig;
import com.phone2computer.transfer.core.UploadState;
import com.phone2computer.transfer.core.UploadTask;
import com.phone2computer.transfer.data.ContentInspector;
import com.phone2computer.transfer.data.PairingPreferences;
import com.phone2computer.transfer.data.UploadJournal;
import com.phone2computer.transfer.service.UploadService;
import com.phone2computer.transfer.service.UploadProgressRegistry;
import com.phone2computer.transfer.util.FileLogger;
import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

public final class MainActivity extends Activity {
    private static final int REQUEST_FILES = 1001;
    private static final int REQUEST_NOTIFICATIONS = 1002;
    private PairingPreferences pairingPreferences;
    private UploadJournal journal;
    private ContentInspector inspector;
    private FileLogger logger;
    private UploadListAdapter adapter;
    private EditText pairingInput;
    private TextView pairingStatus;
    private TextView queueSummary;
    private final BroadcastReceiver statusReceiver = new BroadcastReceiver() {
        @Override
        public void onReceive(Context context, Intent intent) {
            refresh();
        }
    };

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        setContentView(R.layout.activity_main);
        pairingPreferences = new PairingPreferences(this);
        journal = new UploadJournal(new File(getFilesDir(), "uploads/tasks.journal"));
        inspector = new ContentInspector(getContentResolver());
        logger = new FileLogger(this);
        bindViews();
        handlePairingIntent(getIntent());
        requestNotificationPermission();
        refresh();
    }

    private void bindViews() {
        pairingInput = findViewById(R.id.pairing_input);
        pairingStatus = findViewById(R.id.pairing_status);
        queueSummary = findViewById(R.id.queue_summary);
        adapter = new UploadListAdapter(this);
        ((ListView) findViewById(R.id.upload_list)).setAdapter(adapter);

        ((Button) findViewById(R.id.connect_button)).setOnClickListener(view -> savePairing(
            pairingInput.getText().toString()
        ));
        ((Button) findViewById(R.id.choose_button)).setOnClickListener(view -> chooseFiles());
        ((Button) findViewById(R.id.resume_button)).setOnClickListener(
            view -> startServiceAction(UploadService.ACTION_START)
        );
        ((Button) findViewById(R.id.pause_button)).setOnClickListener(
            view -> startServiceAction(UploadService.ACTION_PAUSE)
        );
        ((Button) findViewById(R.id.retry_button)).setOnClickListener(
            view -> startServiceAction(UploadService.ACTION_RETRY)
        );
        ((Button) findViewById(R.id.battery_button)).setOnClickListener(
            view -> openBatterySettings()
        );
    }

    private void savePairing(String value) {
        try {
            PairingConfig config = PairingConfig.parse(value);
            pairingPreferences.save(config);
            pairingInput.setText("");
            toast("已连接到 Mac");
            refresh();
        } catch (IllegalArgumentException error) {
            toast(error.getMessage());
        }
    }

    private void handlePairingIntent(Intent intent) {
        Uri data = intent == null ? null : intent.getData();
        if (data != null && "phone2computer".equalsIgnoreCase(data.getScheme())) {
            savePairing(data.toString());
        }
    }

    private void chooseFiles() {
        if (pairingPreferences.load().isEmpty()) {
            toast("请先从扫码页面打开 App，或粘贴配对链接");
            return;
        }
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT)
            .setType("*/*")
            .putExtra(Intent.EXTRA_MIME_TYPES, new String[] {"image/*", "video/*"})
            .putExtra(Intent.EXTRA_ALLOW_MULTIPLE, true)
            .addCategory(Intent.CATEGORY_OPENABLE)
            .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            .addFlags(Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION);
        startActivityForResult(intent, REQUEST_FILES);
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode != REQUEST_FILES || resultCode != RESULT_OK || data == null) {
            return;
        }
        List<Uri> uris = selectedUris(data);
        int accepted = 0;
        for (Uri uri : uris) {
            try {
                getContentResolver().takePersistableUriPermission(
                    uri,
                    Intent.FLAG_GRANT_READ_URI_PERMISSION
                );
                journal.save(inspector.inspect(uri));
                accepted++;
            } catch (Exception error) {
                logger.error("无法加入文件：" + uri, error);
            }
        }
        toast("已加入 " + accepted + " 个文件");
        refresh();
        if (accepted > 0) {
            startServiceAction(UploadService.ACTION_START);
        }
    }

    private static List<Uri> selectedUris(Intent data) {
        List<Uri> uris = new ArrayList<>();
        ClipData clips = data.getClipData();
        if (clips != null) {
            for (int index = 0; index < clips.getItemCount(); index++) {
                uris.add(clips.getItemAt(index).getUri());
            }
        } else if (data.getData() != null) {
            uris.add(data.getData());
        }
        return uris;
    }

    private void startServiceAction(String action) {
        if (pairingPreferences.load().isEmpty()) {
            toast("尚未连接 Mac");
            return;
        }
        Intent intent = new Intent(this, UploadService.class).setAction(action);
        startForegroundService(intent);
    }

    private void refresh() {
        pairingStatus.setText(pairingPreferences.load()
            .map(config -> "已连接：" + config.serverOrigin())
            .orElse("尚未连接 Mac"));
        try {
            List<UploadTask> tasks = journal.list();
            long completed = tasks.stream()
                .filter(task -> task.state() == UploadState.COMPLETED)
                .count();
            long failed = tasks.stream()
                .filter(task -> task.state() == UploadState.FAILED)
                .count();
            long totalBytes = tasks.stream().mapToLong(UploadTask::length).sum();
            long uploadedBytes = tasks.stream()
                .mapToLong(UploadProgressRegistry::uploadedBytes)
                .sum();
            int progress = totalBytes == 0L
                ? 0
                : (int) Math.min(100L, uploadedBytes * 100L / totalBytes);
            queueSummary.setText(getString(
                R.string.queue_summary,
                tasks.size(),
                completed,
                failed,
                progress
            ));
            adapter.replace(tasks);
        } catch (IOException error) {
            queueSummary.setText("读取任务列表失败");
            logger.error("刷新任务列表失败", error);
        }
    }

    private void openBatterySettings() {
        startActivity(new Intent(Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS));
        toast("请允许 Phone2Computer 后台活动，并将应用启动设为手动管理");
    }

    private void requestNotificationPermission() {
        if (
            Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU
                && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)
                    != PackageManager.PERMISSION_GRANTED
        ) {
            requestPermissions(
                new String[] {Manifest.permission.POST_NOTIFICATIONS},
                REQUEST_NOTIFICATIONS
            );
        }
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        handlePairingIntent(intent);
    }

    @Override
    @SuppressLint("UnspecifiedRegisterReceiverFlag")
    protected void onStart() {
        super.onStart();
        IntentFilter filter = new IntentFilter(UploadService.ACTION_STATUS);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            registerReceiver(statusReceiver, filter, RECEIVER_NOT_EXPORTED);
        } else {
            registerReceiver(statusReceiver, filter);
        }
    }

    @Override
    protected void onStop() {
        unregisterReceiver(statusReceiver);
        super.onStop();
    }

    private void toast(String message) {
        Toast.makeText(this, message, Toast.LENGTH_LONG).show();
    }
}
