
import argparse
import json
import os
import re





if __name__ == '__main__':
        parser = argparse.ArgumentParser(description='Generate a Next.js page.tsx from a markdown file.')
        parser.add_argument('markdown_fp', nargs='?', default='D:\\toolnotes_pro\\docs\\robloxstudio\\1_robloxstudio_introduction_and_download\\composed_notes.md')
        parser.add_argument('--output', dest='output_fp', default=None, help='Optional output path for page.tsx')
        args = parser.parse_args()
        main(args.markdown_fp, args.output_fp, note_title='Roblox Studio简介与下载')
