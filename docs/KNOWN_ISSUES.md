# Known Issues

## py-libp2p Connection Issue

### Status: Under Investigation - Swarm Partially Implemented

**See [PY_LIBP2P_STATUS.md](PY_LIBP2P_STATUS.md) for full analysis.**

### Description

Real py-libp2p node-to-node connections are currently not working in the test environment. Attempts to establish connections between two hosts result in:

```
SwarmException: unable to connect to [peer_id], no addresses established a successful connection
```

### Root Cause Analysis

1. **Listener Initialization Problem**: `network.listen()` doesn't actually start listening
   - `listen()` waits for `event_listener_nursery_created` to be set
   - This event is only set by `network.run()`
   - But `run()` fails with `AttributeError: 'Swarm' object has no attribute '_manager'`

2. **Lifecycle Management**: The network lifecycle isn't properly initialized:
   ```python
   # These don't work:
   network.listen(addr)  # Waits forever for internal event
   await network.run()   # Fails - manager not initialized
   new_host(listen_addrs=[addr])  # Doesn't actually start listening
   ```

3. **Missing Initialization**: There appears to be a missing initialization step or configuration that would properly set up the network's internal state.

### Investigation Steps Taken

1. ✅ Verified `listen()` signature and implementation
2. ✅ Checked `network.run()` requirements  
3. ✅ Tested with `listen_addrs` parameter in `new_host()`
4. ✅ Tried manual listener initialization with nurseries
5. ✅ Checked for async initialization patterns
6. ✅ Verified GMP and fastecdsa installation (resolved separately)

### Diagnostic Scripts

See `/tests/` directory:
- `diagnose_connection.py` - Initial diagnosis
- `diagnose_connection_fixed.py` - Attempted fix with sync listen
- `test_connection_working.py` - Attempted fix with wait_for_listener
- `test_connection_final.py` - Attempted fix with network.run()
- `test_connection_simple.py` - Simplified approach with listen_addrs

**Result**: All attempts show `Host listeners: 0` - listeners never start.

### Workaround

**For PoC Demonstration**: Use simulated data instead of real py-libp2p connections.

The `MetadataCollector` can still demonstrate the concepts by:
1. Registering with INotifee interface (works)
2. Accepting simulated connection events
3. Processing privacy analysis on simulated data

**Working Examples**:
- `examples/basic_analysis.py` - Full end-to-end with simulated data ✅
- `libp2p-privacy analyze --host simulated` - CLI with simulated data ✅

### Impact on PoC

**Minimal Impact**: The PoC successfully demonstrates:
- ✅ Privacy analysis algorithms
- ✅ Mock ZK proof system
- ✅ Report generation (console, JSON, HTML)
- ✅ CLI interface
- ✅ MetadataCollector INotifee integration
- ✅ Full API design

**Not Demonstrated**: 
- ❌ Real node-to-node connections
- ❌ Live event capture from actual libp2p traffic

### Technical Details

**Python Version**: 3.13  
**py-libp2p Version**: 0.3.0  
**OS**: macOS (darwin 25.0.0)  
**Architecture**: x86_64 (Intel)

**Dependencies**:
- ✅ GMP library installed (via Homebrew)
- ✅ fastecdsa working
- ✅ All Python packages installed
- ✅ No import errors

**Network Configuration**:
- Using localhost (127.0.0.1)
- Explicit TCP ports (10000+)
- No firewall issues (local connections)

---