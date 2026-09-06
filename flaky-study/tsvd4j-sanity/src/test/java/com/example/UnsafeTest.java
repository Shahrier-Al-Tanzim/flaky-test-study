package com.example;

import java.util.ArrayList;
import java.util.Collection;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import org.junit.Test;

public class UnsafeTest {

    static Map<String, Integer> shared = new HashMap<>();
    static int counter = 0;          // plain field: exercises field tracking
    static Object lock = new Object();

    @Test
    public void twoWriters() throws Exception {
        Runnable r = () -> {
            for (int i = 0; i < 200; i++) {
                shared.put(Thread.currentThread().getName(), i);   // API write
                counter = counter + i;                             // field write
            }
        };
        Thread t1 = new Thread(r, "w1");
        Thread t2 = new Thread(r, "w2");
        t1.start();
        t2.start();
        t1.join();
        t2.join();
    }

    // --- False-positive checks below (Tier 3 of next_steps.md). ---
    // The paper never tests whether TSVD4J correctly stays SILENT on safe
    // code. Every test below is expected to report NOTHING. If any of them
    // DOES report a pair, that is a genuine finding worth writing up.

    static Collection<Integer> sharedList = new ArrayList<>();

    @Test
    public void twoWritersCollectionAdd() throws Exception {
        // Expect: nothing reported - but for the WRONG reason (issue 4: an
        // off-by-one bug drops Collection.add from TSVD4J's own tracked-API
        // list). This code is NOT actually thread-safe (ArrayList has no
        // synchronization), so silence here does not mean TSVD4J judged it
        // safe - it means TSVD4J cannot see this call at all.
        Runnable r = () -> {
            for (int i = 0; i < 200; i++) {
                sharedList.add(i);
            }
        };
        Thread t1 = new Thread(r, "w1-add");
        Thread t2 = new Thread(r, "w2-add");
        t1.start();
        t2.start();
        t1.join();
        t2.join();
    }

    static int lockedCounter = 0;

    @Test
    public void twoWritersSynchronized() throws Exception {
        // Expect: nothing reported, and for the RIGHT reason - every write
        // is inside a synchronized block on a shared lock, so two threads
        // can never touch lockedCounter at the same time. A pair reported
        // here would be a real false positive.
        Runnable r = () -> {
            for (int i = 0; i < 200; i++) {
                synchronized (lock) {
                    lockedCounter = lockedCounter + i;
                }
            }
        };
        Thread t1 = new Thread(r, "w1-sync");
        Thread t2 = new Thread(r, "w2-sync");
        t1.start();
        t2.start();
        t1.join();
        t2.join();
    }

    static Map<String, Integer> concurrentShared = new ConcurrentHashMap<>();

    @Test
    public void twoWritersConcurrentHashMap() throws Exception {
        // Expect: nothing reported. ConcurrentHashMap is built to be safe
        // for exactly this pattern (many threads calling put() at once). A
        // pair reported here would mean TSVD4J doesn't know which
        // collection classes are already thread-safe.
        Runnable r = () -> {
            for (int i = 0; i < 200; i++) {
                concurrentShared.put(Thread.currentThread().getName(), i);
            }
        };
        Thread t1 = new Thread(r, "w1-chm");
        Thread t2 = new Thread(r, "w2-chm");
        t1.start();
        t2.start();
        t1.join();
        t2.join();
    }

    static int sequentialCounter = 0;

    @Test
    public void sequentialWritersNoOverlap() throws Exception {
        // Expect: nothing reported. t1 fully finishes (join()) before t2
        // even starts, so the two threads never run at the same time - this
        // cannot be a race no matter what data they touch. A pair reported
        // here would mean TSVD4J's "close together in time" check is too
        // loose.
        Runnable r = () -> {
            for (int i = 0; i < 200; i++) {
                sequentialCounter = sequentialCounter + i;
            }
        };
        Thread t1 = new Thread(r, "w1-seq");
        t1.start();
        t1.join();   // t1 fully finishes before t2 is even created

        Thread t2 = new Thread(r, "w2-seq");
        t2.start();
        t2.join();
    }
}