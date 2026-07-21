package com.phone2computer.transfer.ui;

import android.content.Context;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.BaseAdapter;
import android.widget.ProgressBar;
import android.widget.TextView;
import com.phone2computer.transfer.R;
import com.phone2computer.transfer.core.UploadState;
import com.phone2computer.transfer.core.UploadTask;
import com.phone2computer.transfer.service.UploadProgressRegistry;
import java.util.ArrayList;
import java.util.List;

public final class UploadListAdapter extends BaseAdapter {
    private final LayoutInflater inflater;
    private List<UploadTask> tasks = new ArrayList<>();

    public UploadListAdapter(Context context) {
        inflater = LayoutInflater.from(context);
    }

    public void replace(List<UploadTask> nextTasks) {
        tasks = new ArrayList<>(nextTasks.subList(0, Math.min(100, nextTasks.size())));
        notifyDataSetChanged();
    }

    @Override
    public int getCount() {
        return tasks.size();
    }

    @Override
    public UploadTask getItem(int position) {
        return tasks.get(position);
    }

    @Override
    public long getItemId(int position) {
        return getItem(position).id().hashCode();
    }

    @Override
    public View getView(int position, View convertView, ViewGroup parent) {
        View view = convertView;
        ViewHolder holder;
        if (view == null) {
            view = inflater.inflate(R.layout.item_upload, parent, false);
            holder = new ViewHolder(
                view.findViewById(R.id.file_name),
                view.findViewById(R.id.file_state),
                view.findViewById(R.id.file_progress)
            );
            view.setTag(holder);
        } else {
            holder = (ViewHolder) view.getTag();
        }
        UploadTask task = getItem(position);
        int progress = UploadProgressRegistry.progressPercent(task);
        holder.name.setText(task.filename());
        holder.state.setText(stateLabel(task.state(), task.errorMessage(), progress));
        holder.progress.setProgress(progress);
        return view;
    }

    private static String stateLabel(UploadState state, String error, int progress) {
        return switch (state) {
            case PENDING -> "等待中";
            case UPLOADING -> "传输中 · " + progress + "%";
            case PAUSED -> "已暂停";
            case COMPLETED -> "已完成";
            case FAILED -> error.isBlank() ? "失败" : "失败：" + error;
        };
    }

    private static final class ViewHolder {
        private final TextView name;
        private final TextView state;
        private final ProgressBar progress;

        private ViewHolder(TextView name, TextView state, ProgressBar progress) {
            this.name = name;
            this.state = state;
            this.progress = progress;
        }
    }
}
