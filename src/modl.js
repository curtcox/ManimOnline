/** modl parser and SVG editor adapted from curtcox/modl index.html (main, 2026-10-14).
 * Keep the reserved vocabulary, quoting, image nodes and stored positions compatible.
 */
const Modl = (() => {
  const NODE_SIZES = ["tiny", "small", "normal", "big", "bigger", "huge"];
  const NODE_SHAPES = ["none", "circle", "square", "diamond", "triangle", "hex"];
  const EDGE_STYLES = ["solid", "dashed", "dotted", "bold"];

  const COLORS = {
    gray:   "#9aa4b2",
    black:  "#1f2937",
    white:  "#f8fafc",
    red:    "#ef4444",
    orange: "#f97316",
    yellow: "#eab308",
    green:  "#22c55e",
    teal:   "#14b8a6",
    blue:   "#3b82f6",
    purple: "#a855f7",
    pink:   "#ec4899",
    brown:  "#92400e",
  };

  function lexLine(line) {
    const pieces = [];
    const isWS = (c) => /\s/.test(c);
    let i = 0;
    while (i < line.length) {
      const c = line[i];
      if (isWS(c)) {
        let j = i;
        while (j < line.length && isWS(line[j])) j++;
        pieces.push({ type: "ws", raw: line.slice(i, j) });
        i = j;
      } else if (c === "#" && (i === 0 || isWS(line[i - 1]))) {
        pieces.push({ type: "comment", raw: line.slice(i) });
        break;
      } else if (line.startsWith("->", i)) {
        pieces.push({ type: "arrow", raw: "->" });
        i += 2;
      } else {
        const start = i;
        let value = "";
        let quoted = false;
        let canOpen = true;
        while (i < line.length && !isWS(line[i]) && !line.startsWith("->", i)) {
          const q = line[i];
          const close = (canOpen && (q === '"' || q === "'")) ? line.indexOf(q, i + 1) : -1;
          if (close >= 0) {
            value += line.slice(i + 1, close);
            quoted = true;
            i = close + 1;
          } else {
            value += q;
            canOpen = false;
            i++;
          }
        }
        pieces.push({ type: "word", raw: line.slice(start, i), value, quoted });
      }
    }
    return pieces;
  }

  function looksLikeUrlToken(tok) {
    if (!tok) return false;
    if (tok.startsWith("/")) return true;
    if (tok.startsWith("http://") || tok.startsWith("https://")) return true;
    if (tok.startsWith("mailto:")) return true;
    if (tok.startsWith("www.")) return true;
    return false;
  }

  function normalizeUrl(tok) {
    if (!tok) return "";
    if (tok.startsWith("/")) return "https://" + tok.slice(1);
    if (tok.startsWith("www.")) return "https://" + tok;
    return tok;
  }

  function isValidId(id) {
    // Keep it simple; allow common graph ids
    return /^[A-Za-z0-9_:\-]+$/.test(id);
  }

  // Quoted ids may hold any characters, but not nothing
  function idError(word, lineNo) {
    if (word.quoted) return word.value ? "" : `Line ${lineNo+1}: empty node id`;
    return isValidId(word.value) ? "" : `Line ${lineNo+1}: invalid node id "${word.value}"`;
  }

  function parseAttrs(words, kind) {
    // Order: style, color, url, text
    // But each optional, so we detect by reserved sets. Quoted words are never keywords or URLs.
    const tokens = words.map(w => w.quoted ? null : w.value);
    let i = 0;

    let size = "";
    let style = "";
    let color = "";
    let url = "";
    let text = "";

    if (tokens[i]) {
      if (kind === "node") {
        if (NODE_SIZES.includes(tokens[i])) {
          size = tokens[i++];
        }
        if (tokens[i] && NODE_SHAPES.includes(tokens[i])) {
          style = tokens[i++]; // shape
        }
      } else if (kind === "edge") {
        if (NODE_SIZES.includes(tokens[i])) {
          size = tokens[i++];
        }
        if (tokens[i] && EDGE_STYLES.includes(tokens[i])) {
          style = tokens[i++]; // line style
        }
      }
    }

    if (tokens[i] && Object.prototype.hasOwnProperty.call(COLORS, tokens[i])) {
      color = tokens[i++];
    }

    if (tokens[i] && looksLikeUrlToken(tokens[i])) {
      url = normalizeUrl(tokens[i++]);
    }

    const textGiven = i < words.length;
    if (textGiven) {
      text = words.slice(i).map(w => w.value).join(" ");
    }

    return { size, style, color, url, text, textGiven };
  }

  function parseSource(src) {
    const nodes = new Map(); // id -> {id, size, shape, color, url, text}
    const edges = [];        // {from,to, size,style,color,url,text, key}
    let background = "";

    const errors = [];
    const lines = src.split(/\r?\n/);

    function ensureNode(id) {
      if (!nodes.has(id)) {
        nodes.set(id, {
          id,
          size: "normal",
          shape: "circle",
          color: "gray",
          url: "",
          text: "",
          sizeGiven: false,
          shapeGiven: false,
        });
      }
      return nodes.get(id);
    }

    for (let lineNo = 0; lineNo < lines.length; lineNo++) {
      const pieces = lexLine(lines[lineNo]);
      const words = pieces.filter(p => p.type === "word");
      const hasArrow = pieces.some(p => p.type === "arrow");
      if (!words.length && !hasArrow) continue;

      if (!hasArrow && words.length === 1 && !words[0].quoted
          && Object.prototype.hasOwnProperty.call(COLORS, words[0].value)) {
        background = words[0].value;
        continue;
      }

      if (hasArrow) {
        // Edge line (possibly chain)
        const segs = [[]];
        for (const p of pieces) {
          if (p.type === "arrow") segs.push([]);
          else if (p.type === "word") segs[segs.length - 1].push(p);
        }
        const nonEmpty = segs.filter(s => s.length);
        if (nonEmpty.length < 2) {
          errors.push(`Line ${lineNo+1}: malformed edge line`);
          continue;
        }

        // Last segment may contain attrs after the last node id
        const lastWords = nonEmpty[nonEmpty.length - 1];

        const chainIds = [];
        for (let i = 0; i < nonEmpty.length - 1; i++) {
          const err = idError(nonEmpty[i][0], lineNo);
          if (err) {
            errors.push(err);
            continue;
          }
          chainIds.push(nonEmpty[i][0].value);
        }

        const lastErr = idError(lastWords[0], lineNo);
        if (lastErr) {
          errors.push(lastErr);
          continue;
        }
        chainIds.push(lastWords[0].value);

        const attrs = parseAttrs(lastWords.slice(1), "edge");
        // Apply to every edge in chain
        for (let i = 0; i < chainIds.length - 1; i++) {
          const from = chainIds[i];
          const to = chainIds[i + 1];
          ensureNode(from);
          ensureNode(to);

          edges.push({
            from, to,
            size: attrs.size || "normal",
            style: attrs.style || "solid",
            color: attrs.color || "gray",
            url: attrs.url || "",
            text: attrs.text || "",
            key: `${from}->${to}#${edges.length}` // allow duplicates
          });
        }
      } else {
        // Node line
        const err = idError(words[0], lineNo);
        if (err) {
          errors.push(err);
          continue;
        }
        const attrs = parseAttrs(words.slice(1), "node");
        const n = ensureNode(words[0].value);
        if (attrs.size) { n.size = attrs.size; n.sizeGiven = true; }
        if (attrs.style) { n.shape = attrs.style; n.shapeGiven = true; }
        if (attrs.color) n.color = attrs.color;
        if (attrs.url) n.url = attrs.url;
        if (attrs.textGiven) n.text = attrs.text;
        // Without text we keep prior text, so a later bare "id" line won't wipe it; "" clears it explicitly.
      }
    }

    // Prune accidental empty duplicates? We'll just keep as parsed.

    return { nodes, edges, background, errors };
  }


  function copyPositions(input = {}) {
    const result = Object.create(null);
    for (const id of Object.keys(input).sort()) {
      const p = input[id];
      if (Array.isArray(p) && p.length === 2 && p.every(Number.isFinite)) result[id] = p.slice();
    }
    return result;
  }

  // Screen = translation + scale * world. Keep the camera out of saved positions.
  const ZOOM_MIN = 0.001;
  const ZOOM_MAX = 1000;

  function zoomViewport(viewport, factor, centerX, centerY) {
    if (![factor, centerX, centerY].every(Number.isFinite) || factor <= 0) return false;
    const nextScale = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, viewport.scale * factor));
    if (nextScale === viewport.scale) return false;
    const worldX = (centerX - viewport.tx) / viewport.scale;
    const worldY = (centerY - viewport.ty) / viewport.scale;
    const tx = centerX - worldX * nextScale;
    const ty = centerY - worldY * nextScale;
    if (![tx, ty].every(Number.isFinite)) return false;
    Object.assign(viewport, { scale: nextScale, tx, ty });
    return true;
  }

  function create(source, { positions = {}, onChange = () => {}, onFrame = () => {} } = {}) {
    const parsed = parseSource(source);
    if (parsed.errors.length) throw new Error(parsed.errors.join('\n'));
    const $svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    $svg.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
    $svg.setAttribute('width', '800');
    $svg.setAttribute('height', '450');
    $svg.setAttribute('role', 'img');
    $svg.setAttribute('aria-label', 'modl diagram preview');
    const state = { pos: copyPositions(positions) };
    const diagram = parsed;
    let destroyed = false;
    function renderAll() {
      if (destroyed) return;
      ensurePositions(diagram);
      prunePositions(diagram);
      render(diagram);
      onFrame($svg, { ...viewport });
    }
  const NODE_W = 110;
  const NODE_H = 64;

  function nodeScale(size) {
    if (size === "tiny") return 0.25;
    if (size === "small") return 0.5;
    if (size === "big") return 2.0;
    if (size === "bigger") return 4.0;
    if (size === "huge") return 8.0;
    return 1.0; // normal
  }

  function hexToRgb(hex) {
    const h = hex.replace("#", "").trim();
    const v = parseInt(h, 16);
    if (h.length !== 6 || Number.isNaN(v)) return { r: 200, g: 200, b: 200 };
    return { r: (v >> 16) & 255, g: (v >> 8) & 255, b: v & 255 };
  }

  function rgba(hex, a) {
    const { r, g, b } = hexToRgb(hex);
    return `rgba(${r},${g},${b},${a})`;
  }

  function luminance(hex) {
    const { r, g, b } = hexToRgb(hex);
    const srgb = [r, g, b].map(v => {
      const x = v / 255;
      return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4);
    });
    return 0.2126 * srgb[0] + 0.7152 * srgb[1] + 0.0722 * srgb[2];
  }

  function ensurePositions(diagram) {
    const rect = ({ width: 800, height: 450 });
    const W = Math.max(400, rect.width);
    const H = Math.max(300, rect.height);

    const ids = Array.from(diagram.nodes.keys()).sort();
    const missing = ids.filter(id => !state.pos[id] || !Array.isArray(state.pos[id]));

    if (missing.length === 0) return;

    // Place missing nodes around a circle
    const cx = W * 0.5;
    const cy = H * 0.5;
    const r = Math.min(W, H) * 0.32;

    // Count total for stable distribution
    const all = ids;
    for (let i = 0; i < all.length; i++) {
      const id = all[i];
      if (state.pos[id]) continue;
      const ang = (i / Math.max(1, all.length)) * Math.PI * 2;
      const x = cx + Math.cos(ang) * r;
      const y = cy + Math.sin(ang) * r;
      state.pos[id] = [Math.round(x), Math.round(y)];
    }
  }

  let viewport = { scale: 1, tx: 0, ty: 0 };
  let viewportGroup = null;

  function applyViewportTransform() {
    if (!viewportGroup) return;
    viewportGroup.setAttribute("transform", `translate(${viewport.tx} ${viewport.ty}) scale(${viewport.scale})`);
    // Giant blur regions are costly when node dragging rebuilds the SVG.
    $svg.toggleAttribute('data-modl-simple', viewport.scale < 0.1 || viewport.scale > 8);
  }

  function zoomAt(factor, centerX, centerY) {
    if (destroyed || dragging || panning || !zoomViewport(viewport, factor, centerX, centerY)) return;
    applyViewportTransform();
    onFrame($svg, { ...viewport });
  }

  function prunePositions(diagram) {
    const live = new Set(diagram.nodes.keys());
    for (const id of Object.keys(state.pos)) {
      if (!live.has(id)) delete state.pos[id];
    }
  }

  function svgPointFromEvent(evt) {
    const pt = $svg.createSVGPoint();
    pt.x = evt.clientX;
    pt.y = evt.clientY;
    const ctm = $svg.getScreenCTM();
    if (!ctm) return { x: 0, y: 0 };
    const inv = ctm.inverse();
    const p = pt.matrixTransform(inv);
    return { x: p.x, y: p.y };
  }

  function applyEdgeStyle(style, colorName) {
    const color = COLORS[colorName] || COLORS.gray;
    const props = {
      stroke: color,
      "stroke-width": (style === "bold") ? 3.5 : 2.2,
      "stroke-linecap": "round",
      "stroke-linejoin": "round",
      "stroke-dasharray": "",
    };
    if (style === "dashed") props["stroke-dasharray"] = "10 7";
    if (style === "dotted") props["stroke-dasharray"] = "2 7";
    return props;
  }

  function markerIdFor(colorName) {
    return `arrow-${colorName}`;
  }

  function buildMarkers(defsEl) {
    // Create one arrow marker per color name to match edge stroke.
    for (const name of Object.keys(COLORS)) {
      const col = COLORS[name];
      const marker = document.createElementNS("http://www.w3.org/2000/svg", "marker");
      marker.setAttribute("id", markerIdFor(name));
      marker.setAttribute("markerWidth", "10");
      marker.setAttribute("markerHeight", "10");
      marker.setAttribute("refX", "9");
      marker.setAttribute("refY", "5");
      marker.setAttribute("orient", "auto");
      marker.setAttribute("markerUnits", "strokeWidth");

      const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
      path.setAttribute("d", "M 0 0 L 10 5 L 0 10 z");
      path.setAttribute("fill", col);

      marker.appendChild(path);
      defsEl.appendChild(marker);
    }
  }

  function nodeRadius(shape, size) {
    // Rough collision/edge endpoint offset
    const sc = nodeScale(size);
    if (shape === "none") return 4 * sc;
    if (shape === "circle") return Math.max(NODE_W, NODE_H) * 0.32 * sc;
    if (shape === "triangle" || shape === "diamond" || shape === "hex") return Math.max(NODE_W, NODE_H) * 0.36 * sc;
    return Math.max(NODE_W, NODE_H) * 0.34 * sc; // square-ish
  }

  // -----------------------------
  // Image nodes: a node whose URL is a displayable image shows that image
  // -----------------------------
  const IMAGE_EXTENSION = /\.(svg|png|apng|jpe?g|gif|webp|avif|bmp|ico)$/i;
  const images = new Map(); // url -> { status: "loading" | "ok" | "failed", width, height }
  let imageRenderRaf = 0;

  function hasImageExtension(url) {
    try { return IMAGE_EXTENSION.test(new URL(url).pathname); } catch { return false; }
  }

  // URLs without an image extension are probed by loading them as an image; the node switches over if that works.
  // Returns null while the URL isn't known to be an image. width/height are 0 until known (or if the image has
  // no intrinsic size, like an SVG without width/height).
  function nodeImage(url) {
    if (!/^https?:\/\//i.test(url)) return null;
    let entry = images.get(url);
    if (!entry) {
      entry = { status: "loading", width: 0, height: 0 };
      images.set(url, entry);
      const img = new Image();
      img.onload = () => {
        entry.status = "ok";
        entry.width = img.naturalWidth;
        entry.height = img.naturalHeight;
        if (!imageRenderRaf) {
          imageRenderRaf = requestAnimationFrame(() => {
            imageRenderRaf = 0;
            renderAll();
          });
        }
      };
      img.onerror = () => {
        entry.status = "failed";
        if (hasImageExtension(url)) renderAll();
      };
      img.src = url;
    }
    if (entry.status === "ok") return entry;
    if (entry.status === "loading" && hasImageExtension(url)) return entry;
    return null;
  }

  // An explicit size fits the image in that size's box; otherwise it's shown at its natural size
  function imageNodeSize(n, img) {
    if (!n.sizeGiven && img.width && img.height) return { w: img.width, h: img.height };
    const sc = nodeScale(n.size);
    const boxW = NODE_W * sc, boxH = NODE_H * sc;
    if (!img.width || !img.height) return { w: boxW, h: boxH };
    const k = Math.min(boxW / img.width, boxH / img.height);
    return { w: img.width * k, h: img.height * k };
  }

  // Distance from the center of a convex polygon (points relative to that center) to its edge along (ux, uy)
  function rayExit(points, ux, uy) {
    let best = Infinity;
    for (let i = 0; i < points.length; i++) {
      const [px, py] = points[i];
      const [qx, qy] = points[(i + 1) % points.length];
      const ex = qx - px, ey = qy - py;
      const den = ux * ey - uy * ex;
      if (Math.abs(den) < 1e-9) continue;
      const t = (px * ey - py * ex) / den;
      const s = (px * uy - py * ux) / den;
      if (t > 0 && s >= -1e-9 && s <= 1 + 1e-9) best = Math.min(best, t);
    }
    return Number.isFinite(best) ? best : 0;
  }

  function rectPoints(hw, hh) {
    return [[-hw, -hh], [hw, -hh], [hw, hh], [-hw, hh]];
  }

  // Geometry of an image node relative to its center, or null if the node isn't showing an image.
  // An explicitly given shape becomes a frame drawn around the image.
  function imageLayout(n) {
    const img = n.url ? nodeImage(n.url) : null;
    if (!img) return null;
    const { w, h } = imageNodeSize(n, img);
    const sc = n.sizeGiven ? nodeScale(n.size) : 1;
    const shape = (n.shapeGiven && NODE_SHAPES.includes(n.shape) && n.shape !== "none") ? n.shape : "";
    const pad = shape ? Math.max(3, 6 * sc) : 0;
    const W = w / 2 + pad, H = h / 2 + pad;

    let frame = null;
    let outline;
    if (shape === "circle") {
      frame = { r: Math.hypot(W, H) };
    } else if (shape === "square") {
      frame = { points: rectPoints(W, H), rx: Math.min(12 * sc, W, H) };
    } else if (shape === "diamond") {
      frame = { points: [[0, -2 * H], [2 * W, 0], [0, 2 * H], [-2 * W, 0]] };
    } else if (shape === "triangle") {
      frame = { points: [[0, -3 * H], [2 * W, H], [-2 * W, H]] };
    } else if (shape === "hex") {
      const hw = W / 0.55;
      frame = { points: [[-W, -H], [W, -H], [hw, 0], [W, H], [-W, H], [-hw, 0]] };
    }
    if (frame && frame.points) outline = frame.points;
    else if (!frame) outline = rectPoints(w / 2 + 2, h / 2 + 2);

    const bounds = frame && frame.r
      ? { left: -frame.r, top: -frame.r, right: frame.r, bottom: frame.r }
      : {
          left: Math.min(...outline.map(p => p[0])),
          top: Math.min(...outline.map(p => p[1])),
          right: Math.max(...outline.map(p => p[0])),
          bottom: Math.max(...outline.map(p => p[1])),
        };

    return {
      w, h, sc, frame, bounds,
      reach: (ux, uy) => (frame && frame.r) ? frame.r : rayExit(outline, ux, uy),
    };
  }

  // reachA/reachB give the distance from a node's center to its edge in a direction
  function edgeEndpoints(a, b, reachA, reachB) {
    const ax = a[0], ay = a[1];
    const bx = b[0], by = b[1];
    const dx = bx - ax, dy = by - ay;
    const len = Math.hypot(dx, dy) || 1;
    const ux = dx / len, uy = dy / len;

    const ra = reachA(ux, uy);
    const rb = reachB(-ux, -uy);

    const x1 = ax + ux * ra;
    const y1 = ay + uy * ra;
    const x2 = bx - ux * rb;
    const y2 = by - uy * rb;

    return { x1, y1, x2, y2, ux, uy, len };
  }

  function truncateLabel(s, n) {
    if (!s) return "";
    return s.length > n ? s.slice(0, n - 1) + "…" : s;
  }

  function render(diagram) {
    // Setup svg coordinate system in pixels
    const rect = ({ width: 800, height: 450 });
    const W = Math.max(400, rect.width);
    const H = Math.max(300, rect.height);

    $svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
    $svg.style.touchAction = "none";
    $svg.innerHTML = "";

    const defs = document.createElementNS("http://www.w3.org/2000/svg", "defs");
    buildMarkers(defs);
    const detailStyle = document.createElementNS('http://www.w3.org/2000/svg', 'style');
    detailStyle.textContent = 'svg[data-modl-simple] [filter] { filter: none; }';
    defs.appendChild(detailStyle);
    $svg.appendChild(defs);

    // Keep the native dark canvas unless the source chooses a background color.
    const bg = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    bg.setAttribute("x", "0"); bg.setAttribute("y", "0");
    bg.setAttribute("width", W); bg.setAttribute("height", H);
    const background = COLORS[diagram.background] || '#0b0d10';
    bg.setAttribute("fill", background);
    bg.style.cursor = "grab";
    bg.addEventListener("pointerdown", (ev) => startPan(ev));
    $svg.appendChild(bg);

    // Draw edges under nodes
    viewportGroup = document.createElementNS("http://www.w3.org/2000/svg", "g");
    const edgeLayer = document.createElementNS("http://www.w3.org/2000/svg", "g");
    const nodeLayer = document.createElementNS("http://www.w3.org/2000/svg", "g");
    viewportGroup.appendChild(edgeLayer);
    viewportGroup.appendChild(nodeLayer);
    $svg.appendChild(viewportGroup);
    applyViewportTransform();

    const imageLayouts = new Map();
    for (const [id, n] of diagram.nodes.entries()) {
      const layout = imageLayout(n);
      if (layout) imageLayouts.set(id, layout);
    }
    const reachOf = (node) => {
      const layout = imageLayouts.get(node.id);
      return layout ? layout.reach : () => nodeRadius(node.shape, node.size);
    };

    // Edge rendering
    for (const e of diagram.edges) {
      const fromPos = state.pos[e.from];
      const toPos = state.pos[e.to];
      const fromNode = diagram.nodes.get(e.from);
      const toNode = diagram.nodes.get(e.to);
      if (!fromPos || !toPos || !fromNode || !toNode) continue;

      const { x1, y1, x2, y2, ux, uy } = edgeEndpoints(fromPos, toPos, reachOf(fromNode), reachOf(toNode));

      const g = document.createElementNS("http://www.w3.org/2000/svg", "g");

      // Visible stroke
      const p = document.createElementNS("http://www.w3.org/2000/svg", "path");
      p.setAttribute("d", `M ${x1} ${y1} L ${x2} ${y2}`);

      const styleProps = applyEdgeStyle(e.style || "solid", e.color || "gray");
      for (const [k, v] of Object.entries(styleProps)) p.setAttribute(k, v);

      p.setAttribute("fill", "none");
      p.setAttribute("marker-end", `url(#${markerIdFor(e.color || "gray")})`);

      // Hover text
      const title = document.createElementNS("http://www.w3.org/2000/svg", "title");
      const tText = [
        `${e.from} -> ${e.to}`,
        e.text ? `text: ${e.text}` : "",
        e.url ? `link: ${e.url}` : ""
      ].filter(Boolean).join("\n");
      title.textContent = tText;
      p.appendChild(title);

      // Click overlay for edges (fatter invisible stroke)
      const hit = document.createElementNS("http://www.w3.org/2000/svg", "path");
      hit.setAttribute("d", `M ${x1} ${y1} L ${x2} ${y2}`);
      hit.setAttribute("fill", "none");
      hit.setAttribute("stroke", "transparent");
      hit.setAttribute("stroke-width", "14");
      hit.style.cursor = e.url ? "pointer" : "default";
      hit.addEventListener("click", (ev) => {
        ev.stopPropagation();
        if (e.url) safeOpen(e.url);
      });

      // Edge label (optional)
      if (e.text) {
        const mx = (x1 + x2) / 2;
        const my = (y1 + y2) / 2;
        const edgeTextScale = nodeScale(e.size || "normal");
        // Offset label slightly perpendicular
        const px = -uy, py = ux;
        const tx = mx + px * 10;
        const ty = my + py * 10;

        const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
        label.setAttribute("x", tx);
        label.setAttribute("y", ty);
        label.setAttribute("text-anchor", "middle");
        label.setAttribute("dominant-baseline", "middle");
        label.setAttribute("font-family", "system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial");
        label.setAttribute("font-size", String(Math.max(10, Math.round(12 * edgeTextScale))));
        label.setAttribute("fill", "rgba(232,237,243,0.85)");
        label.setAttribute("paint-order", "stroke");
        label.setAttribute("stroke", "rgba(0,0,0,0.6)");
        label.setAttribute("stroke-width", "3");
        label.style.pointerEvents = "none";
        label.textContent = truncateLabel(e.text, 28);
        g.appendChild(label);
      }

      g.appendChild(p);
      g.appendChild(hit);
      edgeLayer.appendChild(g);
    }

    // Node rendering
    for (const [id, n] of diagram.nodes.entries()) {
      const pos = state.pos[id];
      if (!pos) continue;
      const x = pos[0], y = pos[1];

      const sc = nodeScale(n.size);
      const w = NODE_W * sc;
      const h = NODE_H * sc;

      const col = COLORS[n.color] || COLORS.gray;
      const fillCol = rgba(col, 0.18);
      const strokeCol = rgba(col, 0.85);
      const labelCol = luminance(background) < 0.38 ? "rgba(248,250,252,0.95)" : "rgba(15,23,42,0.92)";

      const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
      g.setAttribute("data-node-id", id);
      g.style.cursor = "grab";

      // Hover text
      const title = document.createElementNS("http://www.w3.org/2000/svg", "title");
      const tText = [
        id,
        n.text ? `text: ${n.text}` : "",
        n.url ? `link: ${n.url}` : ""
      ].filter(Boolean).join("\n");
      title.textContent = tText;
      g.appendChild(title);

      const layout = imageLayouts.get(id);
      if (layout) {
        renderImageNode(g, n, id, x, y, layout, fillCol, strokeCol);
        g.addEventListener("pointerdown", (ev) => startDrag(ev, id));
        nodeLayer.appendChild(g);
        continue;
      }

      // Shape
      const shape = (n.shape && NODE_SHAPES.includes(n.shape)) ? n.shape : "circle";
      let el;

      if (shape === "none") {
        el = null;
      } else if (shape === "circle") {
        el = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        el.setAttribute("cx", x);
        el.setAttribute("cy", y);
        el.setAttribute("r", Math.min(w, h) * 0.42);
      } else if (shape === "square") {
        el = document.createElementNS("http://www.w3.org/2000/svg", "rect");
        el.setAttribute("x", x - w / 2);
        el.setAttribute("y", y - h / 2);
        el.setAttribute("width", w);
        el.setAttribute("height", h);
        el.setAttribute("rx", 12 * sc);
      } else if (shape === "diamond") {
        el = document.createElementNS("http://www.w3.org/2000/svg", "polygon");
        const pts = [
          [x, y - h/2],
          [x + w/2, y],
          [x, y + h/2],
          [x - w/2, y],
        ].map(p => p.join(",")).join(" ");
        el.setAttribute("points", pts);
      } else if (shape === "triangle") {
        el = document.createElementNS("http://www.w3.org/2000/svg", "polygon");
        const pts = [
          [x, y - h/2],
          [x + w/2, y + h/2],
          [x - w/2, y + h/2],
        ].map(p => p.join(",")).join(" ");
        el.setAttribute("points", pts);
      } else if (shape === "hex") {
        el = document.createElementNS("http://www.w3.org/2000/svg", "polygon");
        const hw = w/2, hh = h/2;
        const pts = [
          [x - hw*0.55, y - hh],
          [x + hw*0.55, y - hh],
          [x + hw,      y],
          [x + hw*0.55, y + hh],
          [x - hw*0.55, y + hh],
          [x - hw,      y],
        ].map(p => p.join(",")).join(" ");
        el.setAttribute("points", pts);
      } else {
        // fallback
        el = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        el.setAttribute("cx", x);
        el.setAttribute("cy", y);
        el.setAttribute("r", Math.min(w, h) * 0.42);
      }

      if (el) {
        el.setAttribute("fill", fillCol);
        el.setAttribute("stroke", strokeCol);
        el.setAttribute("stroke-width", "2.2");
        el.setAttribute("filter", "drop-shadow(0px 8px 18px rgba(0,0,0,0.45))");
        el.style.pointerEvents = "all";

        // Click to follow link
        if (n.url) {
          el.style.cursor = "pointer";
          el.addEventListener("click", (ev) => {
            // If dragging, ignore click (handled by drag logic)
            if (dragMoved || (dragging && dragging.id === id)) return;
            ev.stopPropagation();
            safeOpen(n.url);
          });
        }

        g.appendChild(el);
      } else {
        // Invisible hit target so "none" nodes remain draggable/clickable.
        const hit = document.createElementNS("http://www.w3.org/2000/svg", "rect");
        hit.setAttribute("x", x - w / 2);
        hit.setAttribute("y", y - h / 2);
        hit.setAttribute("width", w);
        hit.setAttribute("height", h);
        hit.setAttribute("fill", "transparent");
        hit.setAttribute("stroke", "none");
        hit.style.pointerEvents = "all";
        if (n.url) {
          hit.style.cursor = "pointer";
          hit.addEventListener("click", (ev) => {
            if (dragMoved || (dragging && dragging.id === id)) return;
            ev.stopPropagation();
            safeOpen(n.url);
          });
        }
        g.appendChild(hit);
      }

      // Label: prefer node text; fallback to id
      const labelText = n.text ? truncateLabel(n.text, 22) : id;
      const textEl = document.createElementNS("http://www.w3.org/2000/svg", "text");
      textEl.setAttribute("x", x);
      textEl.setAttribute("y", y);
      textEl.setAttribute("text-anchor", "middle");
      textEl.setAttribute("dominant-baseline", "middle");
      textEl.setAttribute("font-family", "system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial");
      textEl.setAttribute("font-size", String(Math.max(10, Math.round(13 * sc))));
      textEl.setAttribute("font-weight", "700");
      textEl.setAttribute("fill", (shape === "none") ? strokeCol : labelCol);
      textEl.style.pointerEvents = "none";
      textEl.textContent = labelText;

      g.appendChild(textEl);

      // Drag handlers
      g.addEventListener("pointerdown", (ev) => startDrag(ev, id));

      nodeLayer.appendChild(g);
    }
  }

  function renderImageNode(g, n, id, x, y, layout, fillCol, strokeCol) {
    const { w, h, sc, frame, bounds } = layout;
    const shadow = "drop-shadow(0px 8px 18px rgba(0,0,0,0.45))";

    if (frame) {
      let el;
      if (frame.r) {
        el = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        el.setAttribute("cx", x);
        el.setAttribute("cy", y);
        el.setAttribute("r", frame.r);
      } else if (frame.rx !== undefined) {
        el = document.createElementNS("http://www.w3.org/2000/svg", "rect");
        el.setAttribute("x", x + bounds.left);
        el.setAttribute("y", y + bounds.top);
        el.setAttribute("width", bounds.right - bounds.left);
        el.setAttribute("height", bounds.bottom - bounds.top);
        el.setAttribute("rx", frame.rx);
      } else {
        el = document.createElementNS("http://www.w3.org/2000/svg", "polygon");
        el.setAttribute("points", frame.points.map(([px, py]) => `${x + px},${y + py}`).join(" "));
      }
      el.setAttribute("fill", fillCol);
      el.setAttribute("stroke", strokeCol);
      el.setAttribute("stroke-width", "2.2");
      el.setAttribute("filter", shadow);
      el.style.pointerEvents = "none";
      g.appendChild(el);
    }

    const image = document.createElementNS("http://www.w3.org/2000/svg", "image");
    image.setAttribute("href", n.url);
    image.setAttribute("x", x - w / 2);
    image.setAttribute("y", y - h / 2);
    image.setAttribute("width", w);
    image.setAttribute("height", h);
    image.setAttribute("preserveAspectRatio", "xMidYMid meet");
    if (!frame) image.setAttribute("filter", shadow);
    image.style.pointerEvents = "none";
    g.appendChild(image);

    // Transparent hit target covering the whole node so it stays draggable/clickable
    const hit = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    hit.setAttribute("x", x + bounds.left);
    hit.setAttribute("y", y + bounds.top);
    hit.setAttribute("width", bounds.right - bounds.left);
    hit.setAttribute("height", bounds.bottom - bounds.top);
    hit.setAttribute("fill", "transparent");
    hit.setAttribute("stroke", "none");
    hit.style.pointerEvents = "all";
    hit.style.cursor = "pointer";
    hit.addEventListener("click", (ev) => {
      if (dragMoved || (dragging && dragging.id === id)) return;
      ev.stopPropagation();
      safeOpen(n.url);
    });
    g.appendChild(hit);

    if (n.text) {
      const fontSize = Math.max(10, Math.round(13 * sc));
      const textEl = document.createElementNS("http://www.w3.org/2000/svg", "text");
      textEl.setAttribute("x", x);
      textEl.setAttribute("y", y + bounds.bottom + 4 + fontSize / 2);
      textEl.setAttribute("text-anchor", "middle");
      textEl.setAttribute("dominant-baseline", "middle");
      textEl.setAttribute("font-family", "system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial");
      textEl.setAttribute("font-size", String(fontSize));
      textEl.setAttribute("font-weight", "700");
      textEl.setAttribute("fill", "rgba(232,237,243,0.92)");
      textEl.setAttribute("paint-order", "stroke");
      textEl.setAttribute("stroke", "rgba(0,0,0,0.6)");
      textEl.setAttribute("stroke-width", "3");
      textEl.style.pointerEvents = "none";
      textEl.textContent = truncateLabel(n.text, 22);
      g.appendChild(textEl);
    }
  }

  function safeOpen(url) {
    if (!/^(https?:|mailto:)/i.test(url)) return;
    try {
      window.open(url, "_blank", "noopener,noreferrer");
    } catch {
      location.href = url;
    }
  }

  let lastNavTime = 0;
  function openUrl(url) {
    if (!url) return;
    const now = performance.now();
    if (now - lastNavTime < 250) return;
    lastNavTime = now;
    safeOpen(url);
  }

  // -----------------------------
  // Dragging
  // -----------------------------
  let dragging = null;
  let dragMoved = false;
  let dragRaf = 0;
  let dragHashTimer = 0;
  let panning = null;

  function startDrag(ev, id) {
    // Only left click / primary pointer
    if (ev.button !== 0) return;
    ev.preventDefault();
    ev.stopPropagation();
    if (dragging || panning) return;
    const p = svgPointFromEvent(ev);
    const cur = state.pos[id];
    dragging = {
      id,
      x: cur[0], y: cur[1],
      startX: p.x, startY: p.y,
      clientX: ev.clientX, clientY: ev.clientY,
      pointerId: ev.pointerId
    };
    dragMoved = false;
    $svg.setPointerCapture(ev.pointerId);
  }

  function moveDrag(ev) {
    if (!dragging || ev.pointerId !== dragging.pointerId) return;
    // Fractional world positions matter: rounding at 1000x causes 1000px jumps.
    // Use deltas to avoid subtracting two large world-space coordinates.
    const p = svgPointFromEvent(ev);
    const nx = dragging.x + (p.x - dragging.startX) / viewport.scale;
    const ny = dragging.y + (p.y - dragging.startY) / viewport.scale;
    if (![nx, ny].every(Number.isFinite)) return;
    const id = dragging.id;
    if (Math.hypot(ev.clientX - dragging.clientX, ev.clientY - dragging.clientY) >= 3) dragMoved = true;
    if (!dragMoved) return;

    state.pos[id] = [nx, ny];

    // Throttle full render to animation frames
    if (!dragRaf) {
      dragRaf = requestAnimationFrame(() => {
        dragRaf = 0;
        renderAll();
      });
    }

    // Debounce hash updates while dragging (still all state in URL)
    clearTimeout(dragHashTimer);
    dragHashTimer = setTimeout(() => onChange(copyPositions(state.pos)), 120);
  }

  function startPan(ev) {
    if (![0, 1].includes(ev.button) || dragging || panning) return;
    ev.preventDefault();
    const p = svgPointFromEvent(ev);
    panning = {
      pointerId: ev.pointerId,
      startX: p.x,
      startY: p.y,
      tx: viewport.tx,
      ty: viewport.ty,
    };
    $svg.classList.add("panning");
    $svg.setPointerCapture(ev.pointerId);
  }

  function movePan(ev) {
    if (!panning || ev.pointerId !== panning.pointerId) return;
    const p = svgPointFromEvent(ev);
    viewport.tx = panning.tx + (p.x - panning.startX);
    viewport.ty = panning.ty + (p.y - panning.startY);
    applyViewportTransform();
    onFrame($svg, { ...viewport });
  }

  function endPan() {
    if (!panning) return;
    const pointerId = panning.pointerId;
    panning = null;
    try { $svg.releasePointerCapture(pointerId); } catch {}
    $svg.classList.remove("panning");
  }

  function endDrag(ev) {
    if (!dragging || ev.pointerId !== dragging.pointerId) return;
    const finishedId = dragging.id;
    const finishedMoved = dragMoved;
    const pointerId = dragging.pointerId;
    dragging = null;
    clearTimeout(dragHashTimer);
    try { $svg.releasePointerCapture(pointerId); } catch {}
    if (finishedMoved) {
      onChange(copyPositions(state.pos));
    } else if (ev.type === 'pointerup') {
      const n = diagram && diagram.nodes ? diagram.nodes.get(finishedId) : null;
      if (n && n.url) openUrl(n.url);
    }
  }

  // Middle drag can pan even when a deeply zoomed node covers the whole canvas.
  $svg.addEventListener('pointerdown', ev => { if (ev.button === 1) startPan(ev); }, true);
  $svg.addEventListener("pointermove", (ev) => {
    moveDrag(ev);
    movePan(ev);
  });
  $svg.addEventListener("pointerup", (ev) => {
    endDrag(ev);
    if (panning?.pointerId === ev.pointerId) endPan();
  });
  $svg.addEventListener("pointercancel", (ev) => {
    endDrag(ev);
    if (panning?.pointerId === ev.pointerId) endPan();
  });
  $svg.addEventListener('lostpointercapture', ev => {
    endDrag(ev);
    if (panning?.pointerId === ev.pointerId) endPan();
  });

  // Touch: one finger drags nodes or pans as above; a second finger pinches (zoom and pan
  // about the fingers' midpoint). touch-action keeps the browser from zooming the page.
  const touches = new Map();
  let pinch = null;
  $svg.style.touchAction = 'none';
  function pinchState() {
    const [a, b] = [...touches.values()];
    return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2, d: Math.hypot(a.x - b.x, a.y - b.y) };
  }
  $svg.addEventListener('pointerdown', ev => {
    if (ev.pointerType !== 'touch' || destroyed) return;
    touches.set(ev.pointerId, svgPointFromEvent(ev));
    // On a phone the letterbox around the drawing is large; let a finger there pan too.
    if (touches.size === 1 && ev.target === $svg) startPan(ev);
    if (touches.size !== 2) return;
    ev.stopPropagation();
    ev.preventDefault();
    if (dragging) endDrag({ pointerId: dragging.pointerId, type: 'pointercancel' });
    if (panning) endPan();
    pinch = { ...pinchState(), viewport: { ...viewport } };
  }, true);
  $svg.addEventListener('pointermove', ev => {
    if (!touches.has(ev.pointerId)) return;
    touches.set(ev.pointerId, svgPointFromEvent(ev));
    if (!pinch || touches.size !== 2 || destroyed) return;
    const now = pinchState();
    const next = { ...pinch.viewport };
    if (pinch.d > 0) zoomViewport(next, now.d / pinch.d, pinch.x, pinch.y);
    next.tx += now.x - pinch.x;
    next.ty += now.y - pinch.y;
    if (![next.tx, next.ty].every(Number.isFinite)) return;
    viewport = next;
    applyViewportTransform();
    onFrame($svg, { ...viewport });
  });
  for (const type of ['pointerup', 'pointercancel']) {
    $svg.addEventListener(type, ev => {
      if (touches.delete(ev.pointerId) && touches.size < 2) pinch = null;
    });
  }


    $svg.addEventListener('wheel', event => {
      event.preventDefault();
      if (!event.deltaY) return;
      const p = svgPointFromEvent(event);
      const unit = event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? 450 : 1;
      zoomAt(Math.exp(Math.max(-2, Math.min(2, -event.deltaY * unit * 0.002))), p.x, p.y);
    }, { passive: false });
    renderAll();
    return {
      svg: $svg,
      positions: () => copyPositions(state.pos),
      viewport: () => ({ ...viewport }),
      zoom: (factor, x = 400, y = 225) => zoomAt(factor, x, y),
      resetView() {
        if (destroyed || dragging || panning) return;
        viewport = { scale: 1, tx: 0, ty: 0 };
        applyViewportTransform();
        onFrame($svg, { ...viewport });
      },
      destroy() {
        destroyed = true;
        cancelAnimationFrame(dragRaf);
        cancelAnimationFrame(imageRenderRaf);
        clearTimeout(dragHashTimer);
        dragging = null;
        panning = null;
        $svg.remove();
      }
    };
  }
  return { parse: parseSource, lexLine, create, copyPositions, zoomViewport, ZOOM_MIN, ZOOM_MAX };
})();
if (typeof module !== 'undefined') module.exports = Modl;
else globalThis.Modl = Modl;
