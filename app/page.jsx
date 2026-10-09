import Chat from './Chat.jsx';
import manifest from '../data/sources.json';
import examples from '../data/examples.json';
import index from '../data/index.json';

export default function Page() {
  return <Chat documents={manifest.documents.map(({ title, file, source_url }) => ({ title, file, url: source_url }))}
    examples={examples} chunkCount={index.chunks.length} />;
}
