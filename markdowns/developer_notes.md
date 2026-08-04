# Developer Notes & Contribution Guidelines

## 1. Code Style & Linting (Stylecheck)
We enforce strict code quality standards to maintain readability and maintainability across the Python stack.
- **Formatter:** Use `black` with a standard line length (e.g., 88 characters) to ensure uniform code formatting.
- **Import Sorting:** Use `isort` to automatically organize and group imports.
- **Linter:** Use `ruff` or `flake8` to catch syntax and stylistic errors.
- **Type Checking:** Python code must include static type hints and pass `mypy` strict checks.
- **Pre-commit Hooks:** Ensure all hooks (black, isort, ruff, mypy) are configured to run automatically before committing.

## 2. Commit Message Guidelines
We strictly follow the [Conventional Commits](https://www.conventionalcommits.org/) specification. This enables automated changelog generation, semantic versioning, and a clean project history.

**Format:**
`<type>[optional scope]: <description>`

**Allowed Types:**
- `feat`: A new feature (e.g., `feat(api): add QR code endpoint`).
- `fix`: A bug fix (e.g., `fix(worker): resolve GeoIP lookup timeout`).
- `docs`: Documentation only changes.
- `style`: Changes that do not affect the meaning of the code (white-space, formatting, etc.).
- `refactor`: A code change that neither fixes a bug nor adds a feature.
- `perf`: A code change that improves performance.
- `test`: Adding missing tests or correcting existing tests.
- `chore`: Changes to the build process or auxiliary tools/libraries.

## 3. Programming Paradigm & Style
Our codebase embraces a hybrid approach: **Object-Oriented Component Design** combined with **Functional Style Methods**.

### Object-Oriented Component Design
- **Architectural Boundaries:** Use classes to define major system components, services, and interfaces (e.g., `AnalyticsService`, `URLRepository`).
- **Dependency Injection (DI):** Pass dependencies (like database connections or Redis clients) into component constructors rather than hardcoding them or relying on global state. This makes components highly modular and testable.

### Functional Style Methods (Inside Classes)
- **Pure Functions:** Keep internal methods pure where possible. Given the same inputs, they should return the same outputs without side effects.
- **Immutability:** Avoid mutating instance state or input parameters unexpectedly. Prefer returning new data structures (e.g., using Pydantic models).
- **Declarative Logic:** Utilize functional constructs like `map`, `filter`, and comprehensions over traditional `for` and `while` loops where it enhances readability.

### SOLID Principles
All application logic must adhere to SOLID principles to ensure a decoupled and scalable architecture:
- **S - Single Responsibility Principle:** A class or module should have one, and only one, reason to change.
- **O - Open/Closed Principle:** Software entities should be open for extension but closed for modification.
- **L - Liskov Substitution Principle:** Derived classes must be substitutable for their base classes without altering the correctness of the program.
- **I - Interface Segregation Principle:** Client-specific interfaces are better than one general-purpose interface.
- **D - Dependency Inversion Principle:** Depend upon abstractions (interfaces/protocols), not concretions.

## 4. Local Development Environment
To ensure environment consistency and true cloud-native readiness without requiring a root-level Docker daemon, we use **Podman** for local development.

### Prerequisites
- Install `podman` and `podman-compose`.

### Running the Application Locally
1. **Build the application images:**
   ```bash
   podman-compose build
   ```
2. **Start the localized cluster (Database, Redis, API, Workers):**
   ```bash
   podman-compose up -d
   ```
3. **Tail the logs for a specific service (e.g., the API):**
   ```bash
   podman-compose logs -f api
   ```
4. **Stop and tear down the environment:**
   ```bash
   podman-compose down
   ```
