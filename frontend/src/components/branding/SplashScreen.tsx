import { useEffect, useRef, useState } from "react";
import pelLogoSrc from "../../assets/pel-logo.png";

export type SplashMode = "disintegrate" | "fade";

interface Props {
  theme: "light" | "dark";
  mode?: SplashMode;
  onFinished: () => void;
}

type Phase = "in" | "disintegrating" | "out";

interface Particle {
  originX: number;
  originY: number;
  targetX: number;
  targetY: number;
  r: number;
  g: number;
  b: number;
  a: number;
  size: number;
}

const MARK_SIZE = 128; // rendered size of the diamond mark, in CSS px
const HOLD_MS = 850; // mark visible + breathing, before it exits
const DISINTEGRATE_MS = 1000; // particles traveling outward + fading (disintegrate mode only)
const OUT_MS = 300; // final scrim fade
const FADE_START_T = 0.5; // particles hold full opacity until 50% through the travel, then fade

function easeOutCubic(t: number) {
  return 1 - Math.pow(1 - t, 3);
}

/**
 * Splash sequence, two interchangeable exit styles:
 *
 *  - "disintegrate": the mark's pixels are sampled onto a canvas and flown
 *    outward toward the screen edges with easing, fading as they travel.
 *  - "fade": the mark simply dissolves in place — quieter, faster.
 *
 * Both hold on the mark + "Change your life" motto first. Reduced-motion
 * always forces the plain fade regardless of `mode`.
 */
export function SplashScreen({ theme, mode = "disintegrate", onFinished }: Props) {
  const isDark = theme === "dark";
  const [phase, setPhase] = useState<Phase>("in");
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const particlesRef = useRef<Particle[]>([]);
  const rafRef = useRef<number | undefined>(undefined);
  const startRef = useRef(0);
  const reducedMotion =
    typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const useParticles = mode === "disintegrate" && !reducedMotion;

  // Phase clock
  useEffect(() => {
    if (!useParticles) {
      const t1 = setTimeout(() => setPhase("out"), HOLD_MS);
      const t2 = setTimeout(onFinished, HOLD_MS + 400);
      return () => {
        clearTimeout(t1);
        clearTimeout(t2);
      };
    }
    const t1 = setTimeout(() => setPhase("disintegrating"), HOLD_MS);
    return () => clearTimeout(t1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (phase !== "out") return;
    const t = setTimeout(onFinished, OUT_MS);
    return () => clearTimeout(t);
  }, [phase, onFinished]);

  // Disintegration: sample the mark's pixels onto an offscreen canvas,
  // then animate each one flying outward on the visible canvas.
  useEffect(() => {
    if (phase !== "disintegrating" || !useParticles) return;
    const canvas = canvasRef.current;
    if (!canvas) return;

    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    canvas.width = vw * dpr;
    canvas.height = vh * dpr;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.scale(dpr, dpr);

    // Redraw the mark (gradient diamond + logo) onto a small offscreen
    // canvas purely so we can read its pixels — same visual as the DOM
    // version rendered during the "in" phase, so the handoff is seamless.
    const off = document.createElement("canvas");
    off.width = MARK_SIZE;
    off.height = MARK_SIZE;
    const octx = off.getContext("2d")!;

    octx.save();
    octx.translate(MARK_SIZE / 2, MARK_SIZE / 2);
    octx.rotate(Math.PI / 4);
    const half = MARK_SIZE * 0.39;
    const r = MARK_SIZE * 0.09;
    const grad = octx.createLinearGradient(-half, -half, half, half);
    grad.addColorStop(0, "#0f88e0");
    grad.addColorStop(1, "#095282");
    octx.fillStyle = grad;
    octx.beginPath();
    octx.moveTo(-half + r, -half);
    octx.arcTo(half, -half, half, half, r);
    octx.arcTo(half, half, -half, half, r);
    octx.arcTo(-half, half, -half, -half, r);
    octx.arcTo(-half, -half, half, -half, r);
    octx.closePath();
    octx.fill();
    octx.restore();

    let cancelled = false;

    const runParticles = () => {
      if (cancelled) return;
      const logoSize = MARK_SIZE * 0.56;
      octx.drawImage(logoImg, (MARK_SIZE - logoSize) / 2, (MARK_SIZE - logoSize) / 2, logoSize, logoSize);

      const imgData = octx.getImageData(0, 0, MARK_SIZE, MARK_SIZE).data;
      const centerX = vw / 2;
      const centerY = vh / 2;
      const stride = 3; // sample every 3rd pixel — enough density at this mark size, keeps particle count sane
      const maxDist = Math.hypot(vw, vh) / 2 + 100; // guarantees particles clear the screen edges
      const particles: Particle[] = [];

      for (let y = 0; y < MARK_SIZE; y += stride) {
        for (let x = 0; x < MARK_SIZE; x += stride) {
          const i = (y * MARK_SIZE + x) * 4;
          const alpha = imgData[i + 3];
          if (alpha < 40) continue;

          const dx0 = x - MARK_SIZE / 2;
          const dy0 = y - MARK_SIZE / 2;
          let angle = dx0 === 0 && dy0 === 0 ? Math.random() * Math.PI * 2 : Math.atan2(dy0, dx0);
          angle += (Math.random() - 0.5) * 0.6; // jitter so it reads as dust, not a mechanical radial burst

          const dist = maxDist * (0.55 + Math.random() * 0.55);
          const originX = centerX + dx0;
          const originY = centerY + dy0;

          particles.push({
            originX,
            originY,
            targetX: originX + Math.cos(angle) * dist,
            targetY: originY + Math.sin(angle) * dist,
            r: imgData[i],
            g: imgData[i + 1],
            b: imgData[i + 2],
            a: alpha / 255,
            size: 2.2 + Math.random() * 2.6,
          });
        }
      }

      particlesRef.current = particles;
      startRef.current = performance.now();
      rafRef.current = requestAnimationFrame(tick);
    };

    const logoImg = new Image();
    logoImg.src = pelLogoSrc;
    if (logoImg.complete) runParticles();
    else logoImg.onload = runParticles;

    function tick(now: number) {
      const t = Math.min((now - startRef.current) / DISINTEGRATE_MS, 1);
      const eased = easeOutCubic(t);
      const alphaMul = t <= FADE_START_T ? 1 : 1 - (t - FADE_START_T) / (1 - FADE_START_T);

      ctx!.clearRect(0, 0, vw, vh);
      for (const p of particlesRef.current) {
        const px = p.originX + (p.targetX - p.originX) * eased;
        const py = p.originY + (p.targetY - p.originY) * eased;
        ctx!.fillStyle = `rgba(${p.r},${p.g},${p.b},${p.a * alphaMul})`;
        ctx!.fillRect(px, py, p.size, p.size);
      }

      if (t < 1) {
        rafRef.current = requestAnimationFrame(tick);
      } else {
        ctx!.clearRect(0, 0, vw, vh);
        setPhase("out");
      }
    }

    return () => {
      cancelled = true;
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [phase, useParticles]);

  return (
    <div
      className={`fixed inset-0 z-50 flex items-center justify-center transition-opacity ${
        phase === "out" ? "opacity-0 duration-300 ease-out" : "opacity-100"
      } ${isDark ? "bg-ink-950" : "bg-porcelain"}`}
    >
      <div
        className={`relative flex items-center justify-center transition-opacity duration-500 ${
          phase === "in" ? "opacity-100" : "opacity-0"
        }`}
      >
        <div
          className={`absolute h-72 w-72 rounded-full blur-3xl animate-glow-breathe ${
            isDark ? "bg-pel-500/40" : "bg-pel-400/25"
          }`}
        />
        <div
          className="relative flex items-center justify-center rounded-xl bg-gradient-to-br from-pel-500 to-pel-800 rotate-45 shadow-lg shadow-pel-900/30 animate-mark-in"
          style={{ width: MARK_SIZE, height: MARK_SIZE }}
        >
          <img
            src={pelLogoSrc}
            alt="PEL"
            className="-rotate-45"
            style={{ width: MARK_SIZE * 0.56, height: MARK_SIZE * 0.56 }}
          />
        </div>
      </div>

      {useParticles && (
        <canvas
          ref={canvasRef}
          className="absolute inset-0 pointer-events-none"
          style={{ width: "100vw", height: "100vh" }}
        />
      )}

      <div
        className={`absolute bottom-16 left-1/2 -translate-x-1/2 text-center transition-opacity duration-300 ${
          phase === "in" ? "opacity-100" : "opacity-0"
        }`}
      >
        <p className={`font-display text-sm tracking-[0.35em] uppercase ${isDark ? "text-ink-200" : "text-ink-700"}`}>
          PEL AI
        </p>
        <p className={`font-display italic text-lg mt-1.5 ${isDark ? "text-pel-200" : "text-pel-700"}`}>
          Change your life
        </p>
        <p
          className={`text-xs font-mono uppercase tracking-wide mt-1.5 ${
            isDark ? "text-ink-400" : "text-ink-500"
          }`}
        >
          Knowledge Assistant
        </p>
      </div>
    </div>
  );
}
