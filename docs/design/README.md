# Design Patterns (DES index)

Repeatable, cross-cutting patterns (used 2+ places). One-time choices live in the
[ADR index](../architecture/README.md).

| ID | Pattern | Status | Applies to | Grounded in |
|----|---------|--------|-----------|-------------|
| [DES-001](DES-001-read-along-timing-windows.md) | Read-along timing windows (pause-fold rule) | Active | TTS producer, item contract, web player, caption export | [exp 001](../../experiments/001-player-ready-item/README.md) |
| [DES-002](DES-002-config-selected-backend.md) | Config-selected backend (startup selection, no test flags) | Active | database engine, audio storage | [exp 001](../../experiments/001-player-ready-item/README.md) |
