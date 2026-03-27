CREATE TABLE youtube_video_crawl_item_tb (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT NOT NULL,
    crawl_pt TEXT NOT NULL,          -- 抓取批次或平台标识
    title TEXT,
    link TEXT,
    channel TEXT,
    channel_url TEXT,
    views_raw TEXT,                  -- 原始播放量字符串（如 "1.2M views"）
    views_value INTEGER,             -- 转换后的数字播放量
    publish_date_raw TEXT,           -- 原始发布时间字符串
    publish_date_clean DATETIME,     -- 格式化后的日期
    rank_index INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP, "platform" TEXT, "digg_count" INTEGER, "play_url" TEXT, "all_video_urls" TEXT, "video_duration" INTEGER, "video_ratio" TEXT,
    
    -- 约束：keyword + crawl_pt 组合唯一
    UNIQUE(keyword, crawl_pt, link, rank_index)
)