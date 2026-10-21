# Fastapi_tutorial
Just a simple tutorial for Fast API introduction

Day-1:
Let's have a small tutorail and see how fast API works

Day-2: 
Persistent Storage with SQL Model and SQL Alchemy

## How a request reaches the database

The application follows this path when an endpoint reads or changes data:

```text
Client (for example, Swagger UI)
	-> FastAPI matches the HTTP method and URL to a route
	-> Depends(get_sessions) provides a SQLModel session
	-> The route runs a query or saves changes through that session
	-> SQLite reads or writes database.db
	-> FastAPI converts the returned value to an HTTP response
```

FastAPI routes are declared with decorators such as `@app.get` and
`@app.post`. The decorator specifies the HTTP method and URL path. For example,
`@app.get("/item/{item_id}")` defines a GET endpoint with a path parameter named
`item_id`; FastAPI parses that part of the URL as an integer because the
function parameter is annotated as `int`.

### Available routes

| Method and path | Purpose |
| --- | --- |
| `GET /` | Returns a welcome message. |
| `POST /items/` | Accepts an item, stores it, creates its chapter rows, and returns the item with HTTP status `201`. |
| `GET /items/` | Reads and returns all stored items. |
| `GET /item/{item_id}` | Looks up one item and prepares a response with the item and chapter query results. Returns `404` if the item does not exist. |

The `response_model` on the create and list routes tells FastAPI which model
shape to use when validating and serializing the response. The `Item` model
also calculates `status` and `percentage` from the chapter counts, so clients
can receive those progress values with an item.

**Detail-route note:** the current chapter query compares `Chapter.item_id` to
the `Item.id` database column instead of the requested `item_id` value. To
return only the chapters belonging to the requested item, the filter should
compare `Chapter.item_id == item_id`.

## Database sessions

The SQLModel `engine` represents the configured connection to the database.
A `Session` is a short-lived unit of work used by a route to query records or
stage changes. It is not the database itself: it uses the engine to communicate
with SQLite and tracks pending changes until they are committed.

`get_sessions()` is a FastAPI dependency. Each route that declares
`session: Session = Depends(get_sessions)` receives a session for that request.
The dependency's `with Session(engine)` context manager closes the session
after the route finishes, including when request handling raises an error.
This keeps database work tied to a request instead of sharing one session
globally across requests.

For example, `POST /items/` adds the new item to the session and calls
`commit()` to persist it. It then calls `refresh()` so SQLAlchemy can populate
database-generated values such as the item's new ID. The route creates one
`Chapter` row per planned chapter, adds those rows, and commits again. Read
routes use `select(...)` to build a query and `session.exec(...)` to run it;
`.all()` collects all matching rows.

## SQLite database

SQLite stores the database in a local file, so this tutorial does not need a
separate database server. The engine URL is built from `sqlite_file_name`,
which is set to `database.db`. Because that is a relative path, SQLite creates
or opens the file relative to the process's current working directory (run the
Uvicorn command from the project root to keep it there).

At application startup, `create_db_and_tables()` calls
`SQLModel.metadata.create_all(engine)`. This creates the declared `Item` and
`Chapter` tables when they are missing; it does not replace an existing
database or provide schema migrations. Committed records remain in the file
after the application stops and are available when it starts again.

The engine is configured with `check_same_thread=False` because FastAPI may
handle work across different threads, while SQLite's default connection check
restricts a connection to the thread that created it. Sessions are still
created per request; this setting does not mean one session is shared across
all requests.



# Creating a Virtual env

```bash
python -m venv .venv   # creating an Enviorment 
```

### Activating env
```bash
source .venv/bin/activate
```
### Deactivating
```bash
deactivate
```

# Installing requirements
```bash
pip install -r requirements.txt
```

# Running code 
```bash
uvicorn fastapi_tutorial.main:app --reload
```