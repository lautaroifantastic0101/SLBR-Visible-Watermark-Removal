import argparse
import os
from urllib.parse import urlparse

import requests
from cloudflare import Cloudflare


def normalize_github_repo(link):
    """从 GitHub 链接中提取 owner/repo，失败返回 None。"""
    if not link:
        return None
    try:
        parsed = urlparse(link.strip())
        host = (parsed.netloc or "").lower()
        if host not in {"github.com", "www.github.com"}:
            return None

        parts = [p for p in parsed.path.split("/") if p]
        if len(parts) < 2:
            return None

        owner = parts[0]
        repo = parts[1].replace(".git", "")
        if not owner or not repo:
            return None
        return f"{owner}/{repo}"
    except Exception:
        return None


def select_rows(client, account_id, database_id, beginid=None, limit=None):
    sql = """
    SELECT id, link
    FROM myainote_open_source_tool_tb
    WHERE lower(link) LIKE '%github.com/%'
    """

    params = []
    if beginid is not None:
        sql += " AND id >= ?"
        params.append(str(beginid))

    sql += " ORDER BY id ASC"

    if limit is not None:
        sql += " LIMIT ?"
        params.append(str(limit))

    resp = client.d1.database.query(
        account_id=account_id,
        database_id=database_id,
        sql=sql,
        params=params if params else None,
    )

    if not resp.result:
        return []
    first = resp.result[0]
    return first.results if hasattr(first, "results") and first.results else []


def fetch_repo_stats(session, repo_full_name, github_token=None):
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"

    repo_url = f"https://api.github.com/repos/{repo_full_name}"
    repo_resp = session.get(repo_url, headers=headers, timeout=20)
    repo_resp.raise_for_status()
    repo_data = repo_resp.json()

    stars = str(repo_data.get("stargazers_count", "0"))
    forks = str(repo_data.get("forks_count", "0"))

    commits_url = f"https://api.github.com/repos/{repo_full_name}/commits"
    commits_resp = session.get(commits_url, headers=headers, params={"per_page": 1}, timeout=20)
    commits_resp.raise_for_status()
    commits_data = commits_resp.json()

    last_commit = ""
    if isinstance(commits_data, list) and commits_data:
        commit_obj = commits_data[0] or {}
        commit_info = commit_obj.get("commit") or {}
        committer = commit_info.get("committer") or {}
        last_commit = str(committer.get("date", ""))

    return stars, forks, last_commit


def update_row(client, account_id, database_id, row_id, stars, forks, last_commit):
    sql = """
    UPDATE myainote_open_source_tool_tb
    SET stars = ?, forks = ?, last_commit = ?, updated_at = CURRENT_TIMESTAMP
    WHERE id = ?
    """

    resp = client.d1.database.query(
        account_id=account_id,
        database_id=database_id,
        sql=sql,
        params=[stars, forks, last_commit, str(row_id)],
    )

    if not resp.result or not resp.result[0].success:
        raise RuntimeError(f"更新失败，id={row_id}")



def main():
    parser = argparse.ArgumentParser(description="将爬虫文件塞入到数据库中")
    parser.add_argument("--cf_d1_api_token", required=False, help="Cloudflare D1 API Token，可通过环境变量 CF_D1_API_TOKEN 传递")
    parser.add_argument("--cf_ai_api_token", required=False, help="Cloudflare AI API Token，可通过环境变量 CF_D1_API_TOKEN 传递")
    parser.add_argument("--cf_d1_account_id", required=False, help="Cloudflare D1 ACCOUNT_ID，可通过环境变量 CF_D1_ACCOUNT_ID 传递")
    parser.add_argument("--cf_d1_database_id", required=False, help="Cloudflare D1 DATABASE_ID，可通过环境变量 CF_D1_DATABASE_ID 传递")
    parser.add_argument("--github_api_token", required=False, help="GitHub API Token，可通过环境变量 GITHUB_API_TOKEN 或 GITHUB_TOKEN 传递")
    
    parser.add_argument("--beginid", type=int, help="处理起始 id（含）")
    parser.add_argument("--limit", type=int, help="处理的数量")
    
    
    args = parser.parse_args()

    # 获取参数
    api_token = args.cf_d1_api_token or os.getenv('CF_D1_API_TOKEN')
    account_id = args.cf_d1_account_id or os.getenv('CF_D1_ACCOUNT_ID')
    database_id = args.cf_d1_database_id or os.getenv('CF_D1_DATABASE_ID')
    github_token = args.github_api_token or os.getenv('GITHUB_API_TOKEN') or os.getenv('GITHUB_TOKEN')
    
    beginid = args.beginid
    limit = args.limit

    if not all([api_token, account_id, database_id]):
        print("缺少 D1 配置，请提供 --cf_d1_* 或环境变量 CF_D1_API_TOKEN / CF_D1_ACCOUNT_ID / CF_D1_DATABASE_ID")
        return

    client = Cloudflare(api_token=api_token)
    session = requests.Session()

    rows = select_rows(client, account_id, database_id, beginid=beginid, limit=limit)
    print(f"待处理记录数: {len(rows)}")

    success = 0
    failed = 0
    skipped = 0

    for row in rows:
        row_id = row.get("id")
        link = (row.get("link") or "").strip()
        repo_full_name = normalize_github_repo(link)
        if not repo_full_name:
            skipped += 1
            print(f"[SKIP] id={row_id}, 非标准 GitHub 仓库链接: {link}")
            continue

        try:
            stars, forks, last_commit = fetch_repo_stats(session, repo_full_name, github_token=github_token)
            update_row(client, account_id, database_id, row_id, stars, forks, last_commit)
            success += 1
            print(f"[OK] id={row_id}, repo={repo_full_name}, stars={stars}, forks={forks}, last_commit={last_commit}")
        except Exception as e:
            failed += 1
            print(f"[FAIL] id={row_id}, repo={repo_full_name}, error={e}")

    print(f"完成: success={success}, failed={failed}, skipped={skipped}, total={len(rows)}")


if __name__ == '__main__':
    main()






