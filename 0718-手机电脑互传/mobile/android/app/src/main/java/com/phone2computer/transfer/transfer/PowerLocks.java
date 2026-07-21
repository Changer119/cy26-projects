package com.phone2computer.transfer.transfer;

import android.annotation.SuppressLint;
import android.content.Context;
import android.net.wifi.WifiManager;
import android.os.PowerManager;

@SuppressWarnings("deprecation")
public final class PowerLocks {
    private final PowerManager.WakeLock wakeLock;
    private final WifiManager.WifiLock wifiLock;

    public PowerLocks(Context context) {
        PowerManager power = context.getSystemService(PowerManager.class);
        WifiManager wifi = context.getApplicationContext().getSystemService(WifiManager.class);
        wakeLock = power.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "phone2computer:upload");
        wifiLock = wifi.createWifiLock(WifiManager.WIFI_MODE_FULL_HIGH_PERF, "phone2computer:upload");
        wakeLock.setReferenceCounted(false);
        wifiLock.setReferenceCounted(false);
    }

    @SuppressLint("WakelockTimeout")
    public void acquire() {
        if (!wakeLock.isHeld()) {
            wakeLock.acquire();
        }
        if (!wifiLock.isHeld()) {
            wifiLock.acquire();
        }
    }

    public void release() {
        if (wifiLock.isHeld()) {
            wifiLock.release();
        }
        if (wakeLock.isHeld()) {
            wakeLock.release();
        }
    }
}
