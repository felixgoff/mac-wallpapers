<script>
  import { onMount, tick } from 'svelte';
  import { items, cats, catName, counts, byId } from './lib/data.js';
  import { visibleItems, groupItems, inCategory } from './lib/group.js';
  import { ICONS } from './lib/icons.js';
  import { toast } from './lib/downloads.svelte.js';
  import Tile from './lib/Tile.svelte';
  import QuickLook from './lib/QuickLook.svelte';

  let cat = $state('all'), q = $state(''), selected = $state(null), qlOpen = $state(false), scrolled = $state(false);
  let sortBy = $state(savedSort());
  function savedSort() {
    try { return localStorage.getItem('sortBy') === 'version' ? 'version' : 'category'; } catch { return 'category'; }
  }

  const visible = $derived(visibleItems(items, { cat, q, sortBy, catName }));
  const groups = $derived(groupItems(visible, { sortBy, catName, cat }));
  const title = $derived(cat === 'all' ? 'All Wallpapers' : catName(cat));
  // Running tile index, so only the first couple of dozen tiles stagger in
  const starts = $derived(groups.reduce((acc, g, k) => [...acc, k ? acc[k - 1] + groups[k - 1].items.length : 0], []));
  const sub = g => sortBy === 'version' ? String(g.items.length)
    : cat === 'all' && !g.more && g.label !== catName(g.c) ? catName(g.c) : '';

  let scroller = $state(), search = $state(), ql = $state();
  const navButtons = {}, segButtons = {};

  // Sliding highlights for the sidebar and the segmented control; no animation on first paint or resize
  let animated = $state(false), pill = $state(''), thumb = $state('');
  const layout = () => {
    const b = navButtons[cat], s = segButtons[sortBy];
    pill = `width:${b.offsetWidth}px;height:${b.offsetHeight}px;transform:translate(${b.offsetLeft}px,${b.offsetTop}px)`;
    thumb = `width:${s.offsetWidth}px;transform:translateX(${s.offsetLeft}px)`;
  };
  $effect(layout);
  const settle = () => requestAnimationFrame(() => requestAnimationFrame(() => (animated = true)));
  onMount(() => { settle(); openFromLink(); });

  // Share links: …/#macos-tahoe opens that wallpaper's Quick Look; the address follows what's open
  async function openFromLink() {
    const d = byId.get(decodeURIComponent(location.hash.slice(1)));
    if (!d) return closeQL();
    if (!inCategory(d, cat) || !visible.includes(d)) { cat = d.c; q = ''; }
    await tick();
    tileEl(d.i)?.scrollIntoView({ block: 'center' });
    openQL(d.i);
  }
  $effect(() => {
    const d = qlOpen && selected != null ? items[selected] : null;
    const hash = d ? '#' + d.id : '';
    if (location.hash !== hash) history.replaceState(null, '', hash || location.pathname + location.search);
    document.title = d ? `${d.n} — Mac Wallpapers` : 'Mac Wallpapers';
  });
  function relayout() { animated = false; layout(); settle(); }

  function pick(c) {
    if (c === cat) return;
    cat = c;
    scroller.scrollTop = 0;
    navButtons[c].scrollIntoView({ block: 'nearest', inline: 'nearest', behavior: 'smooth' });
  }
  function sort(s) {
    if (s === sortBy) return;
    sortBy = s;
    try { localStorage.setItem('sortBy', s); } catch {}
    scroller.scrollTop = 0;
  }

  const tileEl = i => scroller.querySelector(`.tile[data-i="${i}"]`);
  async function select(i, focus) {
    selected = i;
    if (!focus) return;
    await tick();
    tileEl(i)?.focus({ preventScroll: true });
    tileEl(i)?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }
  async function openQL(i) {
    selected = i;
    qlOpen = true;
    await tick();
    requestAnimationFrame(() => ql.flyIn(tileEl(i)?.querySelector('.frame')));
  }
  function closeQL() {
    if (!qlOpen) return;
    ql.flyOut(tileEl(selected)?.querySelector('.frame'));
    qlOpen = false;
    tileEl(selected)?.focus({ preventScroll: true });
  }

  // Arrow keys move like Finder's icon view: left/right through the list, up/down to the nearest tile in the next row
  function step(dx, dy) {
    const tiles = [...scroller.querySelectorAll('.tile')];
    if (!tiles.length) return;
    let k = tiles.findIndex(t => +t.dataset.i === selected);
    if (k < 0) return select(+tiles[0].dataset.i, true);
    if (dy) {
      const r = tiles[k].getBoundingClientRect(), cx = r.left + r.width / 2;
      const rows = tiles.filter(t => { const b = t.getBoundingClientRect(); return dy > 0 ? b.top > r.top + 5 : b.top < r.top - 5; });
      if (!rows.length) return;
      const tops = rows.map(t => t.getBoundingClientRect().top);
      const rowTop = dy > 0 ? Math.min(...tops) : Math.max(...tops);
      const dist = t => { const b = t.getBoundingClientRect(); return Math.abs(b.top - rowTop) < 5 ? Math.abs(b.left + b.width / 2 - cx) : Infinity; };
      return select(+rows.reduce((a, t) => (dist(t) < dist(a) ? t : a)).dataset.i, true);
    }
    select(+tiles[Math.max(0, Math.min(tiles.length - 1, k + dx))].dataset.i, true);
  }

  function onkey(e) {
    if (e.target === search) {
      if (e.key === 'Escape') { q = ''; search.blur(); }
      return;
    }
    if ((e.metaKey || e.ctrlKey) && e.key === 'f') { e.preventDefault(); search.focus(); return; }
    if (e.target.closest?.('button, a, input') && (e.key === ' ' || e.key === 'Enter')) return; // buttons and links keep their own Space/Enter
    if (e.key === ' ' || (qlOpen && e.key === 'Escape')) {
      e.preventDefault();
      if (qlOpen) closeQL(); else if (selected != null) openQL(selected);
      return;
    }
    const k = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] }[e.key];
    if (k) { e.preventDefault(); if (qlOpen) ql.step(k[0] || k[1]); else step(...k); }
    if (e.key === 'Enter' && selected != null && !qlOpen) openQL(selected);
  }
</script>

<svelte:window onkeydown={onkey} onresize={relayout} onhashchange={openFromLink} />

{#snippet icon(name)}
  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round" stroke-linecap="round" aria-hidden="true">{@html ICONS[name] ?? ICONS.all}</svg>
{/snippet}

<div class="desktop"></div>
<div class="window">
  <nav class="sidebar" aria-label="Categories">
    <div class="lights" aria-hidden="true"><i></i><i></i><i></i></div>
    <div class="pill" class:instant={!animated} style={pill}></div>
    <button class="item" bind:this={navButtons.all} aria-current={cat === 'all'} onclick={() => pick('all')}>
      {@render icon('all')}All Wallpapers<span class="ct">{items.length}</span>
    </button>
    {#each cats as c, k (c.id)}
      {#if k === 0 || cats[k - 1].g !== c.g}<h6>{c.g}</h6>{/if}
      <button class="item" bind:this={navButtons[c.id]} aria-current={cat === c.id} onclick={() => pick(c.id)}>
        {@render icon(c.n)}{c.n}<span class="ct">{counts[c.id]}</span>
      </button>
    {/each}
  </nav>

  <main class="content">
    <div class="toolbar" class:scrolled>
      {#key title + sortBy}
        <div class="heading swap">
          <div class="t">{title}</div>
          <div class="st">{visible.length} wallpaper{visible.length === 1 ? '' : 's'}</div>
        </div>
      {/key}
      <div class="seg" role="radiogroup" aria-label="Group wallpapers by">
        <span class="seg-thumb" class:instant={!animated} style={thumb} aria-hidden="true"></span>
        <button role="radio" aria-checked={sortBy === 'category'} bind:this={segButtons.category} onclick={() => sort('category')}>Category</button>
        <button role="radio" aria-checked={sortBy === 'version'} bind:this={segButtons.version} onclick={() => sort('version')}><span class="long">{'macOS '}</span>Version</button>
      </div>
      <label class="search" class:has={q}>
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" aria-hidden="true"><circle cx="6.8" cy="6.8" r="4.8"/><path d="m10.4 10.4 3.8 3.8"/></svg>
        <input bind:this={search} bind:value={q} type="search" placeholder="Search" aria-label="Search wallpapers" autocomplete="off" spellcheck="false">
        <button class="clear" aria-label="Clear search" onclick={e => { e.preventDefault(); q = ''; search.focus(); }}>
          <svg viewBox="0 0 8 8" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><path d="m1.5 1.5 5 5m0-5-5 5"/></svg>
        </button>
      </label>
    </div>

    <div class="scroll" bind:this={scroller} onscroll={() => (scrolled = scroller.scrollTop > 0)}>
      {#if !visible.length}
        <div class="empty">
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round" aria-hidden="true"><circle cx="6.8" cy="6.8" r="4.8"/><path d="m10.4 10.4 3.8 3.8"/></svg>
          No Results for “{q.trim()}”
        </div>
      {:else}
        {#each groups as g, gk (g.key)}
          <section class="section">
            {#if !(groups.length === 1 && g.label === title)}
              <h2>{g.label}{#if sub(g)}<small>{sub(g)}</small>{/if}</h2>
            {/if}
            <div class="grid" role="listbox" aria-label={g.label}>
              {#each g.items as d, k (d.i)}
                <Tile {d} order={starts[gk] + k} selected={d.i === selected} onselect={i => select(i, false)} onopen={openQL} />
              {/each}
            </div>
          </section>
        {/each}
      {/if}
    </div>
  </main>
</div>

<QuickLook bind:this={ql} d={selected == null ? null : items[selected]} open={qlOpen} list={visible}
  onselect={i => select(i, true)} onclose={closeQL} />

<div class="toast" class:show={toast.show} role="status" aria-live="polite">{toast.msg}</div>
