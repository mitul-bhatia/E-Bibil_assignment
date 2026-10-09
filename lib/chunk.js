// Split by Markdown heading, then by size. No LLM or tokenizer is needed here.
export function chunkDocument(text, source, maxChars = 1800, overlap = 200) {
  const lines = text.split(/(?<=\n)/);
  const sections = [];
  let heading = 'Introduction';
  let content = '';
  const hierarchy = [];
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const atx = line.trim().match(/^(#{1,6})\s+(.+?)\s*#*$/);
    const setext = line.trim() && lines[i + 1]?.trim().match(/^(=+|-+)$/);
    if (atx || setext) {
      if (content) sections.push({ heading, text: content });
      const level = atx ? atx[1].length : setext[1][0] === '=' ? 1 : 2;
      const title = (atx ? atx[2] : line.trim()).replace(/[*`]/g, '').replace(/\\\./g, '.');
      while (hierarchy.length && hierarchy.at(-1).level >= level) hierarchy.pop();
      hierarchy.push({ level, title });
      heading = hierarchy.map(item => item.title).join(' → ');
      content = '';
    }
    content += line;
  }
  if (content) sections.push({ heading, text: content });
  const chunks = [];
  for (const section of sections) {
    let start = 0;
    while (start < section.text.length) {
      let end = Math.min(start + maxChars, section.text.length);
      if (end < section.text.length) {
        const boundary = section.text.lastIndexOf('\n\n', end);
        const space = section.text.lastIndexOf(' ', end);
        if (boundary > start + maxChars / 2) end = boundary;
        else if (space > start + maxChars / 2) end = space;
      }
      const passage = section.text.slice(start, end);
      if (passage.trim()) chunks.push({
        id: `${source.file.split('/').at(-1).replace('.md', '')}-${chunks.length + 1}`,
        document: source.title, filename: source.file.split('/').at(-1),
        section: section.heading, url: source.source_url, text: passage,
      });
      if (end === section.text.length) break;
      start = Math.max(start + 1, end - overlap);
    }
  }
  return chunks;
}
