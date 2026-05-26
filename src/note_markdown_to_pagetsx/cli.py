
import argparse
import json
import os
import re


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
                                            src={{block.src}}
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


def main(markdown_fp, output_fp=None, note_title=None):
        output_fp, section_count = write_page_tsx(markdown_fp, output_fp, note_title)
        print(f'Generated {output_fp} from {markdown_fp} with {section_count} sections.')


if __name__ == '__main__':
        parser = argparse.ArgumentParser(description='Generate a Next.js page.tsx from a markdown file.')
        parser.add_argument('markdown_fp', nargs='?', default='D:\\toolnotes_pro\\docs\\robloxstudio\\1_robloxstudio_introduction_and_download\\composed_notes.md')
        parser.add_argument('--output', dest='output_fp', default=None, help='Optional output path for page.tsx')
        args = parser.parse_args()
        main(args.markdown_fp, args.output_fp, note_title='Roblox Studio简介与下载')
