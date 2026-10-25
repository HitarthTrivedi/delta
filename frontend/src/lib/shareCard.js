// Share cards for earned badges, drawn on a canvas (no extra library).
// The image leaves Delta, so it uses one fixed light palette whatever the
// viewer's theme, and carries only what the learner chooses to share.

const PAPER = '#f6f1e7';
const INK = '#1c1a17';
const INK_SOFT = '#5b554c';
const REWARD = '#b7791f';

function wrap(g, text, maxWidth) {
  const words = String(text).split(' ');
  const lines = [];
  let line = '';
  for (const w of words) {
    const next = line ? `${line} ${w}` : w;
    if (g.measureText(next).width > maxWidth && line) {
      lines.push(line);
      line = w;
    } else {
      line = next;
    }
  }
  if (line) lines.push(line);
  return lines;
}

function star(g, cx, cy, outer, inner) {
  g.beginPath();
  for (let i = 0; i < 10; i += 1) {
    const r = i % 2 ? inner : outer;
    const a = (Math.PI / 5) * i - Math.PI / 2;
    g[i ? 'lineTo' : 'moveTo'](cx + r * Math.cos(a), cy + r * Math.sin(a));
  }
  g.closePath();
}

export function badgeCardBlob({ title, description, tier, maxTier, name, earnedAt }) {
  const c = document.createElement('canvas');
  c.width = 1200;
  c.height = 630;
  const g = c.getContext('2d');
  g.fillStyle = PAPER;
  g.fillRect(0, 0, c.width, c.height);

  // Medal
  g.beginPath(); g.arc(270, 315, 165, 0, Math.PI * 2); g.fillStyle = REWARD; g.fill();
  g.beginPath(); g.arc(270, 315, 135, 0, Math.PI * 2); g.fillStyle = '#fbf7ef'; g.fill();
  star(g, 270, 305, 78, 34); g.fillStyle = REWARD; g.fill();
  for (let i = 0; i < maxTier; i += 1) {
    g.beginPath();
    g.arc(270 + (i - (maxTier - 1) / 2) * 30, 410, 9, 0, Math.PI * 2);
    g.fillStyle = i < tier ? REWARD : '#e3dccd';
    g.fill();
  }

  // Text
  const x = 500;
  g.fillStyle = INK_SOFT;
  g.font = '600 26px system-ui, -apple-system, Segoe UI, sans-serif';
  g.fillText('BADGE EARNED ON DELTA', x, 190);
  g.fillStyle = INK;
  g.font = '600 68px Georgia, serif';
  const titleLines = wrap(g, title, 640).slice(0, 2);
  titleLines.forEach((l, i) => g.fillText(l, x, 270 + i * 76));
  g.fillStyle = INK_SOFT;
  g.font = '30px system-ui, -apple-system, Segoe UI, sans-serif';
  const y = 270 + titleLines.length * 76 + 10;
  wrap(g, description, 640).slice(0, 2).forEach((l, i) => g.fillText(l, x, y + i * 40));
  const when = earnedAt ? new Date(earnedAt).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' }) : '';
  g.fillStyle = INK;
  g.font = '600 28px system-ui, -apple-system, Segoe UI, sans-serif';
  g.fillText([name, when].filter(Boolean).join(' · '), x, 530);

  return new Promise((resolve) => c.toBlob(resolve, 'image/png'));
}

/** Opens the phone's share sheet (WhatsApp, LinkedIn...) or downloads the image. */
export async function shareBadge(badge, name) {
  const blob = await badgeCardBlob({
    title: badge.title, description: badge.description, tier: badge.tier, maxTier: badge.max_tier,
    name, earnedAt: badge.earned_at,
  });
  const file = new File([blob], `delta-badge-${badge.key}.png`, { type: 'image/png' });
  const text = `I earned the "${badge.title}" badge on Delta: ${badge.description}.`;
  if (navigator.canShare && navigator.canShare({ files: [file] })) {
    try {
      await navigator.share({ files: [file], text });
      return 'shared';
    } catch (err) {
      if (err?.name === 'AbortError') return 'cancelled';
    }
  }
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = file.name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  return 'downloaded';
}
