CREATE TABLE youtube_channel_tb (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_name TEXT NOT NULL,
    channel_url TEXT NOT NULL,
    description TEXT NOT NULL,          -- 抓取批次或平台标识
    subscribers INTEGER,
    video_count INTEGER,
    crawl_pt TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(channel_url, crawl_pt)
);
