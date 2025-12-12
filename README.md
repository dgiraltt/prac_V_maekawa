# Maekawa Mutex Algorithm

This repository contains a small Python skeleton that demonstrates Maekawa's distributed mutual-exclusion algorithm 
using Lamport timestamps. The implementation runs multiple logical nodes inside a single Python process; 
each node exposes a TCP server and connects to the other nodes via TCP clients on the loopback interface.

## Project layout
- `src/main.py` — entrypoint that creates a `MaekawaMutex` and runs it.
- `src/maekawaMutex.py` — sets up `Node` objects and orchestrates starting/joining them.
- `src/node.py` — Node class with the Maekawa algorithm behaviors (request, grant, release, inquire, yield, failed). 
Each Node runs as a Thread.
- `src/nodeServer.py` — per-node TCP server thread: accepts connections and dispatches incoming messages to `Node` handlers.
- `src/nodeSend.py` — per-node TCP clients: holds sockets to every other node and sends messages (supports multicast).
- `src/message.py` — `Message` structure and `MessageType` constants; JSON (de)serialization and handling of concatenated JSONs.
- `src/config.py` — small configuration values: `numNodes`, `port`, `exec_time`.
- `src/utils.py` — small helpers to create server/client sockets.

## Functionality
- The process creates `numNodes` Node instances (IDs 0..n-1). Each node opens a server socket on port `config.port + id` 
and keeps client sockets to connect to all other nodes.
- When a node wants to enter the critical section it multicasts a `REQUEST` to its quorum (formed by a grid-based scheme). 
Peers reply with `GRANT`, `FAILED`, or `INQUIRE` according to Maekawa rules.
- Lamport timestamps are used to order requests. Each sender increments its local Lamport clock on sends; 
receivers update clocks on message arrival.

## Execution
From the repository src directory, run the project with the Python interpreter.
```bash
uv run main.py
```

## Configuration
- Edit `src/config.py` to change:
  - `numNodes` — number of logical nodes (default: 4)
  - `port` — base port (node i listens on `port + i`)

## References
- https://www.geeksforgeeks.org/maekawas-algorithm-for-mutual-exclusion-in-distributed-system/
- https://en.wikipedia.org/wiki/Maekawa%27s_algorithm
- https://github.com/yvetterowe/Maekawa-Mutex
- https://github.com/Sletheren/Maekawa-JAVA
- https://www.weizmann.ac.il/sci-tea/benari/software-and-learning-materials/daj-distributed-algorithms-java