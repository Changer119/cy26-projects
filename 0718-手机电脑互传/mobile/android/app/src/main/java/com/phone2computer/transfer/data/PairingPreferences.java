package com.phone2computer.transfer.data;

import android.content.Context;
import android.content.SharedPreferences;
import com.phone2computer.transfer.core.PairingConfig;
import java.util.Optional;

public final class PairingPreferences {
    private static final String NAME = "pairing";
    private static final String SERVER = "server";
    private static final String TOKEN = "token";
    private final SharedPreferences preferences;

    public PairingPreferences(Context context) {
        preferences = context.getSharedPreferences(NAME, Context.MODE_PRIVATE);
    }

    public void save(PairingConfig config) {
        preferences.edit()
            .putString(SERVER, config.serverOrigin())
            .putString(TOKEN, config.token())
            .apply();
    }

    public Optional<PairingConfig> load() {
        String server = preferences.getString(SERVER, "");
        String token = preferences.getString(TOKEN, "");
        if (server == null || server.isBlank() || token == null || token.isBlank()) {
            return Optional.empty();
        }
        try {
            return Optional.of(new PairingConfig(server, token));
        } catch (IllegalArgumentException ignored) {
            return Optional.empty();
        }
    }
}
