'use client';

import { useEffect, useRef, useState } from 'react';

function Icon({ name, size = 20 }) {
  const paths = {
    book: <><path d="M4 5h6a3 3 0 0 1 3 3v12a4 4 0 0 0-3-2H4z"/><path d="M13 8a3 3 0 0 1 3-3h4v13h-4a4 4 0 0 0-3 2"/></>,
    arrow: <><path d="M12 19V5m-5 5 5-5 5 5"/></>,
    plus: <path d="M12 5v14M5 12h14"/>,
    external: <><path d="M14 4h6v6m0-6-10 10"/><path d="M20 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1h5"/></>,
    chevron: <path d="m9 5 7 7-7 7"/>,
    file: <><path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6M8 13h8M8 17h5"/></>,
    menu: <path d="M4 6h16M4 12h16M4 18h16"/>,
    close: <path d="m6 6 12 12M18 6 6 18"/>,
  };
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>;
}

function Evidence({ passages, title = 'Sources' }) {
  return <div className="evidence"><h3>{title}</h3>{passages.map((source, i) =>
    <details key={source.id} className="source">
      <summary><span className="source-number">{i + 1}</span><span><strong>{source.document}</strong><span className="section-name">{source.section}</span></span><Icon name="chevron" size={16}/></summary>
      <div className="source-body"><blockquote>{source.text}</blockquote>
        <a href={source.url} target="_blank" rel="noreferrer">Open original document <Icon name="external" size={13}/></a>
        <span className="source-file">{source.filename}</span>
      </div>
    </details>
  )}</div>;
}

export default function Chat({ documents, examples, chunkCount }) {
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState('');
  const [busy, setBusy] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const end = useRef(null);
  const input = useRef(null);
  const activeRequest = useRef(null);
  useEffect(() => { end.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }); }, [messages, busy]);
  useEffect(() => () => activeRequest.current?.abort(), []);

  async function send(value = question) {
    const text = value.trim();
    if (!text || busy) return;
    setQuestion(''); setMenuOpen(false); setBusy(true);
    setMessages(previous => [...previous, { role: 'user', text }]);
    const controller = new AbortController();
    activeRequest.current = controller;
    const timeout = setTimeout(() => controller.abort(), 145000);
    try {
      const response = await fetch('/api/ask', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question: text }), signal: controller.signal });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || 'The answer could not be loaded. Please try again.');
      setMessages(previous => [...previous, { role: 'assistant', ...result }]);
    } catch (error) {
      const message = error.name === 'AbortError' ? 'The request took too long. Please try again.' : error.message;
      setMessages(previous => [...previous, { role: 'error', text: message, question: text }]);
    } finally {
      clearTimeout(timeout); setBusy(false); activeRequest.current = null; input.current?.focus();
    }
  }

  return <div className="app-shell">
    {menuOpen && <button className="sidebar-scrim" aria-label="Close navigation" onClick={() => setMenuOpen(false)}/>}
    <aside className={`sidebar ${menuOpen ? 'is-open' : ''}`} aria-label="Knowledge library">
      <a className="brand" href="/"><span className="brand-mark"><Icon name="book" size={23}/></span><span>source<span className="brand-dot">.</span></span></a>
      <button className="new-chat" disabled={busy} onClick={() => { setMessages([]); setQuestion(''); setMenuOpen(false); input.current?.focus(); }}><Icon name="plus" size={17}/> New conversation</button>
      <nav className="sidebar-section" aria-label="Example questions"><h2>Try a question</h2>{examples.map(example =>
        <button className="example-nav" disabled={busy} key={example.label} onClick={() => send(example.question)}>{example.label}<Icon name="chevron" size={14}/></button>
      )}</nav>
      <div className="sidebar-section library"><h2>Knowledge library <span>{documents.length}</span></h2>{documents.map(document =>
        <a className="document-link" key={document.file} href={document.url} target="_blank" rel="noreferrer"><Icon name="file" size={18}/><span>{document.title}<small>Automattic · Markdown</small></span><Icon name="external" size={12}/></a>
      )}<p>Documents captured on 9 Oct 2026.</p></div>
      <div className="sidebar-bottom"><span className={`status-dot ${chunkCount ? '' : 'pending'}`}/><span>{chunkCount ? `${chunkCount} passages indexed` : 'Index preparation pending'}</span>
        <a href="https://github.com/mitul-bhatia/E-Bibil_assignment" target="_blank" rel="noreferrer">View the code <Icon name="external" size={13}/></a>
      </div>
    </aside>

    <main className="main-panel">
      <header className="topbar"><div><button className="mobile-menu" aria-label="Open navigation" aria-expanded={menuOpen} onClick={() => setMenuOpen(true)}><Icon name="menu"/></button><span>Client knowledge assistant</span></div><span className="demo-label">eBibil assessment</span></header>
      <div className="conversation" aria-label="Conversation" aria-busy={busy}>
        {!messages.length ? <section className="welcome">
          <div className="welcome-symbol"><Icon name="book" size={38}/></div>
          <h1>Ask a question.<br/><span>Follow the evidence.</span></h1>
          <p>Clear answers from Automattic’s policies.<br/>Every answer comes with a source you can read.</p>
          <div className="starter-list">{examples.slice(0, 4).map(example => <button key={example.label} disabled={busy} onClick={() => send(example.question)}><span>{example.label}</span><Icon name="chevron" size={16}/></button>)}</div>
          <button className="unknown-example" disabled={busy} onClick={() => send(examples.at(-1).question)}>Or try a question the documents can’t answer <Icon name="chevron" size={14}/></button>
        </section> : <div className="message-list">{messages.map((message, i) =>
          message.role === 'user' ? <article className="user-message" key={i}><span className="message-label">You</span><p>{message.text}</p></article> :
          message.role === 'error' ? <article className="error-message" key={i} role="alert"><h2>Couldn’t complete this answer</h2><p>{message.text}</p><button disabled={busy} onClick={() => send(message.question)}>Try again</button></article> :
          <article className="assistant-message" key={i}><div className="assistant-label"><span className="mini-brand"><Icon name="book" size={15}/></span>Source<span className="answer-state">{message.answerable ? 'Supported by documents' : 'Not in these documents'}</span></div>
            <p className="answer-text">{message.answer}</p>
            {!message.answerable && <p className="unknown-note">These policies don’t provide the information needed to answer that question.</p>}
            {!!message.sources.length && <Evidence passages={message.sources}/>}
            <details className="retrieval-details"><summary>How this answer was found <span>{(message.elapsedMs / 1000).toFixed(1)}s</span></summary><p>Your question was embedded, compared with the saved vectors, and the {message.retrieved.length} closest passages were sent to Gemini. Citation IDs were checked against these passages.</p><Evidence passages={message.retrieved} title="Retrieved passages"/></details>
          </article>
        )}</div>}
        {busy && <div className="working" role="status"><span className="working-dot"/><span>Finding evidence and preparing your answer…</span></div>}
        <div ref={end}/>
      </div>
      <div className="composer-area"><form className="composer" onSubmit={event => { event.preventDefault(); send(); }}>
        <label className="sr-only" htmlFor="question">Ask about Automattic policies</label>
        <textarea id="question" ref={input} value={question} maxLength={1000} rows={2} placeholder="Ask about privacy, subscriptions, or cookies…" disabled={busy} onChange={event => setQuestion(event.target.value)} onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); send(); } }}/>
        <div className="composer-actions"><span><span className="status-dot"/> Answers from {documents.length} documents</span><button className="send-button" type="submit" disabled={busy || !question.trim()} aria-label="Send question"><Icon name="arrow" size={19}/></button></div>
      </form><p className="composer-note">Each question is answered independently. Check the sources for important details.</p>
      </div>
    </main>
  </div>;
}
