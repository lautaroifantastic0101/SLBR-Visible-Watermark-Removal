





def main(file_path):

    

    # parser = argparse.ArgumentParser(description="转化文档")
    # args_cli = parser.parse_args()

    # parser.add_argument("--r2_account_id", required=False, help="Cloudflare R2 ACCOUNT_ID，可以通过环境变量传递")
    # parser.add_argument("--r2_access_key_id", required=False, help="Cloudflare R2 ACCESS_KEY_ID，可以通过环境变量传递")
    # parser.add_argument("--r2_secret_access_key", required=False, help="Cloudflare R2 SECRET_ACCESS_KEY，可以通过环境变量传递")
    # args_cli = parser.parse_args()
    # r2_account_id = args_cli.r2_account_id
    # r2_access_key_id = args_cli.r2_access_key_id
    # r2_secret_access_key = args_cli.r2_secret_access_key



    ###################################################################
    # 【0】 Initialize the S3 client
    ###################################################################
    s3_client = boto3.client(
        "s3",
        endpoint_url=ENDPOINT_URL,
        aws_access_key_id=r2_access_key_id,
        aws_secret_access_key=r2_secret_access_key,
    )
    # s3_client = ''


    composed_notes = []
    with open(file_path, 'r', encoding='utf-8') as f:
        composed_notes = json.load(f)

    for note in composed_notes:
        print(f"Title: {note.get('json_title', 'N/A')}")
        print(f"Content: {note.get('json_content', 'N/A')}")
        print(f"frames: {note.get('frames', 'N/A')}")
        
        print("-" * 40)

    
    # current_dir = Path(__file__).resolve().parent
    last_folder = os.path.basename(os.path.dirname(file_path))
    print(f"Current directory: {last_folder}")
    write_markdown(s3_client, composed_notes, os.path.join(os.path.dirname(file_path), "composed_notes.md"))
        



if __name__ == "__main__":
    main("D:\\toolnotes_pro\\docs\\robloxstudio\\1_robloxstudio_introduction_and_download\\composed_notes.json")
