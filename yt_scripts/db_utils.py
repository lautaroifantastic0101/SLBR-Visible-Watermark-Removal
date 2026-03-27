from cloudflare import Cloudflare


def query_by_links(client, database_id, account_id, links):
    """
    根据输入的多个 links 查询 D1 数据库表 youtube_video_crawl_item_tb，返回结果。

    :param client: Cloudflare 客户端实例
    :param database_id: 数据库 ID
    :param account_id: 账户 ID
    :param links: 要查询的链接列表
    :return: 查询结果，列表形式
    """
    try:
        # 构造 SQL 查询
        placeholders = ', '.join([f"'{link}'" for link in links])
        query = f"""
        SELECT * FROM youtube_video_crawl_item_tb WHERE link IN ({placeholders})
        """

        # 执行查询
        resp = client.d1.database.query(
            database_id=database_id,
            account_id=account_id,
            sql=query
        )

        # 检查响应
        if resp is None or not resp.get('success', True):
            print("查询失败:", resp.get('errors', resp))
            return []

        return resp.get('result', [])

    except Exception as e:
        print(f"查询出错: {e}")
        return []

# 示例用法
if __name__ == "__main__":
    from cloudflare import Cloudflare

    api_token = "your_api_token"  # 替换为实际 API Token
    account_id = "your_account_id"  # 替换为实际账户 ID
    database_id = "your_database_id"  # 替换为实际数据库 ID

    client = Cloudflare(api_token=api_token)

    links = ["https://example.com/video1", "https://example.com/video2"]  # 替换为实际查询的链接列表
    results = query_by_links(client, database_id, account_id, links)
    print("查询结果:", results)