<script>
  // Everything being downloaded, decoded or packed right now: what it's doing, how far along, and a way to stop it
  import { jobs } from './downloads.svelte.js';
  const active = $derived([...jobs.values()].filter(j => j.state === 'loading'));
</script>

<div class="activity" role="region" aria-label="Activity">
  {#each active as j (j)}
    <div class="act">
      <div class="act-text">
        <b>{j.title}</b>
        <span aria-live="polite">{j.step}</span>
        <div class="act-bar" class:indeterminate={j.p == null} role="progressbar" aria-label={j.title}
          aria-valuemin="0" aria-valuemax="100" aria-valuenow={j.p == null ? null : Math.round(j.p * 100)}>
          <i style:width={j.p == null ? null : `${j.p * 100}%`}></i>
        </div>
      </div>
      <button class="act-x" title="Cancel" aria-label={`Cancel ${j.title}`} onclick={() => j.ctrl.abort()}>
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="m5 5 6 6M11 5l-6 6"/></svg>
      </button>
    </div>
  {/each}
</div>
