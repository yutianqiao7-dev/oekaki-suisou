// おえかき水槽ウィジェット（Scriptable 用）
// 更新されるたびに魚の位置・向きが変わり、時間帯で水の色が変わる。
// ウィジェットをタップすると、動く水槽ページが開く。

const TANK_URL = "https://claude.ai/artifact/1equDzpV4NgWY1UM6vbo5M"

const family = config.widgetFamily || "large"
const SIZES = { small: [338, 338], medium: [720, 338], large: [720, 758], extraLarge: [1520, 758] }
const [W, H] = SIZES[family] || SIZES.large

const rand = (a, b) => a + Math.random() * (b - a)
const pick = arr => arr[Math.floor(Math.random() * arr.length)]

// 時間帯ごとの水の色（上・下）
function waterColors() {
  const h = new Date().getHours()
  if (h >= 5 && h < 10) return ["#7cc8d8", "#1d6c94"]   // 朝
  if (h >= 10 && h < 16) return ["#3aa6cc", "#0d4a7a"]  // 昼
  if (h >= 16 && h < 19) return ["#e39a6e", "#2a4f7a"]  // 夕方
  return ["#163a63", "#040f22"]                          // 夜
}

function drawFish(ctx, cx, cy, L, body, accent, face) {
  const p = (x, y) => new Point(cx + x * L * face, cy + y * L)
  const path = pts => { const b = new Path(); b.addLines(pts); b.closeSubpath(); return b }
  const outline = new Color("#1e1e32")
  ctx.setLineWidth(Math.max(2, L * 0.025))
  ctx.setStrokeColor(outline)
  // しっぽ
  const tail = path([p(-0.4, 0), p(-0.78, -0.3), p(-0.68, 0), p(-0.78, 0.3)])
  ctx.setFillColor(new Color(accent)); ctx.addPath(tail); ctx.fillPath(); ctx.addPath(tail); ctx.strokePath()
  // 背びれ
  const fin = path([p(-0.12, -0.22), p(0.05, -0.42), p(0.15, -0.21)])
  ctx.addPath(fin); ctx.fillPath(); ctx.addPath(fin); ctx.strokePath()
  // 胴体
  const bodyRect = new Rect(cx - L * 0.5, cy - L * 0.27, L, L * 0.54)
  ctx.setFillColor(new Color(body)); ctx.fillEllipse(bodyRect); ctx.strokeEllipse(bodyRect)
  // しま
  ctx.setFillColor(new Color(accent))
  for (const x of [-0.12, 0.08]) {
    ctx.fillRect(new Rect(cx + x * L * face - L * 0.03, cy - L * 0.2, L * 0.06, L * 0.4))
  }
  // 目
  const ex = cx + 0.3 * L * face, ey = cy - 0.05 * L, er = L * 0.07
  ctx.setFillColor(Color.white()); ctx.fillEllipse(new Rect(ex - er, ey - er, er * 2, er * 2))
  ctx.setFillColor(new Color("#141420"))
  ctx.fillEllipse(new Rect(ex - er * 0.45 + er * 0.2 * face, ey - er * 0.45, er * 0.9, er * 0.9))
}

function build() {
  const ctx = new DrawContext()
  ctx.size = new Size(W, H)
  ctx.opaque = true
  ctx.respectScreenScale = true

  // 水のグラデーション（帯を重ねて近似）
  const [top, bottom] = waterColors()
  const c1 = new Color(top), c2 = new Color(bottom)
  const bands = 40
  for (let i = 0; i < bands; i++) {
    const t = i / (bands - 1)
    const mix = (a, b) => Math.round((a + (b - a) * t) * 255)
    const hex = [mix(c1.red, c2.red), mix(c1.green, c2.green), mix(c1.blue, c2.blue)]
      .map(v => v.toString(16).padStart(2, "0")).join("")
    ctx.setFillColor(new Color("#" + hex))
    ctx.fillRect(new Rect(0, (H * i) / bands, W, H / bands + 1))
  }

  // 光の筋
  for (let i = 0; i < 3; i++) {
    const x0 = W * (0.15 + i * 0.32)
    const ray = new Path()
    ray.addLines([new Point(x0, 0), new Point(x0 + 30, 0), new Point(x0 + W * 0.22, H), new Point(x0 + W * 0.08, H)])
    ray.closeSubpath()
    ctx.setFillColor(new Color("#ffffe6", 0.07)); ctx.addPath(ray); ctx.fillPath()
  }

  // 砂
  const sandTop = H * 0.84
  ctx.setFillColor(new Color("#d6be8c"))
  const sand = new Path(); const pts = [new Point(0, H)]
  for (let x = 0; x <= W; x += 20) pts.push(new Point(x, sandTop + 8 * Math.sin(x / 50)))
  pts.push(new Point(W, H)); sand.addLines(pts); sand.closeSubpath()
  ctx.addPath(sand); ctx.fillPath()
  ctx.setFillColor(new Color("#5c6270")); ctx.fillEllipse(new Rect(-W * 0.05, sandTop - H * 0.03, W * 0.35, H * 0.12))
  ctx.setFillColor(new Color("#505666")); ctx.fillEllipse(new Rect(W * 0.7, sandTop - H * 0.05, W * 0.38, H * 0.16))

  // 水草
  const weedCount = Math.round(W / 70)
  for (let i = 0; i < weedCount; i++) {
    const x = (i + rand(0.2, 0.8)) * W / weedCount, h = H * rand(0.25, 0.45), lean = rand(-25, 25)
    const weed = new Path(); const L = [], R = []
    for (let k = 0; k <= 10; k++) {
      const u = k / 10, cx = x + lean * u * u, cy = sandTop + 10 - h * u, hw = 7 * (1 - u) + 1
      L.push(new Point(cx - hw, cy)); R.push(new Point(cx + hw, cy))
    }
    weed.addLines(L.concat(R.reverse())); weed.closeSubpath()
    ctx.setFillColor(new Color(pick(["#2c9650", "#46af5a", "#1e785a"]))); ctx.addPath(weed); ctx.fillPath()
  }

  // 魚（毎回ランダム配置）
  const palette = [["#ff8a5c", "#ffd84d"], ["#5cc8ff", "#2f6fe0"], ["#ff6fa8", "#ffe0ef"],
                   ["#ffd84d", "#f07a2a"], ["#9b6bff", "#5be0c4"]]
  const count = family === "small" ? 3 : 5
  const base = Math.min(W, H) * (family === "small" ? 0.32 : 0.24)
  const used = palette.slice().sort(() => Math.random() - 0.5).slice(0, count)
  used.forEach(([b, a], i) => {
    const L = base * rand(0.75, 1.1)
    const x = rand(L * 0.8, W - L * 0.8)
    const y = H * 0.12 + (H * 0.62) * ((i + rand(0.2, 0.8)) / count)
    drawFish(ctx, x, y, L, b, a, Math.random() < 0.5 ? -1 : 1)
  })

  // 泡
  ctx.setStrokeColor(new Color("#dcf5ff", 0.8)); ctx.setLineWidth(2)
  const bx = W * rand(0.3, 0.7)
  for (let i = 0; i < 9; i++) {
    const r = rand(4, 10), y = sandTop - (sandTop * i) / 9 - rand(0, 20)
    ctx.strokeEllipse(new Rect(bx + rand(-12, 12) - r, y - r, r * 2, r * 2))
  }
  return ctx.getImage()
}

const widget = new ListWidget()
widget.backgroundImage = build()
widget.url = TANK_URL
// 15分ごとに描き直しを依頼（実際の更新タイミングは iOS が決める）
widget.refreshAfterDate = new Date(Date.now() + 15 * 60 * 1000)

if (config.runsInWidget) {
  Script.setWidget(widget)
} else {
  await widget.presentLarge()
}
Script.complete()
