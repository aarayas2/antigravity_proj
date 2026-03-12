# Architecture & Design Decisions

## Persistence Layer

### Overview
To meet the requirements of scalable and thread-safe data persistence for stock analysis metrics, a new `persistence.py` module was introduced, decoupling file I/O operations from the main `app.py` presentation logic.

### Design Patterns Utilized
1. **Strategy Pattern (`StatsStorageStrategy`)**: The interface for reading and writing data allows multiple storage mechanisms to be swapped interchangeably. Currently, `JsonStatsStorage` is implemented, but this guarantees that a `SqlStatsStorage` could be added in the future without modifying `StatsManager`.
2. **Repository/DAO Pattern (`StatsManager`)**: Acts as a centralized Data Access Object that encapsulates the business rules (checking if a ticker exists, conditionally appending, or overwriting). The UI layer merely calls `save_stats()`, adhering strictly to the Single Responsibility Principle.
3. **Singleton Pattern**: The `StatsManager` enforces a single active instance across the application lifecycle. This is crucial for managing concurrent requests in the web app, allowing us to enforce a write queue using internal threading locks.

### Concurrency and Thread Safety
To prevent JSON file corruption when multiple users access the Dash interface simultaneously:
- **`threading.Lock`**: Placed within the Singleton's read/write operations, guaranteeing that only one web request can modify the application state or write to disk at any given time.

### Future-Proofing
By separating concerns through the `StatsStorageStrategy`, the system is fully prepared for a database migration (e.g., PostgreSQL or MongoDB). The only required change would be implementing a new class conforming to the strategy interface and passing it into the `StatsManager` upon initialization. The Dash UI code (`app.py`) would remain completely untouched, ensuring high maintainability.
