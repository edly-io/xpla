// Multiplayer Flappy Bird UI.
//
// Each player runs a local, deterministic game (own pipes, own physics).
// Position is broadcast ~10 Hz via `game.position`; other players appear
// as semi-transparent ghost birds. On death, the final score is sent
// to the sandbox which updates `best_score` and `top_scores`.

const CANVAS_W = 480;
const CANVAS_H = 640;
const BIRD_X = 120;
const BIRD_R = 14;
const GRAVITY = 1400;
const FLAP_VY = -420;
const PIPE_W = 64;
const PIPE_GAP = 160;
const PIPE_SPACING = 220;
const PIPE_SPEED = 180;
const GHOST_TTL_MS = 2000;
const BROADCAST_MS = 100;

export function setup(activity) {
  const root = activity.element;
  const permission = activity.permission;
  const canPlay = permission === "play" || permission === "edit";

  root.innerHTML = `
    <style>
      .fb-wrap { display: flex; gap: 16px; font-family: system-ui, sans-serif; }
      .fb-stage { position: relative; }
      .fb-canvas { display: block; background: #70c5ce; border-radius: 8px; cursor: pointer; }
      .fb-overlay {
        position: absolute; inset: 0;
        display: flex; align-items: center; justify-content: center;
        color: #fff; text-align: center; pointer-events: none;
        text-shadow: 0 2px 4px rgba(0,0,0,0.5);
      }
      .fb-overlay-box { background: rgba(0,0,0,0.45); padding: 16px 24px; border-radius: 8px; pointer-events: auto; }
      .fb-overlay-box h2 { margin: 0 0 8px; font-size: 22px; }
      .fb-overlay-box p { margin: 4px 0; }
      .fb-overlay-box button { margin-top: 10px; padding: 6px 14px; font-size: 14px; cursor: pointer; }
      .fb-panel {
        min-width: 200px; padding: 12px 16px;
        background: #f6f6f8; border-radius: 8px; font-size: 14px;
      }
      .fb-panel h3 { margin: 0 0 8px; font-size: 15px; }
      .fb-panel ol { margin: 0; padding-left: 22px; }
      .fb-panel li { margin: 2px 0; }
      .fb-panel .best { font-size: 24px; font-weight: bold; color: #2a6; }
    </style>
    <div class="fb-wrap">
      <div class="fb-stage">
        <canvas class="fb-canvas" width="${CANVAS_W}" height="${CANVAS_H}"></canvas>
        <div class="fb-overlay"><div class="fb-overlay-box" data-role="overlay"></div></div>
      </div>
      <div class="fb-panel">
        <h3>Your best</h3>
        <div class="best" data-role="best">0</div>
        <h3 style="margin-top: 16px;">Top 10</h3>
        <ol data-role="top"></ol>
      </div>
    </div>
  `;

  const canvas = root.querySelector(".fb-canvas");
  const ctx = canvas.getContext("2d");
  const overlayBox = root.querySelector('[data-role="overlay"]');
  const bestEl = root.querySelector('[data-role="best"]');
  const topEl = root.querySelector('[data-role="top"]');

  const ghosts = new Map();
  let rngState = 0;
  let game = newGame();
  let lastBroadcast = 0;
  let lastFrame = performance.now();

  function dailySeed() {
    const d = new Date();
    const dayNum = Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()) / 86400000;
    let h = Math.floor(dayNum) >>> 0;
    h = Math.imul(h ^ (h >>> 16), 0x85ebca6b) >>> 0;
    h = Math.imul(h ^ (h >>> 13), 0xc2b2ae35) >>> 0;
    return (h ^ (h >>> 16)) >>> 0;
  }

  function nextRandom() {
    rngState = (rngState + 0x6d2b79f5) >>> 0;
    let t = rngState;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  }

  function newGame() {
    rngState = dailySeed();
    return {
      state: "idle",
      bird: { y: CANVAS_H / 2, vy: 0 },
      pipes: seedPipes(),
      score: 0,
      scrollX: 0,
    };
  }

  function seedPipes() {
    const pipes = [];
    let x = CANVAS_W + 100;
    for (let i = 0; i < 6; i++) {
      pipes.push({ x, gapY: randomGapY() });
      x += PIPE_SPACING;
    }
    return pipes;
  }

  function randomGapY() {
    const margin = 60;
    return margin + nextRandom() * (CANVAS_H - 2 * margin - PIPE_GAP);
  }

  function flap() {
    if (!canPlay) return;
    if (game.state === "idle") game.state = "playing";
    if (game.state === "playing") game.bird.vy = FLAP_VY;
    else if (game.state === "dead") {
      game = newGame();
    }
  }

  canvas.addEventListener("mousedown", flap);
  canvas.addEventListener("touchstart", (e) => { e.preventDefault(); flap(); }, { passive: false });
  function onKey(e) {
    if (e.code === "Space" || e.code === "ArrowUp") {
      e.preventDefault();
      flap();
    }
  }
  window.addEventListener("keydown", onKey);

  function step(dt) {
    if (game.state !== "playing") return;
    const b = game.bird;
    b.vy += GRAVITY * dt;
    b.y += b.vy * dt;
    game.scrollX += PIPE_SPEED * dt;

    for (const p of game.pipes) p.x -= PIPE_SPEED * dt;
    while (game.pipes.length && game.pipes[0].x < -PIPE_W) {
      game.pipes.shift();
      const lastX = game.pipes[game.pipes.length - 1].x;
      game.pipes.push({ x: lastX + PIPE_SPACING, gapY: randomGapY() });
    }

    for (const p of game.pipes) {
      if (!p.passed && p.x + PIPE_W < BIRD_X - BIRD_R) {
        p.passed = true;
        game.score += 1;
      }
    }

    if (b.y + BIRD_R > CANVAS_H || b.y - BIRD_R < 0) die();
    else if (collides()) die();
  }

  function collides() {
    const b = game.bird;
    for (const p of game.pipes) {
      if (p.x + PIPE_W < BIRD_X - BIRD_R) continue;
      if (p.x > BIRD_X + BIRD_R) break;
      if (b.y - BIRD_R < p.gapY || b.y + BIRD_R > p.gapY + PIPE_GAP) return true;
    }
    return false;
  }

  function die() {
    if (game.state !== "playing") return;
    game.state = "dead";
    activity.sendAction("game.over", { score: game.score });
    try {
      activity.sendAction("game.position", { x: BIRD_X, y: game.bird.y, alive: false });
    } catch (_) {}
  }

  function render() {
    ctx.fillStyle = "#70c5ce";
    ctx.fillRect(0, 0, CANVAS_W, CANVAS_H);

    ctx.fillStyle = "#5ab030";
    for (const p of game.pipes) {
      ctx.fillRect(p.x, 0, PIPE_W, p.gapY);
      ctx.fillRect(p.x, p.gapY + PIPE_GAP, PIPE_W, CANVAS_H - p.gapY - PIPE_GAP);
    }

    const now = performance.now();
    for (const [user, g] of ghosts) {
      if (now - g.lastSeen > GHOST_TTL_MS) {
        ghosts.delete(user);
        continue;
      }
      ctx.globalAlpha = g.alive ? 0.45 : 0.2;
      ctx.fillStyle = "#ffcc33";
      ctx.beginPath();
      ctx.arc(g.x, g.y, BIRD_R, 0, Math.PI * 2);
      ctx.fill();
      ctx.globalAlpha = 1;
      ctx.fillStyle = "rgba(0,0,0,0.7)";
      ctx.font = "11px system-ui, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(user, g.x, g.y - BIRD_R - 4);
    }

    ctx.fillStyle = "#ffeb3b";
    ctx.strokeStyle = "#333";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(BIRD_X, game.bird.y, BIRD_R, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();

    ctx.fillStyle = "#fff";
    ctx.strokeStyle = "#000";
    ctx.lineWidth = 3;
    ctx.font = "bold 36px system-ui, sans-serif";
    ctx.textAlign = "center";
    ctx.strokeText(String(game.score), CANVAS_W / 2, 60);
    ctx.fillText(String(game.score), CANVAS_W / 2, 60);
  }

  function updateOverlay() {
    if (!canPlay) {
      overlayBox.innerHTML = `<h2>View only</h2><p>Leaderboard shown on the right.</p>`;
      overlayBox.style.display = "block";
      return;
    }
    if (game.state === "idle") {
      overlayBox.innerHTML = `<h2>Flappy Bird</h2><p>Click or press Space to flap.</p>`;
      overlayBox.style.display = "block";
    } else if (game.state === "dead") {
      overlayBox.innerHTML = `<h2>Game over</h2><p>Score: ${game.score}</p><button data-role="restart">Play again</button>`;
      overlayBox.style.display = "block";
      const btn = overlayBox.querySelector('[data-role="restart"]');
      if (btn) btn.addEventListener("click", (e) => { e.stopPropagation(); flap(); });
    } else {
      overlayBox.style.display = "none";
    }
  }

  let prevState = null;
  function loop(now) {
    const dt = Math.min(0.05, (now - lastFrame) / 1000);
    lastFrame = now;
    step(dt);
    render();

    if (game.state !== prevState) {
      prevState = game.state;
      updateOverlay();
    }

    if (canPlay && game.state === "playing" && now - lastBroadcast > BROADCAST_MS) {
      lastBroadcast = now;
      activity.sendAction("game.position", {
        x: BIRD_X,
        y: game.bird.y,
        alive: true,
      });
    }

    requestAnimationFrame(loop);
  }

  function renderPanels() {
    const best = activity.state.best_score || 0;
    bestEl.textContent = String(best);
    const scores = activity.state.top_scores || [];
    topEl.innerHTML = scores
      .map((s) => `<li>${escapeHtml(s.user)} — <strong>${s.score | 0}</strong></li>`)
      .join("");
  }

  activity.onEvent = (name, value) => {
    if (name === "player.position") {
      ghosts.set(value.user, {
        x: value.x,
        y: value.y,
        alive: value.alive,
        lastSeen: performance.now(),
      });
    } else if (name === "fields.change.best_score") {
      activity.state.best_score = value;
      renderPanels();
    } else if (name === "fields.change.top_scores") {
      activity.state.top_scores = value;
      renderPanels();
    }
  };

  renderPanels();
  updateOverlay();
  if (!canPlay) {
    const stage = root.querySelector(".fb-stage");
    stage.style.display = "none";
  } else {
    requestAnimationFrame(loop);
  }
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = String(str);
  return div.innerHTML;
}
