"""
删除 Sanity 文档的独立脚本。
支持按文档 _id 列表删除，或按 _type 查询后批量删除。
"""
import argparse
import os
from urllib.parse import quote

import requests
from dotenv import load_dotenv

load_dotenv()


def delete_sanity_docs(project_id: str, dataset: str, token: str, document_ids: list, dry_run: bool = False):
    """删除 Sanity 中指定 id 的文档。document_ids 为 _id 列表。"""
    if not document_ids:
        print("未提供要删除的文档 id")
        return 0
    base = f"https://{project_id}.api.sanity.io/v2022-03-07/data/mutate/{dataset}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    mutations = [{"delete": {"id": did}} for did in document_ids]
    payload = {"mutations": mutations}
    if dry_run:
        print(f"  [dry_run] 将删除 {len(document_ids)} 个文档: {document_ids[:10]}{'...' if len(document_ids) > 10 else ''}")
        return len(document_ids)
    try:
        r = requests.post(base, json=payload, headers=headers, timeout=60)
        r.raise_for_status()
        print(f"  已删除 {len(document_ids)} 个文档")
        return len(document_ids)
    except Exception as e:
        print(f"  删除失败: {e}")
        raise


def query_doc_ids(project_id: str, dataset: str, token: str, doc_type: str):
    """按 _type 查询文档 _id 列表。"""
    query = f'*[_type == "{doc_type}"]._id'
    url = f"https://{project_id}.api.sanity.io/v2022-03-07/data/query/{dataset}?query={quote(query)}"
    r = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=30)
    r.raise_for_status()
    return r.json().get("result") or []


def main():
    parser = argparse.ArgumentParser(description="删除 Sanity 文档")
    parser.add_argument("--sanity_project_id", required=False, help="Sanity 项目 ID，可通过环境变量 SANITY_PROJECT_ID 传递")
    parser.add_argument("--sanity_dataset", default="production", help="Sanity 数据集，可通过环境变量 SANITY_DATASET 传递")
    parser.add_argument("--sanity_token", required=False, help="Sanity 写权限 Token，可通过环境变量 SANITY_TOKEN 传递")
    parser.add_argument("--doc_ids", type=str, default="", help="要删除的文档 _id，逗号分隔，如 id1,id2,id3")
    parser.add_argument("--delete_type", type=str, default="", help="按 _type 删除：先查询该类型全部 id 再删除，如 tro_post")
    parser.add_argument("--dry_run", action="store_true", help="仅打印将要删除的 id，不实际请求")
    args = parser.parse_args()

    project_id = args.sanity_project_id or os.getenv("SANITY_PROJECT_ID")
    dataset = args.sanity_dataset or os.getenv("SANITY_DATASET") or "production"
    token = args.sanity_token or os.getenv("SANITY_TOKEN")

    if not project_id or not token:
        print("需要 --sanity_project_id 与 --sanity_token（或环境变量 SANITY_PROJECT_ID / SANITY_TOKEN）")
        return

    doc_ids = [x.strip() for x in args.doc_ids.split(",") if x.strip()]
    if args.delete_type:
        print(f"按 _type 查询: {args.delete_type}")
        try:
            doc_ids = query_doc_ids(project_id, dataset, token, args.delete_type)
            print(f"  查到 {len(doc_ids)} 个文档")
        except Exception as e:
            print(f"查询失败: {e}")
            return

    if not doc_ids:
        print("没有要删除的文档 id（请提供 --doc_ids 或 --delete_type）")
        return

    print(f"删除 Sanity 文档，共 {len(doc_ids)} 个")
    delete_sanity_docs(project_id, dataset, token, doc_ids, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
