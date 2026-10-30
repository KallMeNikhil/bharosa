// The home hero's background: pack codes moving through custody.
//
// Four-character groups from the serial alphabet drift along lanes, the way
// packs move from manufacturer to retailer. A checkpoint sweeps across and
// marks what it reads. A few codes exist twice; when either copy is read, both
// flare clay at once, which is the thing Bharosa looks for: one code, two
// places. The pointer is an inspection lens, a click runs a check
// outward from where it lands, and scrolling gives the lanes depth and pace.

import { useEffect, useRef } from "react";

const ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
const FONT = '500 13px "JetBrains Mono Variable", "JetBrains Mono", ui-monospace, monospace';
const LANE_GAP = 21;
const TOKEN_GAP = 12;
const CLONE_PAIRS = 5;
const SCAN_PERIOD = 10;
const SCAN_TRAVEL = 5;
const LENS_RADIUS = 150;
const READ_FADE = 1.8;
const LINK_LIFE = 3.2;
const RING_LIFE = 1.4;
const RING_SPEED = 520;

const MINT: Rgb = [95, 211, 160];
const READ: Rgb = [217, 245, 231];
const CLAY: Rgb = [255, 128, 112];

type Rgb = [number, number, number];

interface Token {
  text: string;
  read: number;
  scramble: number;
  pair: number;
  x: number;
  y: number;
}

interface Lane {
  y: number;
  speed: number;
  shift: number;
  tokens: Token[];
}

interface Ring {
  x: number;
  y: number;
  age: number;
}

const group = () => Array.from({ length: 4 }, () => ALPHABET[(Math.random() * ALPHABET.length) | 0]).join("");
const mix = (a: Rgb, b: Rgb, t: number): Rgb => [
  a[0] + (b[0] - a[0]) * t,
  a[1] + (b[1] - a[1]) * t,
  a[2] + (b[2] - a[2]) * t,
];
const rgba = ([r, g, b]: Rgb, a: number) => `rgba(${r | 0},${g | 0},${b | 0},${a.toFixed(3)})`;

export function CodeField({ className = "" }: { className?: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const context = canvas?.getContext("2d");
    if (!canvas || !context || typeof ResizeObserver === "undefined") return undefined;
    const ctx = context;
    const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;

    let width = 1;
    let height = 1;
    let pitch = 60;
    let tokenWidth = 34;
    let span = 1;
    let lanes: Lane[] = [];
    const links = new Map<number, number>();
    const rings: Ring[] = [];
    const pointer = { x: -9999, y: -9999, sx: -9999, sy: -9999, moved: 0, inside: false };
    let time = 0;
    let last = 0;
    let raf = 0;
    let visible = true;
    let lastScrollY = window.scrollY;
    let scrollBoost = 0;
    let parallax = 0;

    const layout = () => {
      const ratio = Math.min(window.devicePixelRatio || 1, 2);
      width = Math.max(1, canvas.clientWidth);
      height = Math.max(1, canvas.clientHeight);
      canvas.width = Math.round(width * ratio);
      canvas.height = Math.round(height * ratio);
      ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
      ctx.font = FONT;
      tokenWidth = ctx.measureText("MMMM").width;
      pitch = tokenWidth + TOKEN_GAP;

      const perLane = Math.ceil(width / pitch) + 2;
      span = perLane * pitch;
      const laneCount = Math.ceil((height + 120) / LANE_GAP);
      lanes = Array.from({ length: laneCount }, (_, index) => ({
        y: index * LANE_GAP + 10 - 60,
        speed: (12 + Math.random() * 22) * (index % 6 === 4 ? -0.6 : 1),
        shift: Math.random() * span,
        tokens: Array.from({ length: perLane }, () => ({
          text: group(),
          read: 0,
          scramble: 0,
          pair: -1,
          x: 0,
          y: 0,
        })),
      }));

      // Seed the copies: one code placed on two different lanes.
      links.clear();
      for (let pair = 0; pair < CLONE_PAIRS && lanes.length > 4; pair++) {
        const a = lanes[2 + ((pair * 5) % (lanes.length - 3))].tokens;
        const b = lanes[2 + ((pair * 5 + 3 + pair) % (lanes.length - 3))].tokens;
        const first = a[(pair * 3 + 1) % a.length];
        const second = b[(pair * 7 + 4) % b.length];
        if (first === second || first.pair >= 0 || second.pair >= 0) continue;
        const text = group();
        Object.assign(first, { text, pair });
        Object.assign(second, { text, pair });
      }
      draw();
    };

    const twin = (token: Token) => {
      for (const lane of lanes) for (const other of lane.tokens) if (other !== token && other.pair === token.pair) return other;
      return null;
    };

    const read = (token: Token) => {
      if (token.read > 0.6) return;
      token.read = 1;
      if (token.pair >= 0 && !links.has(token.pair)) {
        links.set(token.pair, 0);
        const other = twin(token);
        if (other) other.read = 1;
      }
    };

    const scanX = () => {
      if (reduce) return -1;
      const phase = time % SCAN_PERIOD;
      if (phase > SCAN_TRAVEL) return -1;
      return (phase / SCAN_TRAVEL) * (width + 160) - 80;
    };

    const step = (dt: number) => {
      time += dt;
      pointer.sx += (pointer.x - pointer.sx) * Math.min(1, dt * 10);
      pointer.sy += (pointer.y - pointer.sy) * Math.min(1, dt * 10);
      pointer.moved = Math.max(0, pointer.moved - dt);

      const y = window.scrollY;
      scrollBoost = Math.min(6, scrollBoost * Math.exp(-dt * 2.5) + Math.abs(y - lastScrollY) * 0.04);
      lastScrollY = y;
      parallax = y * 0.35;

      const scan = scanX();
      for (const lane of lanes) {
        lane.shift = (lane.shift + lane.speed * (1 + scrollBoost) * dt + span) % span;
        lane.tokens.forEach((token, index) => {
          const x = ((index * pitch + lane.shift) % span) - pitch;
          // Re-entering at the edge: a fresh pack, unless it is one of a pair.
          if (Math.abs(x - token.x) > pitch * 2 && token.pair < 0) {
            token.text = group();
            token.read = 0;
          }
          token.x = x;
          token.y = lane.y + parallax * 0.25;
          token.read = Math.max(0, token.read - dt / READ_FADE);
          token.scramble = Math.max(0, token.scramble - dt);

          const cx = token.x + tokenWidth / 2;
          if (scan >= 0 && Math.abs(cx - scan) < 10) read(token);

          const dx = cx - pointer.sx;
          const dy = token.y - pointer.sy;
          const distance = Math.hypot(dx, dy);
          if (pointer.inside && distance < LENS_RADIUS && pointer.moved > 0) {
            token.scramble = Math.max(token.scramble, 0.28);
          }
          if (pointer.inside && token.pair >= 0 && distance < 36) read(token);

          for (const ring of rings) {
            const ringDistance = Math.hypot(cx - ring.x, token.y - ring.y);
            if (Math.abs(ringDistance - ring.age * RING_SPEED) < 16) read(token);
          }
        });
      }

      for (let i = rings.length - 1; i >= 0; i--) {
        rings[i].age += dt;
        if (rings[i].age > RING_LIFE) rings.splice(i, 1);
      }
      for (const [pair, age] of links) {
        if (age + dt > LINK_LIFE) links.delete(pair);
        else links.set(pair, age + dt);
      }
    };

    const draw = () => {
      ctx.clearRect(0, 0, width, height);
      ctx.font = FONT;
      ctx.textBaseline = "middle";

      // A broad, slow light the codes are read under.
      const lx = width * (0.78 + 0.07 * Math.sin(time * 0.13));
      const ly = height * (0.4 + 0.12 * Math.sin(time * 0.09 + 1));
      const sigma = Math.max(width, height) * 0.34;
      const glow = ctx.createRadialGradient(lx, ly, 0, lx, ly, sigma * 1.6);
      glow.addColorStop(0, "rgba(15,157,99,0.20)");
      glow.addColorStop(0.5, "rgba(15,157,99,0.06)");
      glow.addColorStop(1, "rgba(15,157,99,0)");
      ctx.fillStyle = glow;
      ctx.fillRect(0, 0, width, height);

      // The checkpoint: a soft, uneven smear of light rather than a ruled line.
      const scan = scanX();
      if (scan >= 0) {
        const slice = 24;
        for (let y = 0; y < height; y += slice) {
          const x = scan + 22 * Math.sin(y * 0.011 + time * 1.4) + 9 * Math.sin(y * 0.037 - time * 2.1);
          const band = ctx.createLinearGradient(x - 160, 0, x + 50, 0);
          band.addColorStop(0, "rgba(95,211,160,0)");
          band.addColorStop(0.62, "rgba(95,211,160,0.07)");
          band.addColorStop(0.82, "rgba(143,227,189,0.12)");
          band.addColorStop(1, "rgba(95,211,160,0)");
          ctx.fillStyle = band;
          ctx.fillRect(x - 160, y, 210, slice);
        }
      }

      const intro = reduce ? 1 : Math.min(1, time / 1.6);
      const narrow = width < 860;
      const quiet = (x: number) => {
        if (narrow) return 0.5;
        const t = Math.min(1, Math.max(0, (x / width - 0.18) / 0.44));
        return 0.28 + 0.72 * t * t * (3 - 2 * t);
      };
      const clearTop = (y: number) => {
        const t = Math.min(1, Math.max(0, (y - 70) / 90));
        return t * t * (3 - 2 * t);
      };
      const lensOn = pointer.inside;

      for (const lane of lanes) {
        if (lane.y + parallax * 0.25 < -20 || lane.y + parallax * 0.25 > height + 20) continue;
        for (const token of lane.tokens) {
          const cx = token.x + tokenWidth / 2;
          const light = Math.exp(-((cx - lx) ** 2 + (token.y - ly) ** 2) / (2 * sigma * sigma));
          const lens = lensOn ? Math.max(0, 1 - Math.hypot(cx - pointer.sx, token.y - pointer.sy) / LENS_RADIUS) : 0;
          const caught = token.pair >= 0 ? links.get(token.pair) : undefined;
          const flare = caught === undefined ? 0 : Math.min(1, caught * 5) * (1 - caught / LINK_LIFE);

          let alpha = (0.06 + 0.46 * light + 0.55 * lens * lens + 0.6 * token.read) * intro;
          let color = mix(MINT, READ, Math.min(1, token.read + lens * 0.5));
          if (flare > 0) {
            color = mix(color, CLAY, flare);
            alpha = Math.max(alpha, 0.85 * flare * intro);
          }
          // The headline sits on the left and the navigation along the top, so
          // everything quietens there.
          alpha *= quiet(cx) * clearTop(token.y);

          // The lens nudges codes aside, as if they were being looked at.
          const push = lens * lens * 7 * Math.sign(token.y - pointer.sy || 1);
          const text =
            token.scramble > 0 && !reduce
              ? Array.from({ length: 4 }, () => ALPHABET[(Math.random() * ALPHABET.length) | 0]).join("")
              : token.text;
          ctx.fillStyle = rgba(color, Math.min(alpha, 0.95));
          ctx.fillText(text, token.x, token.y + push);
        }
      }
    };

    const frame = (now: number) => {
      raf = 0;
      if (!visible || document.hidden) return;
      const dt = last ? Math.min((now - last) / 1000, 0.05) : 1 / 60;
      last = now;
      step(dt);
      draw();
      raf = requestAnimationFrame(frame);
    };

    const wake = () => {
      if (reduce || raf || !visible || document.hidden) return;
      last = 0;
      raf = requestAnimationFrame(frame);
    };

    const locate = (event: PointerEvent) => {
      const rect = canvas.getBoundingClientRect();
      pointer.x = event.clientX - rect.left;
      pointer.y = event.clientY - rect.top;
      pointer.inside = pointer.x >= 0 && pointer.y >= 0 && pointer.x <= rect.width && pointer.y <= rect.height;
      if (pointer.sx < -1000) {
        pointer.sx = pointer.x;
        pointer.sy = pointer.y;
      }
    };
    const onMove = (event: PointerEvent) => {
      locate(event);
      pointer.moved = 0.15;
    };
    const onDown = (event: PointerEvent) => {
      locate(event);
      if (pointer.inside && !reduce) rings.push({ x: pointer.x, y: pointer.y, age: 0 });
    };
    const onVisibility = () => wake();

    const resizeObserver = new ResizeObserver(layout);
    resizeObserver.observe(canvas);
    const intersection = new IntersectionObserver((entries) => {
      visible = entries.some((entry) => entry.isIntersecting);
      if (visible) wake();
    });
    intersection.observe(canvas);
    window.addEventListener("pointermove", onMove, { passive: true });
    window.addEventListener("pointerdown", onDown, { passive: true });
    document.addEventListener("visibilitychange", onVisibility);
    document.fonts?.ready.then(layout, () => undefined);
    layout();
    wake();

    return () => {
      cancelAnimationFrame(raf);
      resizeObserver.disconnect();
      intersection.disconnect();
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerdown", onDown);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, []);

  return <canvas ref={canvasRef} className={`code-field${className ? ` ${className}` : ""}`} aria-hidden="true" />;
}
