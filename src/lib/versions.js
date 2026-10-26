// macOS releases, newest first; the "macOS Version" grouping follows this order
export const VERSIONS = [
  ['27', 'macOS Golden Gate', '27'], ['26', 'macOS Tahoe', '26'], ['15', 'macOS Sequoia', '15'],
  ['14', 'macOS Sonoma', '14'], ['13', 'macOS Ventura', '13'], ['12', 'macOS Monterey', '12'],
  ['11', 'macOS Big Sur', '11'], ['10.15', 'macOS Catalina', '10.15'], ['10.14', 'macOS Mojave', '10.14'],
  ['10.13', 'macOS High Sierra', '10.13'], ['10.12', 'macOS Sierra', '10.12'], ['10.11', 'OS X El Capitan', '10.11'],
  ['10.10', 'OS X Yosemite', '10.10'], ['10.9', 'OS X Mavericks', '10.9'], ['10.8', 'OS X Mountain Lion', '10.8'],
  ['10.7', 'Mac OS X Lion', '10.7'], ['10.6', 'Mac OS X Snow Leopard', '10.6'], ['10.5', 'Mac OS X Leopard', '10.5'],
  ['10.4', 'Mac OS X Tiger', '10.4'], ['10.3', 'Mac OS X Panther', '10.3'], ['10.2', 'Mac OS X Jaguar', '10.2'],
  ['10.0', 'Mac OS X Cheetah & Puma', '10.0–10.1'], ['9', 'Mac OS 9', ''], ['8.5', 'Mac OS 8.5–9', ''], ['8', 'Mac OS 8', ''],
  ['7.5', 'System 7.5', ''], ['classic', 'Classic Mac OS', ''], ['other', 'Other', ''],
];
export const VLABEL = Object.fromEntries(VERSIONS.map(([k, n, num]) => [k, num ? `${n} ${num}` : n]));
export const VSHORT = Object.fromEntries(VERSIONS.map(([k, n]) => [k, n.replace(/^(macOS|OS X|Mac OS X) /, '')]));
export const VORDER = Object.fromEntries(VERSIONS.map(([k], i) => [k, i]));

// Archive items are filed by release
export const section = d => (d.c === 'archive' ? VSHORT[d.s] : d.s);

// Desktop patterns are tiny tiles; scale the smallest up so their pixels read
export const patSize = d => (d.w <= 16 ? d.w * 6 : d.w <= 64 ? d.w * 2 : d.w <= 128 ? d.w : d.w / 2);

export const mb = n => (n >= 1e9 ? (n / 1e9).toFixed(1) + ' GB' : Math.max(1, Math.round(n / 1e6)) + ' MB');
