# Dependencies fail in modes, not merely “down”

Exercise the behavior the caller must survive: timeout, slow response, connection reset, malformed response, partial success, stale data, duplicate delivery, out-of-order delivery, throttling, unavailable dependency, and recovery after a transient failure.

The oracle includes local state and external side effects. A timeout after a remote commit is not equivalent to a failure before receipt; retrying blindly can duplicate work. Distinguish transport acknowledgement, business completion, persistence, publication, and observability.

Use controlled fakes or existing test facilities. Fault injection against shared or production systems requires explicit authorization and bounded traffic.
