package com.phone2computer.transfer.core;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertThrows;

import org.junit.Test;

public final class ChunkPlannerTest {
    @Test
    public void capsChunkAtRemainingBytes() {
        assertEquals(3L, ChunkPlanner.nextLength(7L, 10L, 8L));
    }

    @Test
    public void usesConfiguredChunkForLargeRemainder() {
        assertEquals(8L, ChunkPlanner.nextLength(4L, 100L, 8L));
    }

    @Test
    public void rejectsOffsetBeyondFile() {
        assertThrows(
            IllegalArgumentException.class,
            () -> ChunkPlanner.nextLength(11L, 10L, 8L)
        );
    }
}
