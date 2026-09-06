# All 6 flagged pairs — the actual code, one by one

This pulls the real source code for every single one of the 6 things
TSVD4J flagged in `commons-dbcp`, and walks through each one: what the code
is supposed to do, what TSVD4J thought was happening, and the verdict.

This finishes the job an earlier plain-English summary started — that
explained 3 of the 6 pairs; this one shows the literal code for all 6,
including the 3 that were still unresolved there.

**Quick result up front: all 6 turned out to involve a `ConcurrentHashMap`.
None of them are real bugs.** Details below for each one.

---

## Pair 1 — `validatingSet.contains()` vs. `validatingSet.remove()`

**The report:**
```
KeyedCPDSConnectionFactory|contains|94:AbstractConnectionFactory|remove|141
```

**What container is involved** — declared in `AbstractConnectionFactory.java`:

```java
// AbstractConnectionFactory.java:53
protected final Set<PooledConnection> validatingSet =
    Collections.newSetFromMap(new ConcurrentHashMap<>());
```

This builds a `Set` directly on top of a `ConcurrentHashMap` — Java's own
"safe for many threads" wrapper trick. It is exactly as safe as a
`ConcurrentHashMap` itself.

**Side A of the pair** — `KeyedCPDSConnectionFactory.java`, line 94:

```java
@Override
public void connectionClosed(final ConnectionEvent event) {
    final PooledConnection pc = (PooledConnection) event.getSource();
    // if this event occurred because we were validating, or if this
    // connection has been marked for removal, ignore it
    // otherwise return the connection to the pool.
    if (!validatingSet.contains(pc)) {
        final PooledConnectionAndInfo pci = pcMap.get(pc);
        if (pci == null) {
            throw new IllegalStateException(NO_KEY_MESSAGE);
        }
        pool.returnObject(pci.getUserPassKey(), pci);
        // ... (continues)
```

**What this is supposed to do:** whenever a database connection gets
closed, check "is someone currently validating this connection?" If not,
hand it back to the shared pool so it can be reused.

**Side B of the pair** — `AbstractConnectionFactory.java`, line 141:

```java
protected void validateConnection(final PooledConnection pooledConnection) throws SQLException {
    validatingSet.add(pooledConn);   // (line 108, adds to the set before validating)
    // ... does the actual validation work ...
    validatingSet.remove(pooledConn);   // line 141, removes it once done
}
```

**What this is supposed to do:** while a connection is being checked
("validated"), mark it as busy by putting it in `validatingSet`. Once
finished, take it back out.

**What TSVD4J thought was happening:** one thread checking "is this
connection in the set?" while another thread was simultaneously removing a
connection from that same set — flagged as a conflict.

**What actually happens, and why it's fine:** `Set.contains()` and
`Set.remove()` on a `ConcurrentHashMap`-backed set are each individually
guaranteed safe by Java itself — no possibility of corrupted data,
crashes, or incorrect internal state, no matter how the timing lines up.
The only remaining question is whether the *surrounding logic* needs the
two operations to happen as one atomic step — and here, it doesn't: if the
`remove()` finishes a moment before or after the `contains()` check, the
closing-connection code still does the sensible thing either way (either it
sees the connection is still being validated and leaves it alone, or it
sees validation just finished and correctly returns it to the pool).
Nothing breaks in either ordering.

**Verdict: false positive.**

---

## Pair 2 — `pcMap.get()` vs. `pcMap.put()`

**The report:**
```
KeyedCPDSConnectionFactory|get|95:KeyedCPDSConnectionFactory|put|204
```

**What container is involved** — declared in `AbstractConnectionFactory.java`:

```java
// AbstractConnectionFactory.java:48
protected final Map<PooledConnection, PooledConnectionAndInfo> pcMap =
    new ConcurrentHashMap<>();
```

A plain `ConcurrentHashMap`, inherited by `KeyedCPDSConnectionFactory`.

**Side A** — reading from it, line 95 (same method shown above):

```java
final PooledConnectionAndInfo pci = pcMap.get(pc);
```

**Side B** — writing to it, line 204:

```java
@Override
public PooledObject<PooledConnectionAndInfo> makeObject(final UserPassKey userPassKey) throws Exception {
    // ... creates a brand new pooled connection ...
    pcMap.put(pooledConnection, pci);
    return new DefaultPooledObject<>(pci);
}
```

**What this is supposed to do:** `pcMap` is the pool's lookup table —
"given this raw connection, what tracking info do we have for it?" One
method reads from it when a connection closes; a different method writes
to it when a brand-new connection is created.

**What TSVD4J thought was happening:** a read and a write on the same map,
close together in time — flagged as a conflict.

**What actually happens:** this is the textbook use case `ConcurrentHashMap`
exists for — many threads reading and writing different keys at once, with
no external locking needed. A `.get()` for one connection and a `.put()`
for an unrelated new connection have no way to interfere with each other.

**Verdict: false positive.**

---

## Pair 3 — `pcMap.remove()` racing with itself

**The report:**
```
KeyedCPDSConnectionFactory|remove|144:KeyedCPDSConnectionFactory|remove|144
```

This is the same line, on both sides — meaning two *different threads*
both happened to be running this exact line at the same time.

**The code, line 144:**

```java
@Override
public void destroyObject(final UserPassKey ignored, final PooledObject<PooledConnectionAndInfo> pooledObject) throws SQLException {
    final PooledConnection pooledConnection = pooledObject.getObject().getPooledConnection();
    pooledConnection.removeConnectionEventListener(this);
    pcMap.remove(pooledConnection);
    pooledConnection.close();
}
```

**What this is supposed to do:** when a connection is being permanently
destroyed (not just returned to the pool), stop tracking it — remove it
from `pcMap`.

**What TSVD4J thought was happening:** two threads both calling `.remove()`
on the same shared map at the same moment — flagged as a conflict.

**What actually happens:** `ConcurrentHashMap.remove()` is safe to call
from any number of threads, at the same time, on the same or different
keys. If both threads happen to be removing the *same* key, one
of them simply does nothing (the entry's already gone) — no error, no
corruption. This is exactly the scenario the class is built to handle.

**Verdict: false positive.**

---

## Pair 4 — `allObjects.get()` vs. `allObjects.put()` (a different library this time)

**The report:**
```
GenericKeyedObjectPool|get|1594:GenericKeyedObjectPool|put|909
```

This one isn't in `commons-dbcp` at all — `GenericKeyedObjectPool` belongs
to `commons-pool2`, a separate Apache library that `commons-dbcp` uses
internally to actually manage its pool of objects. Had to clone that
project's exact matching version (`2.13.0`) to check this properly.

**What container is involved** — declared inside a nested class,
`ObjectDeque`, in `GenericKeyedObjectPool.java`:

```java
// GenericKeyedObjectPool.java:115
private final Map<IdentityWrapper<S>, PooledObject<S>> allObjects =
        new ConcurrentHashMap<>();
```

Same story as before — a plain `ConcurrentHashMap`.

**Side A** — line 909, inside the method that creates a new pooled object:

```java
createdCount.incrementAndGet();
objectDeque.getAllObjects().put(IdentityWrapper.unwrap(p), p);
return p;
```

**Side B** — line 1594, inside the method that handles an object being
returned to the pool:

```java
final PooledObject<T> p = objectDeque.getAllObjects().get(new IdentityWrapper<>(obj));

if (PooledObject.isNull(p)) {
    throw new IllegalStateException("Returned object not currently part of this pool");
}
```

**What this is supposed to do:** `allObjects` is the master list of every
object the pool currently knows about. One method adds a brand-new object
to that list when it's created; a different method looks an object up in
that list when it's being returned.

**What TSVD4J thought was happening:** a write (`put`) and a read (`get`)
on the same map at the same time — flagged as a conflict.

**What actually happens:** again, this is exactly what `ConcurrentHashMap`
is designed for. **One thing worth noting, though** (the "check, then act"
nuance from the verification guide): the `get()` here is immediately
followed by a check that *throws an exception* if the object isn't found.
Could a race cause that exception to fire incorrectly? Looking at it
closely: that exception path exists specifically to catch a genuine
misuse case (returning an object that was never part of the pool, or
returning it twice) — it's a deliberate safeguard, not a sign of data
corruption. A brand-new object being `put()` in doesn't remove or
invalidate anything already in the map, so it cannot be the cause of that
exception firing for an unrelated object.

**Verdict: false positive.**

---

## Pair 5 — `allObjects.get()` vs. `allObjects.remove()`

**The report:**
```
GenericKeyedObjectPool|get|1594:GenericKeyedObjectPool|remove|982
```

Same `get()` at line 1594 as Pair 4, this time paired against a `.remove()`
elsewhere in the same file:

```java
// line 982, inside the method that permanently destroys an object
if (isIdle || always) {
    objectDeque.getAllObjects().remove(IdentityWrapper.unwrap(toDestroy));
    toDestroy.invalidate();
    // ...
}
```

**What this is supposed to do:** when an object is being permanently
destroyed, take it out of the master `allObjects` list.

**What TSVD4J thought was happening:** a read and a removal on the same
map, close together — flagged as a conflict.

**What actually happens:** same reasoning as Pair 4 — individually safe
`ConcurrentHashMap` operations. The one edge case worth naming: if a
thread is trying to *return* an object (line 1594's `get()`) at the exact
moment another thread is *destroying* that same object (line 982's
`remove()`), the returning thread would correctly hit the
`IllegalStateException` safeguard shown in Pair 4 — which is the pool
correctly detecting "this object isn't valid anymore," not a bug.

**Verdict: false positive** (with the same defensive-exception nuance as
Pair 4).

---

## Pair 6 — `allObjects.remove()` racing with itself

**The report:**
```
GenericKeyedObjectPool|remove|982:GenericKeyedObjectPool|remove|982
```

Same line as Pair 5's `remove()`, two different threads both running it at
once — identical shape to Pair 3, just in the other library.

**What actually happens:** identical reasoning to Pair 3 — safe to call
concurrently, including on the same key, no corruption either way.

**Verdict: false positive.**

---

## Summary table

| # | Pair | Container | Type of race TSVD4J saw | Verdict |
| --- | --- | --- | --- | --- |
| 1 | `contains|94` × `remove|141` | `validatingSet` | check vs. write | False positive |
| 2 | `get|95` × `put|204` | `pcMap` | read vs. write | False positive |
| 3 | `remove|144` × itself | `pcMap` | write vs. write (same key) | False positive |
| 4 | `get|1594` × `put|909` | `allObjects` (commons-pool2) | read vs. write | False positive |
| 5 | `get|1594` × `remove|982` | `allObjects` (commons-pool2) | read vs. write | False positive |
| 6 | `remove|982` × itself | `allObjects` (commons-pool2) | write vs. write (same key) | False positive |

**All 6.** Every single thing TSVD4J reported as a "bug" in this run was a
safe operation on a `ConcurrentHashMap` — in two different libraries, three
different container fields, and every basic operation type
(`get`/`put`/`remove`/`contains`). Not one of the 6 was a real
thread-safety bug.
