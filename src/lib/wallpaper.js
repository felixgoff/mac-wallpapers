// What Set as Wallpaper (desktop app) saves: Apple's own HEIC on a Mac, so dynamic wallpapers keep following the
// time of day; never HEIC elsewhere, as Windows and Linux desktops can't show it.
// 'heic' and 'jpeg' are taken out of Apple's file in the page; anything else is the URL of a picture to download.
export function wallpaperSource(d, mac) {
  const src = d.full ?? d.url;
  if (mac && d.how === 'zip') return 'heic';
  return mac || !/\.(heic|zip)$/i.test(src) ? src : 'jpeg';
}
