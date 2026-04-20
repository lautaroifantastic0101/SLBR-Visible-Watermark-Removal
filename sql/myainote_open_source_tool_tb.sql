CREATE TABLE myainote_open_source_tool_tb (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    page TEXT NOT NULL,
    title TEXT NOT NULL,
    icon TEXT NOT NULL,
    description TEXT NOT NULL,
    link TEXT NOT NULL,
    stars TEXT NOT NULL,
    forks TEXT NOT NULL,
    type TEXT NOT NULL,
    last_commit TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(page, title, link)
)