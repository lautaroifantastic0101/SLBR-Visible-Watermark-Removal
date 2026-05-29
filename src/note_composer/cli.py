import argparse
import json
import os
import re
from utils.parse_imgs_zip_upload import upload_file
import boto3
from utils.deepseek_api_call import (
    call_deepseek_chat,
    parse_deepseek_response,
    translate_english_to_chinese,
)

def normalize_text(text):
    normalized = text.lower().replace("'", "")
    normalized = re.sub(r'[^a-z0-9\s]', ' ', normalized)
    return re.sub(r'\s+', ' ', normalized).strip()


def split_sentences(text):
    return [
        sentence.strip()
        for sentence in re.split(r'(?<=[.!?])\s+', text.strip())
        if sentence.strip()
    ]


def score_text_match(anchor_text, candidate_text):
    anchor_normalized = normalize_text(anchor_text)
    candidate_normalized = normalize_text(candidate_text)

    if not anchor_normalized or not candidate_normalized:
        return 0.0

    if (
        anchor_normalized in candidate_normalized
        or candidate_normalized in anchor_normalized
    ):
        shorter_length = min(len(anchor_normalized), len(candidate_normalized))
        longer_length = max(len(anchor_normalized), len(candidate_normalized))
        return shorter_length / longer_length

    anchor_tokens = set(anchor_normalized.split())
    candidate_tokens = set(candidate_normalized.split())
    overlap_ratio = len(anchor_tokens & candidate_tokens) / max(len(anchor_tokens), 1)
    length_ratio = min(len(anchor_normalized), len(candidate_normalized)) / max(
        len(anchor_normalized), len(candidate_normalized)
    )
    return overlap_ratio * 0.8 + length_ratio * 0.2


def find_best_matching_window(anchor_text, segments, search_start_index, search_end_index=None):
    best_match = None
    best_score = 0.0
    if search_end_index is None:
        search_end_index = len(segments) - 1

    for start_index in range(search_start_index, search_end_index + 1):
        window_text = ''
        for end_index in range(start_index, min(start_index + 4, search_end_index + 1)):
            window_text = f"{window_text} {segments[end_index].get('text', '')}".strip()
            score = score_text_match(anchor_text, window_text)
            if score > best_score:
                best_score = score
                best_match = (start_index, end_index)

    if best_score < 0.5:
        return None, best_score
    return best_match, best_score


def find_chapter_start(chapter_sentences, segments, search_start_index):
    anchors = []
    if chapter_sentences:
        anchors.append(chapter_sentences[0])
    if len(chapter_sentences) > 1:
        anchors.append(' '.join(chapter_sentences[:2]))

    best_match = None
    best_score = 0.0
    for anchor in anchors:
        match, score = find_best_matching_window(anchor, segments, search_start_index)
        if score > best_score:
            best_match = match
            best_score = score

    return best_match


def extract_frame_time(response_text):
    if not response_text:
        return None

    patterns = [
        r'captured at\s+(?P<time>\d+(?:\.\d+)?)\s+seconds',
        r'Frame\s+\d+\s*\n\s*(?P<time>\d+(?:\.\d+)?)\s+seconds',
        r'currently at\s+(?P<time>\d+(?:\.\d+)?)\s+seconds',
    ]
    for pattern in patterns:
        match = re.search(pattern, response_text, re.IGNORECASE)
        if match is not None:
            return float(match.group('time'))

    return None


def estimate_frame_time(frame_index, frames_per_minute, transcript_segments):
    if frames_per_minute:
        return round(frame_index * 60 / frames_per_minute + 0.5, 2)

    if transcript_segments:
        transcript_end = transcript_segments[-1].get('end')
        if transcript_end is not None:
            return round(transcript_end, 2)

    return None

def load_chaps_txt(chap_txt_fp):
    if not os.path.exists(chap_txt_fp):
        print(f"File not found: {chap_txt_fp}")
        return []
    with open(chap_txt_fp, 'r', encoding='utf-8') as file:
        content = file.read()

    chapter_pattern = re.compile(
        r'\*\*(?P<title>.*?)\*\*\s*(?P<content>.*?)(?=\n\n\*\*|\Z)',
        re.DOTALL,
    )
    chapters = [
        {
            'json_title': match.group('title').strip(),
            'json_content': match.group('content').strip(),
        }
        for match in chapter_pattern.finditer(content)
    ]

    print("Chapters loaded successfully.")
    return chapters


def load_video_analyzer_output_json(json_fp):
    if not os.path.exists(json_fp):
        print(f"File not found: {json_fp}")
        return {}
    with open(json_fp, 'r', encoding='utf-8') as file:
        try:
            content = json.load(file)
        except json.JSONDecodeError as exc:
            print(f"Invalid JSON in file {json_fp}: {exc}")
            return {}

    frame_analyses = content.get('frame_analyses', [])
    frames_per_minute = content.get('metadata', {}).get('frames_per_minute')
    transcript_segments = content.get('transcript', {}).get('segments', [])

    for frame_index, frame in enumerate(frame_analyses):
        frame_time = extract_frame_time(frame.get('response', ''))
        if frame_time is None:
            frame_time = estimate_frame_time(
                frame_index,
                frames_per_minute,
                transcript_segments,
            )

        frame['time'] = frame_time
        frame['frame_index'] = frame_index

    print("Video analyzer output loaded successfully.")
    return content


def complete_note_composition(chapters, video_analyzer_output):
    segments = video_analyzer_output.get('transcript', {}).get('segments', [])
    if not segments:
        return chapters

    chapter_matches = []
    search_start_index = 0

    for chapter in chapters:
        chapter_sentences = split_sentences(chapter.get('json_content', ''))
        if not chapter_sentences:
            chapter_matches.append((chapter, None, None))
            continue

        start_match = find_chapter_start(chapter_sentences, segments, search_start_index)
        if start_match is None:
            chapter_matches.append((chapter, None, None))
            continue

        chapter_matches.append((chapter, chapter_sentences, start_match))
        search_start_index = start_match[0] + 1

    composed_notes = []
    for index, (chapter, chapter_sentences, start_match) in enumerate(chapter_matches):
        if start_match is None:
            composed_notes.append({**chapter, 'start': None, 'end': None})
            continue

        next_start_match = None
        for next_index in range(index + 1, len(chapter_matches)):
            if chapter_matches[next_index][2] is not None:
                next_start_match = chapter_matches[next_index][2]
                break

        end_search_index = (
            next_start_match[0] - 1 if next_start_match is not None else len(segments) - 1
        )
        end_match = start_match

        if chapter_sentences:
            candidate_end_match, _ = find_best_matching_window(
                chapter_sentences[-1],
                segments,
                start_match[0],
                end_search_index,
            )
            if candidate_end_match is not None and candidate_end_match[1] >= start_match[0]:
                end_match = candidate_end_match
            else:
                end_match = (start_match[0], end_search_index)
        
        # 视频分析结果，增加这个chapters 的 frame array
        frame_array = [
            frame['frame_index'] for frame in video_analyzer_output.get('frame_analyses', [])
            if start_match[0] <= frame['frame_index'] <= end_match[1]
        ]

        composed_notes.append(
            {
                **chapter,
                'start': segments[start_match[0]].get('start'),
                'end': segments[end_match[1]].get('end'),
                'frames': frame_array,
            }
        )

    return composed_notes



def open_frame_picture(s3_client, frame_index, pic_frame_outputpath):
    frame_picture_path = os.path.join(pic_frame_outputpath, 'output', 'frames', f"frame_{frame_index}.jpg")
    last_dir_name = os.path.basename(pic_frame_outputpath)
    # outputdir = os.path.dirname(frame_picture_path)
    if os.path.exists(frame_picture_path):
        print(f"Opening frame picture: {frame_picture_path}")
        # os.startfile(frame_picture_path)
        r2_key = f"notetool/{last_dir_name}/frames/frame_{frame_index}.jpg"
        upload_file(s3_client, "my-blog-app", frame_picture_path, r2_key)
        return r2_key
    else:
        print(f"Frame picture not found: {frame_picture_path}")
        return None


    # D:\toolnotes_pro\docs\robloxstudio\1_robloxstudio_introduction_and_download\output\frames\frame_0.jpg
    


def write_markdown(s3_client, composed_notes, output_file, deepseek_api_key=None):
    # pic_frame_outputpath = os.path.join(os.path.dirname(output_file), "frames")

    with open(output_file, 'w', encoding='utf-8') as f:
        for note in composed_notes:
            title = note.get('json_title', 'N/A')
            content = note.get('json_content', 'N/A')
            frames = note.get('frames', [])
            if deepseek_api_key is None:
                translated_content = content
                translated_title = title
            else:
                translated_content = translate_english_to_chinese(content, api_key=deepseek_api_key)
                translated_title = translate_english_to_chinese(title, api_key=deepseek_api_key)
            
            if frames and len(frames) > 0:
                r2_key = open_frame_picture(s3_client, frames[0], os.path.dirname(output_file))
                if r2_key:
                    translated_content += f"\n\n![Frame Image]({r2_key})\n\n"

            f.write(f"# {translated_title}\n\n")
            f.write(f"{translated_content}\n\n")
            f.write("\n---\n\n")



def parse_markdown_sections(markdown_text):
        raw_sections = [section.strip() for section in re.split(r'\n\s*---\s*\n', markdown_text) if section.strip()]
        sections = []

        for raw_section in raw_sections:
                lines = raw_section.splitlines()
                title = 'Untitled'
                blocks = []
                paragraph_lines = []

                def flush_paragraph():
                        if paragraph_lines:
                                paragraph_text = ' '.join(line.strip() for line in paragraph_lines if line.strip())
                                if paragraph_text:
                                        blocks.append({'type': 'paragraph', 'text': paragraph_text})
                                paragraph_lines.clear()

                for line in lines:
                        stripped_line = line.strip()
                        if not stripped_line:
                                flush_paragraph()
                                continue

                        if stripped_line.startswith('# '):
                                flush_paragraph()
                                title = stripped_line[2:].strip() or title
                                continue

                        image_match = re.match(r'!\[(?P<alt>[^\]]*)\]\((?P<src>[^)]+)\)', stripped_line)
                        if image_match:
                                flush_paragraph()
                                blocks.append(
                                        {
                                                'type': 'image',
                                                'alt': image_match.group('alt').strip() or title,
                                                'src': image_match.group('src').strip(),
                                        }
                                )
                                continue

                        heading_match = re.match(r'(?P<level>#{2,6})\s+(?P<text>.+)', stripped_line)
                        if heading_match:
                                flush_paragraph()
                                blocks.append(
                                        {
                                                'type': 'heading',
                                                'level': len(heading_match.group('level')),
                                                'text': heading_match.group('text').strip(),
                                        }
                                )
                                continue

                        paragraph_lines.append(stripped_line)

                flush_paragraph()
                sections.append({'title': title, 'blocks': blocks})

        return sections


def build_page_component(sections, note_title=None):
        sections_json = json.dumps(sections, ensure_ascii=False, indent=2)
        return f"""type Block =
    | {{ type: 'paragraph'; text: string }}
    | {{ type: 'image'; alt: string; src: string }}
    | {{ type: 'heading'; level: number; text: string }};

type Section = {{
    title: string;
    blocks: Block[];
}};

const sections: Section[] = {sections_json};
const noteTitle: string = {json.dumps(note_title, ensure_ascii=False)};


function renderHeading(level: number, text: string) {{
    if (level === 2) {{
        return <h2 className="mt-8 text-2xl font-semibold text-slate-900">{{text}}</h2>;
    }}

    if (level === 3) {{
        return <h3 className="mt-6 text-xl font-semibold text-slate-900">{{text}}</h3>;
    }}

    return <h4 className="mt-4 text-lg font-semibold text-slate-900">{{text}}</h4>;
}}

export default function Page() {{
    return (
        <main className="min-h-screen bg-slate-50 px-6 py-12 text-slate-800">
            <h1 className="text-4xl font-bold tracking-tight text-slate-950 mb-8">{{noteTitle}}</h1>

            <div className="mx-auto flex max-w-4xl flex-col gap-8">
                {{sections.map((section, sectionIndex) => (
                    <article
                        key={{`${{section.title}}-${{sectionIndex}}`}}
                        className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm"
                    >
                        <h1 className="text-3xl font-bold tracking-tight text-slate-950">{{section.title}}</h1>
                        <div className="mt-6 space-y-4 leading-8 text-slate-700">
                            {{section.blocks.map((block, blockIndex) => {{
                                if (block.type === 'paragraph') {{
                                    return <p key={{blockIndex}}>{{block.text}}</p>;
                                }}

                                if (block.type === 'image') {{
                                    return (
                                        <img
                                            key={{blockIndex}}
                                            src={{`${{process.env.NEXT_PUBLIC_CLOUDFLARE_R2_HOST}}/${{block.src}}`}}
                                            alt={{block.alt}}
                                            className="w-full rounded-2xl border border-slate-200 object-cover shadow-sm"
                                        />
                                    );
                                }}

                                return <div key={{blockIndex}}>{{renderHeading(block.level, block.text)}}</div>;
                            }})}}
                        </div>
                    </article>
                ))}}
            </div>
        </main>
    );
}}
"""


def write_page_tsx(markdown_fp, output_fp=None, note_title=None):
        with open(markdown_fp, 'r', encoding='utf-8') as file:
                markdown_text = file.read()

        sections = parse_markdown_sections(markdown_text)
        output_fp = output_fp or os.path.join(os.path.dirname(markdown_fp), 'page.tsx')
        page_component = build_page_component(sections, note_title)

        with open(output_fp, 'w', encoding='utf-8') as file:
                file.write(page_component)

        return output_fp, len(sections)


def generate_chaps(path_to_note, output_chap_txt_fp, deepseek_api_key=None):
    analysis_json_fp = os.path.join(path_to_note, 'output', 'analysis.json')
    if not os.path.exists(analysis_json_fp):
        print(f"File not found: {analysis_json_fp}")
        return None

    output_path = output_chap_txt_fp
    if not os.path.isabs(output_path):
        output_path = os.path.join(path_to_note, output_path)

    with open(analysis_json_fp, 'r', encoding='utf-8') as file:
        try:
            analysis_data = json.load(file)
            text = analysis_data.get('transcript', {}).get('text', '')
        except json.JSONDecodeError as exc:
            print(f"Invalid JSON in file {analysis_json_fp}: {exc}")
            return None

    if not text or not text.strip():
        print(f"Transcript text is empty in file: {analysis_json_fp}")
        return None

    system_content = (
        "You are a note structuring assistant. "
        "Split the provided transcript into a small number of coherent sections. "
        "Return plain text only. For each section, use this exact format: "
        "**Section Title** followed by one or more paragraph lines. "
        "Separate sections with a blank line. "
        "Do not return JSON, code fences, or extra commentary."
    )
    prompt = (
        "Please divide the following transcript into several logical sections for study notes.\n\n"
        "Requirements:\n"
        "1. Keep the original transcript language.\n"
        "2. Generate a concise title for each section, numbered sequentially.\n"
        "3. Use the format **Section Title** on its own line, then the section content below it.\n"
        "4. Separate each section with exactly one blank line.\n"
        "5. Preserve original text\n\n"
        f"Transcript:\n{text.strip()}"
    )

    try:
        response = call_deepseek_chat(
            api_key=deepseek_api_key or os.getenv('DEEPSEEK_API_KEY', ''),
            prompt=prompt,
            system_content=system_content,
        )
        parsed = parse_deepseek_response(response)
        chapter_text = parsed.get('content', '').strip()
    except Exception as exc:
        print(f"Failed to generate chapters with DeepSeek: {exc}")
        return None

    if not chapter_text:
        print("DeepSeek returned empty chapter text.")
        return None

    with open(output_path, 'w', encoding='utf-8') as output_file:
        output_file.write(chapter_text)

    print(f"Chapters saved to: {output_path}")
    return output_path


def main(path_to_note, deepseek_api_key=None):
    print("Welcome to Note Composer!")
    print("This is a simple CLI tool to help you compose notes.")
    print("You can create, edit, and save your notes easily.")

    chap_path = generate_chaps(path_to_note, 'chaps.txt', deepseek_api_key=deepseek_api_key)
    print(f"Generated chapters file at: {chap_path}")

    chapters_fp = chap_path or os.path.join(path_to_note, 'chaps.txt')
    chapters = load_chaps_txt(chapters_fp)
    video_analyzer_output = load_video_analyzer_output_json(
        os.path.join(path_to_note, 'output', 'analysis.json')
    )
    # print(json.dumps(video_analyzer_output, ensure_ascii=False, indent=2))
    composed_notes = complete_note_composition(chapters, video_analyzer_output)

    print(json.dumps(composed_notes, ensure_ascii=False, indent=2))

    with open(os.path.join(path_to_note, 'composed_notes.json'), 'w', encoding='utf-8') as file:
        json.dump(composed_notes, file, ensure_ascii=False, indent=2)
    # Here you would add the logic for handling user input and managing notes
    # For example, you could implement commands like 'create', 'edit', 'save', etc.
    # This is just a placeholder for the actual functionality.



def note_composer_to_markdown_main(file_path, r2_account_id, r2_access_key_id, r2_secret_access_key, BUCKET_NAME, deepseek_api_key=None):

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
    endpoint_url = f"https://{r2_account_id}.r2.cloudflarestorage.com"
    s3_client = boto3.client(
        "s3",
        endpoint_url=endpoint_url,
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
    write_markdown(s3_client, composed_notes, os.path.join(os.path.dirname(file_path), "composed_notes.md"), deepseek_api_key=deepseek_api_key)



def note_markdown_to_pagetsx_main(markdown_fp, output_fp=None, note_title=None):
        output_fp, section_count = write_page_tsx(markdown_fp, output_fp, note_title)
        print(f'Generated {output_fp} from {markdown_fp} with {section_count} sections.')


def parse_args():
    parser = argparse.ArgumentParser(description='Compose notes, upload frame images to R2, and generate page.tsx.')
    parser.add_argument('--fp', required=True, help='Path to the note workspace directory.')
    parser.add_argument('--BUCKET_NAME', required=True, help='Cloudflare R2 bucket name.')
    parser.add_argument('--r2_account_id', required=True, help='Cloudflare R2 account id.')
    parser.add_argument('--r2_access_key_id', required=True, help='Cloudflare R2 access key id.')
    parser.add_argument('--r2_secret_access_key', required=True, help='Cloudflare R2 secret access key.')
    parser.add_argument('--deepseek_api_key', required=False, help='Deepseek API key, optional for future use.')
    parser.add_argument('--note_title', default=None, help='Optional title used in the generated page.tsx.')
    return parser.parse_args()



if __name__ == "__main__":
    args = parse_args()
    fp = args.fp

    main(fp, deepseek_api_key=args.deepseek_api_key)
    note_composer_to_markdown_main(
        os.path.join(fp, "composed_notes.json"),
        args.r2_account_id,
        args.r2_access_key_id,
        args.r2_secret_access_key,
        args.BUCKET_NAME,
        deepseek_api_key=args.deepseek_api_key,
    )
    note_markdown_to_pagetsx_main(
        os.path.join(fp, "composed_notes.md"),
        note_title=args.note_title or os.path.basename(os.path.normpath(fp)),
    )
