CREATE TABLE
    tro_crawl_item_tb (
        -- id: 自增长主键
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        -- origin_article_id: 原始文章ID（建议增加 UNIQUE 以防重复爬取同一篇）
        origin_article_id TEXT UNIQUE NOT NULL,
        -- crawl_item: 爬取的原始内容或项目（JSON或纯文本）
        crawl_item TEXT,
        -- gemini_ai_resp: Gemini AI 处理后的响应结果
        gemini_ai_resp TEXT,
        -- 额外建议字段：记录创建时间，方便排序和清理数据
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        source_type TEXT DEFAULT 'CifTRONewsItem',
        extract_case_number TEXT,
        extract_court TEXT,
        is_multi_case_number TEXT,
        -- case_number_arr: 从 content 中匹配出的案号列表，存为 JSON 数组字符串
        case_number_arr TEXT
    );

    -- 若表已存在，仅新增字段时执行：
    -- ALTER TABLE tro_crawl_item_tb ADD COLUMN case_number_arr TEXT;




    