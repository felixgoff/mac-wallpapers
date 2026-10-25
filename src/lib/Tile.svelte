<script>
  import { jobs, onDownloadClick, onWallpaperEngine, onPortrait, weKey, portraitKey } from './downloads.svelte.js';
  import { patSize, mb } from './versions.js';
  import { ARROW, WE_ICON, PORTRAIT, WORKSHOP } from './icons.js';

  let { d, order, selected, onselect, onopen } = $props();
  let loaded = $state(false);
  const job = $derived(jobs.get(d.i));
  const weJob = $derived(jobs.get(weKey(d)));
  const ptJob = $derived(jobs.get(portraitKey(d)));

  // An image already in the cache can finish before Svelte attaches onload
  const ready = img => { if (img.complete && img.naturalWidth) loaded = true; };
</script>

<!-- A round tile button with a progress ring: download, portrait or Wallpaper Engine -->
{#snippet button(kind, href, icon, stroke, job, label, title, onclick)}
  <a class="dl {kind}" {href} target={kind ? null : '_blank'} rel="noopener" aria-label={label} {title}
    class:loading={job?.state === 'loading'} class:indeterminate={job?.state === 'loading' && job.p == null}
    class:done={job?.state === 'done'} style:--p={job?.p ?? 0}
    onclick={e => { e.stopPropagation(); onclick(e, d); }}>
    <svg class="arrow" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width={stroke} stroke-linecap="round" stroke-linejoin="round">{@html icon}</svg>
    <svg class="ok" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m3.5 8.5 3 3 6-7"/></svg>
    <svg class="ring" viewBox="0 0 24 24"><circle class="track" cx="12" cy="12" r="9"/><circle class="bar" cx="12" cy="12" r="9"/></svg>
    <svg class="stop" viewBox="0 0 16 16"><rect x="5" y="5" width="6" height="6" rx="1" fill="currentColor"/></svg>
  </a>
{/snippet}

<!-- Arrow keys, Space and Enter are handled for the whole grid in App.svelte -->
<!-- svelte-ignore a11y_click_events_have_key_events -->
<div class="tile" role="option" tabindex={selected ? 0 : -1} data-i={d.i} aria-selected={selected} style:--i={Math.min(order, 24)}
  onclick={() => onselect(d.i)} ondblclick={() => onopen(d.i)}>
  <div class="thumb">
    {#if d.pattern}
      <div class="frame pat ok" style:background-image="url('{d.img}')" style:background-size="{patSize(d)}px"></div>
    {:else}
      <div class="frame" class:ok={loaded}>
        <img loading="lazy" src={d.img} alt="" use:ready onload={() => (loaded = true)} onerror={() => (loaded = true)}>
      </div>
    {/if}
    {#if d.dyn && !d.anim}
      <span class="dynb" title="Dynamic wallpaper: changes with Light and Dark appearance"></span>
    {/if}
    {#if d.anim}
      <span class="anim" title="Animated wallpaper">
        <svg viewBox="0 0 10 10" aria-hidden="true"><path d="M3 1.8v6.4a.5.5 0 0 0 .76.43l5.2-3.2a.5.5 0 0 0 0-.86l-5.2-3.2A.5.5 0 0 0 3 1.8z" fill="currentColor"/></svg>
      </span>
    {/if}
    {#if d.kind === 'builtin' && d.workshop}
      <!-- nothing to download, but it's on the Steam Workshop for Wallpaper Engine -->
      <a class="dl" href={d.workshop[0].u} target="_blank" rel="noopener" aria-label="{d.n} on the Steam Workshop"
        title="Wallpaper Engine: “{d.n}” on the Steam Workshop ({d.workshop[0].l})" onclick={e => e.stopPropagation()}>
        <svg class="arrow" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">{@html WORKSHOP}</svg>
      </a>
    {/if}
    {#if d.kind !== 'builtin'}
      {@render button('', d.url, ARROW, 1.8, job, `Download “${d.n}”`,
        job?.state === 'loading' ? `Downloading “${d.n}”${job.total ? ` — ${mb(job.got)} of ${mb(job.total)}` : ''}. Click to stop.`
          : d.kind === 'set' ? `Download the “${d.n}” videos (${mb(d.size)}, best in Safari)`
          : `Download “${d.n}”${d.kind === 'aerial' ? ' (4K video)' : ''}`, onDownloadClick)}
    {/if}
    {#if d.portrait}
      {@render button('pt', '#portrait', PORTRAIT, 1.6, ptJob, `Download ${d.n} for portrait screens`,
        ptJob?.state === 'loading' ? `Downloading the portrait videos — ${mb(ptJob.got)} of ${mb(ptJob.total)}. Click to stop.`
          : `Portrait: the light and dark videos for portrait screens (${mb(d.portrait.size)}, best in Safari)`, onPortrait)}
    {/if}
    {#if d.we}
      {@render button('we', '#wallpaper-engine', WE_ICON, 1.6, weJob, `Wallpaper Engine: ${d.n}`,
        weJob?.state === 'loading' ? `Building for Wallpaper Engine${weJob.total ? ` — ${mb(weJob.got)} of ${mb(weJob.total)}` : ''}. Click to stop.`
          : `Wallpaper Engine: a package that follows the time of day${d.we.video ? ` (${mb(d.size)} of videos, best in Safari)` : ''}`, onWallpaperEngine)}
    {/if}
  </div>
  <div class="name" title={d.n}>{d.n}</div>
</div>
