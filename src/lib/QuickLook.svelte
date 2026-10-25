<script>
  import { jobs, onDownloadClick, onAltClick, onWallpaperEngine, onPortrait, weKey, portraitKey, say } from './downloads.svelte.js';
  import { VLABEL, section, patSize, mb } from './versions.js';
  import { catName } from './data.js';
  import { ARROW, WE_ICON, PORTRAIT, WORKSHOP, LINK } from './icons.js';

  let { d, open, list, onselect, onclose } = $props();
  let stage = $state(), video = $state();
  let playing = $state(false), failed = $state(false);
  const job = $derived(d && jobs.get(d.i));
  const sec = $derived(d ? section(d) : '');
  const what = $derived(!d ? '' : d.kind === 'aerial' ? '4K video' : d.kind === 'set' ? `Dynamic aerial · ${d.we.parts.length} videos`
    : d.anim ? 'Animated wallpaper'
    : d.kind === 'builtin' ? 'Live wallpaper' : d.pattern ? 'Pattern' : d.dyn ? 'Dynamic picture' : 'Picture');
  const label = $derived(job?.state === 'loading' ? (job.p == null ? 'Downloading…' : `Downloading ${Math.round(job.p * 100)}%`)
    : job?.state === 'done' ? 'Downloaded' : d?.kind === 'set' ? 'Download videos' : 'Download');
  const weJob = $derived(d && jobs.get(weKey(d)));
  const ptJob = $derived(d && jobs.get(portraitKey(d)));
  const ptLabel = $derived(ptJob?.state === 'loading' ? `Portrait ${Math.round((ptJob.p ?? 0) * 100)}%`
    : ptJob?.state === 'done' ? 'Saved' : 'Portrait');
  const weLabel = $derived(weJob?.state === 'loading' ? `Building ${Math.round((weJob.p ?? 0) * 100)}%`
    : weJob?.state === 'done' ? 'Saved' : 'Wallpaper Engine');
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;

  async function copyLink() {
    // w/<id>/ is a page made at build time with the wallpaper's preview for chats (scripts/share-pages.js)
    const url = location.origin + location.pathname + (import.meta.env.DEV ? '#' + d.id : `w/${d.id}/`);
    try { await navigator.clipboard.writeText(url); say(`Copied a link to “${d.n}”`); }
    catch { prompt('Copy this link:', url); } // clipboard can be blocked (e.g. insecure contexts)
  }

  // Stream the real video while open; the blurred thumbnail and spinner hold its place until it plays
  $effect(() => {
    if (!video) return;
    playing = failed = false;
    if (open && d?.video) { video.src = d.video; video.play().catch(() => {}); }
    else { video.pause(); video.removeAttribute('src'); video.load(); }
  });

  // Browsers that don't trust Apple's video server (Chrome) get the short clip the site hosts instead
  function onVideoError() {
    const src = video.getAttribute('src');
    if (!src) return;
    if (d.clip && src !== d.clip) { video.src = d.clip; video.play().catch(() => {}); }
    else failed = true;
  }

  export function step(dir) {
    const k = list.findIndex(x => x.i === d.i);
    onselect(list[(k + dir + list.length) % list.length].i);
    stage.animate([{ opacity: 0, transform: `translateX(${dir * 24}px)` }, { opacity: 1, transform: 'none' }],
      { duration: 280, easing: 'cubic-bezier(.2,.8,.2,1)' });
  }

  // The thumbnail zooms between its tile and the preview
  const box = el => { const r = el.getBoundingClientRect(); return { left: r.left + 'px', top: r.top + 'px', width: r.width + 'px', height: r.height + 'px' }; };
  function fly(from, to, radius, done) {
    const g = Object.assign(document.createElement('img'), { className: 'ghost', src: d.img, alt: '' });
    Object.assign(g.style, box(from), { transition: 'none' });
    document.body.append(g);
    requestAnimationFrame(() => requestAnimationFrame(() => { g.style.transition = ''; Object.assign(g.style, box(to), { borderRadius: radius }); }));
    let ended = false;
    const end = () => {
      if (ended) return;
      ended = true;
      done?.();
      g.style.transition = 'opacity .15s';
      g.style.opacity = 0;
      setTimeout(() => g.remove(), 160);
    };
    g.addEventListener('transitionend', e => (e.propertyName === 'width' || e.propertyName === 'top') && end());
    setTimeout(end, 600); // in case nothing actually moved
  }
  export function flyIn(tile) {
    if (!tile || reduced) return;
    stage.style.visibility = 'hidden';
    fly(tile, stage, '0px', () => (stage.style.visibility = ''));
  }
  export function flyOut(tile) {
    if (tile && !reduced) fly(stage, tile, '8px');
  }
</script>

<div class="ql" class:open aria-hidden={!open} inert={!open} role="presentation" onclick={e => e.target === e.currentTarget && onclose()}>
  <div class="ql-panel" role="dialog" aria-modal="true" aria-labelledby="ql-title">
    {#if d}
      <div class="ql-bar">
        <div class="lights"><button title="Close" aria-label="Close" onclick={onclose}></button><i></i><i></i></div>
        <div class="ql-title" id="ql-title">
          {d.n}<small>{VLABEL[d.v]} · {sec && sec !== catName(d.c) ? sec + ' · ' : ''}{catName(d.c)} · {what}{d.size ? ' · ' + mb(d.size) : ''}</small>
        </div>
        <button class="btn alt-btn" onclick={copyLink} title="Copy a link that opens this wallpaper">
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">{@html LINK}</svg>
          <span>Copy Link</span>
        </button>
        {#if d.portrait}
          <a class="btn alt-btn" href="#portrait" style:--p={ptJob?.p ?? 0} onclick={e => onPortrait(e, d)}
            title="The light and dark videos for portrait screens">
            <span class="fill"></span>
            <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">{@html PORTRAIT}</svg>
            <span>{ptLabel}</span>
          </a>
        {/if}
        {#if d.we}
          <a class="btn alt-btn" href="#wallpaper-engine" style:--p={weJob?.p ?? 0} onclick={e => onWallpaperEngine(e, d)}
            title="A Wallpaper Engine package that follows the time of day">
            <span class="fill"></span>
            <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">{@html WE_ICON}</svg>
            <span>{weLabel}</span>
          </a>
        {/if}
        {#if d.kind === 'builtin'}
          <span class="btn off">Built into macOS</span>
        {:else}
          <a class="btn" href={d.url} target="_blank" rel="noopener" style:--p={job?.p ?? 0} onclick={e => onDownloadClick(e, d)}>
            <span class="fill"></span>
            <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{@html ARROW}</svg>
            <span>{label}</span>
          </a>
        {/if}
      </div>
    {/if}
    <div class="ql-img" bind:this={stage} class:playing class:failed class:still={d && !d.video} class:pattern={d?.pattern}
      style:background-image={d?.pattern ? `url('${d.img}')` : null} style:background-size={d?.pattern ? patSize(d) * 2 + 'px' : null}>
      {#if d && !d.pattern}<img src={d.img} alt="">{/if}
      <video bind:this={video} muted loop playsinline preload="auto"
        onplaying={() => (playing = true)} onerror={onVideoError}></video>
      <div class="spinner" aria-hidden="true">
        {#each Array(8) as _, k}<i style="transform: rotate({k * 45}deg); animation-delay: {(k - 8) / 8}s"></i>{/each}
      </div>
      <button class="ql-nav ql-prev" aria-label="Previous" onclick={() => step(-1)}>
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 3 5 8l5 5"/></svg>
      </button>
      <button class="ql-nav ql-next" aria-label="Next" onclick={() => step(1)}>
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m6 3 5 5-5 5"/></svg>
      </button>
    </div>
    {#if d && (d.note || d.post || d.alts?.length || d.workshop)}
      <div class="ql-foot">
        {#if d.note || d.post}
          <div class="ql-note">{d.note ?? ''}{#if d.post} · <a href={d.post} target="_blank" rel="noopener">Source</a>{/if}</div>
        {/if}
        {#if d.workshop}
          <div class="ql-alts" title="Subscribe on the Workshop and Wallpaper Engine adds it">
            {#each d.workshop as w}
              <a class="alt" href={w.u} target="_blank" rel="noopener">
                <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">{@html WORKSHOP}</svg>Steam Workshop · {w.l}
              </a>
            {/each}
          </div>
        {/if}
        {#if d.alts?.length}
          <div class="ql-alts">
            {#each d.alts as alt}
              <a class="alt" href={alt.u} target="_blank" rel="noopener" title={alt.size ? mb(alt.size) : ''} onclick={e => onAltClick(e, d, alt)}>
                <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{@html ARROW}</svg>{alt.l}
              </a>
            {/each}
          </div>
        {/if}
      </div>
    {/if}
  </div>
</div>
