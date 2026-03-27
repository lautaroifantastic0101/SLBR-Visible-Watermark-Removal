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
        print(query)

        # 执行查询
        resp = client.d1.database.query(
            database_id=database_id,
            account_id=account_id,
            sql=query
        )

        # # 检查响应
        # if resp is None or not resp.get('success', True):
        #     print("查询失败:", resp.get('errors', resp))
        #     return []


        if not resp.result or not resp.result[0].results:
            return []
        return resp.result[0].results
    # return [{"id": row["id"], "content": row["content"] or "", "title": row["title"] or "", "case_number": row["case_number"] or "", "gemini_ai_resp": row["gemini_ai_resp"] or "", "origin_article_id":row["origin_article_id"] or ""} for row in resp.result[0].results]

    except Exception as e:
        print(f"查询出错: {e}")
        return []



def update_video_path(client, database_id, account_id, id, store_path):
    """根据 id 更新 youtube_video_crawl_item_tb 的 store_path 字段。

    :param client: Cloudflare 客户端实例
    :param database_id: 数据库 ID
    :param account_id: 账户 ID
    :param id: 记录 id
    :param store_path: 存储路径
    :return: bool 成功返回 True，失败返回 False
    """
    try:
        escaped_id = str(id).replace("'", "``")
        escaped_path = str(store_path).replace("'", "``")

        sql = f"""
        UPDATE youtube_video_crawl_item_tb
        SET video_store_path = '{escaped_path}', updated_at = CURRENT_TIMESTAMP
        WHERE id = '{escaped_id}'
        """

        resp = client.d1.database.query(
            database_id=database_id,
            account_id=account_id,
            sql=sql
        )

        if resp is None:
            print('update_video_path: empty response')
            return False

        if isinstance(resp, dict):
            if resp.get('success') is False:
                print('update_video_path failed:', resp.get('errors') or resp.get('message'))
                return False
            return True

        if hasattr(resp, 'status_code'):
            if resp.status_code in (200, 201):
                return True
            print(f"update_video_path failed status {resp.status_code}: {getattr(resp, 'text', '')}")
            return False

        # 无法判断时返回 True
        return True
    except Exception as e:
        print(f"update_video_path exception: {e}")
        return False


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
