package com.phone2computer.transfer.transfer;

import java.io.IOException;

public interface ContentSource {
    byte[] read(String contentUri, long offset, int maximumLength) throws IOException;
}
