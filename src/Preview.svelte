<script>
  // The desktop app's Quick Look window: one wallpaper, stepping through the list the gallery showed when it opened it
  import { onMount } from 'svelte';
  import { getCurrentWebviewWindow } from '@tauri-apps/api/webviewWindow';
  import { items, byId } from './lib/data.js';
  import { PREVIEW } from './lib/desktop.js';
  import { toast } from './lib/downloads.svelte.js';
  import Activity from './lib/Activity.svelte';
  import QuickLook from './lib/QuickLook.svelte';

  const win = getCurrentWebviewWindow();
  const saved = () => {
    try { return JSON.parse(localStorage.getItem('previewList')).map(i => items[i]).filter(Boolean); } catch { return []; }
  };
  const read = () => { const l = saved(); return l.length ? l : items; };
  let list = $state.raw(read()), selected = $state(byId.get(PREVIEW)?.i ?? 0), ql = $state();
  const d = $derived(items[selected]);

  $effect(() => { document.title = d.n; win.setTitle(d.n); });
  // the gallery opened another wallpaper while this window was open
  onMount(() => {
    const off = win.listen('show', e => { list = read(); selected = byId.get(e.payload)?.i ?? selected; });
    return () => off.then(f => f());
  });

  function onkey(e) {
    if (e.target.closest?.('button, a, input') && (e.key === ' ' || e.key === 'Enter')) return;
    if (e.key === ' ' || e.key === 'Escape') { e.preventDefault(); win.close(); return; }
    const k = { ArrowLeft: -1, ArrowUp: -1, ArrowRight: 1, ArrowDown: 1 }[e.key];
    if (k) { e.preventDefault(); ql.step(k); }
  }
</script>

<svelte:window onkeydown={onkey} />

<QuickLook bind:this={ql} {d} open {list} onselect={i => (selected = i)} onclose={() => win.close()} />

<div class="toast" class:show={toast.show} role="status" aria-live="polite">{toast.msg}</div>
<Activity />
