/**
 * Manim SVG Renderer for ManimOnline
 * Converts Manim scene output to SVG
 */

const ManimRenderer = {
  // SVG namespace
  SVG_NS: 'http://www.w3.org/2000/svg',

  // Default canvas size (Manim uses 14.2 x 8 unit coordinate system)
  CANVAS_WIDTH: 800,
  CANVAS_HEIGHT: 450,
  UNIT_SCALE: 50, // pixels per Manim unit

  /**
   * Render a scene to SVG
   * @param {Object} sceneData - The scene data from Manim-lite
   * @returns {SVGElement}
   */
  render(sceneData, mathGlyphs) {
    const camera = sceneData.camera || {};
    const width = camera.pixel_width ?? this.CANVAS_WIDTH;
    const height = camera.pixel_height ?? this.CANVAS_HEIGHT;
    const frameHeight = camera.frame_height ?? 8;
    const frameWidth = camera.frame_width ?? frameHeight * width / height;
    const center = camera.frame_center ?? [0, 0, 0];
    if (!Array.isArray(center) || center.length !== 3 || !center.every(Number.isFinite) || center[2] !== 0) throw new Error('Invalid preview camera center');
    const background = camera.background_color ?? '#000000';
    if (![width, height].every(n => Number.isInteger(n) && n > 0 && n <= 4096) ||
        ![frameWidth, frameHeight].every(n => Number.isFinite(n) && n > 0) ||
        !/^#[0-9a-f]{6}$/i.test(background)) throw new Error('Invalid preview camera settings');
    const svg = document.createElementNS(this.SVG_NS, 'svg');
    svg.setAttribute('width', width);
    svg.setAttribute('height', height);
    svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
    svg.style.backgroundColor = background;

    // Explicit geometry keeps the background in SVG and rasterized exports.
    const backdrop = document.createElementNS(this.SVG_NS, 'rect');
    backdrop.setAttribute('width', width);
    backdrop.setAttribute('height', height);
    backdrop.setAttribute('fill', background);
    backdrop.setAttribute('data-manim-background', 'true');
    svg.appendChild(backdrop);
    const mainGroup = document.createElementNS(this.SVG_NS, 'g');
    mainGroup.setAttribute('transform', `translate(${width / 2}, ${height / 2}) scale(${width / frameWidth / this.UNIT_SCALE}, ${-height / frameHeight / this.UNIT_SCALE})`);
    if (center[0] || center[1]) mainGroup.setAttribute('transform', mainGroup.getAttribute('transform') + ` translate(${-center[0] * this.UNIT_SCALE}, ${-center[1] * this.UNIT_SCALE})`);
    svg.appendChild(mainGroup);
    // Community strokes are stroke_width * 0.01 scene units, so they thicken
    // on screen as a moving camera zooms in (Cairo user-space line widths).
    this._strokeUnit = 0.01 * this.UNIT_SCALE;

    // Sort drawable leaves globally, keeping each leaf's ancestor transforms.
    // A child can sit behind or in front of a shape outside its VGroup.
    const layers = [];
    const collect = (mobject, ancestors = [], views = []) => {
      // Camera displays (ZoomedScene) never show their own family.
      if (Number.isInteger(mobject.camera_view)) views = [...views, mobject.camera_view];
      if (mobject.type === 'vgroup') {
        for (const child of mobject.children || []) collect(child, [...ancestors, mobject], views);
      } else {
        let branch = { ...mobject, children: [] };
        for (let i = ancestors.length - 1; i >= 0; i--) {
          branch = { ...ancestors[i], children: [branch] };
        }
        // Geometry-bearing families paint their own path and their descendants;
        // children added to the back of text paint behind its glyphs.
        const parent = { ...mobject, type: 'vgroup' };
        const children = mobject.children || [];
        for (const child of children) if (child.behind_parent) collect(child, [...ancestors, parent], views);
        layers.push({ branch, leaf: mobject, views, z: mobject.z_index ?? 0 });
        for (const child of children) if (!child.behind_parent) collect(child, [...ancestors, parent], views);
      }
    };
    let roots = sceneData.mobjects || [];
    // ThreeDScene frames hold world-space leaves; project them for this camera.
    if (camera.three_d) roots = this.projectThreeD(roots, camera.three_d);
    for (const mobject of roots) collect(mobject);
    // Stable sorting preserves scene/family order for equal z_index values.
    layers.sort((a, b) => a.z - b.z);
    const views = new Map();
    for (const view of camera.views || []) {
      const boxes = [view.source, view.display];
      if (!Number.isInteger(view.id) || !boxes.every(box => Array.isArray(box) && box.length === 4 &&
          box.every(Number.isFinite) && box[2] >= box[0] && box[3] >= box[1]) ||
          !(view.source[2] > view.source[0] && view.source[3] > view.source[1]) ||
          !/^#[0-9a-f]{6}$/i.test(view.background) ||
          !(view.background_opacity >= 0 && view.background_opacity <= 1)) throw new Error('Invalid camera view');
      views.set(view.id, view);
    }
    for (const { branch, leaf } of layers) {
      const view = views.get(leaf.camera_screen);
      const element = view ? this.renderCameraView(view, leaf, layers, mathGlyphs)
        : this.renderMobject(branch, mathGlyphs);
      if (element) mainGroup.appendChild(element);
    }
    delete this._strokeUnit;
    return svg;
  },

  /**
   * Community's ThreeDCamera applied to world-space leaves: start-corner shading,
   * z_index then depth ordering, and rotate-then-perspective projection. Returns new
   * identity-pose leaves ranked by z_index; the frame data itself is not modified.
   */
  projectThreeD(leaves, three) {
    const numbers = [three.phi, three.theta, three.gamma, three.zoom, three.focal_distance];
    const point3 = p => Array.isArray(p) && p.length === 3 && p.every(Number.isFinite);
    if (!numbers.every(Number.isFinite) || !point3(three.frame_center) || !point3(three.light_source)) {
      throw new Error('Invalid 3D camera');
    }
    const rotateZ = a => [[Math.cos(a), -Math.sin(a), 0], [Math.sin(a), Math.cos(a), 0], [0, 0, 1]];
    const rotateX = a => [[1, 0, 0], [0, Math.cos(a), -Math.sin(a)], [0, Math.sin(a), Math.cos(a)]];
    const multiply = (a, b) => a.map(row => [0, 1, 2].map(j => row[0] * b[0][j] + row[1] * b[1][j] + row[2] * b[2][j]));
    const rot = multiply(rotateZ(three.gamma), multiply(rotateX(-three.phi), rotateZ(-three.theta - Math.PI / 2)));
    const [cx, cy, cz] = three.frame_center;
    const fd = three.focal_distance, zoom = three.zoom;
    const rotate = p => {
      const x = p[0] - cx, y = p[1] - cy, z = (p[2] ?? 0) - cz;
      return rot.map(row => row[0] * x + row[1] * y + row[2] * z);
    };
    const factor = rz => three.exponential ? (rz >= 0 ? Math.exp(rz / fd) : fd / (fd - rz))
      : (fd - rz < 0 ? 1e6 : fd / (fd - rz));
    const project = p => {
      const r = rotate(p);
      const f = factor(r[2]) * zoom;
      return [r[0] * f, r[1] * f, r[2]];
    };
    const sub = (a, b) => [a[0] - b[0], a[1] - b[1], (a[2] ?? 0) - (b[2] ?? 0)];
    const norm = v => Math.hypot(v[0], v[1], v[2]);
    const normalize = v => { const n = norm(v); return n > 0 ? v.map(c => c / n) : [0, 0, 0]; };
    const center = points => [0, 1, 2].map(i => {
      let low = Infinity, high = -Infinity;
      for (const p of points) { const v = p[i] ?? 0; if (v < low) low = v; if (v > high) high = v; }
      return points.length ? (low + high) / 2 : 0;
    });
    // Community's get_unit_normal, scaled by the largest component for stability.
    const unitNormal = (v1, v2) => {
      const tol = 1e-6;
      const d1 = Math.max(...v1.map(Math.abs)), d2 = Math.max(...v2.map(Math.abs));
      let u;
      if (d1 === 0) {
        if (d2 === 0) return [0, -1, 0];
        u = v2.map(c => c / d2);
      } else if (d2 === 0) {
        u = v1.map(c => c / d1);
      } else {
        const a = v1.map(c => c / d1), b = v2.map(c => c / d2);
        const cp = [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
        const n = norm(cp);
        if (n > tol) return cp.map(c => c / n);
        u = a;
      }
      if (Math.abs(u[0]) < tol && Math.abs(u[1]) < tol) return [0, -1, 0];
      const cp = [-u[0] * u[2], -u[1] * u[2], u[0] * u[0] + u[1] * u[1]];
      const n = norm(cp);
      return cp.map(c => c / n);
    };
    const shade = (color, points) => {
      if (Array.isArray(color)) return color.map(item => shade(item, points));
      if (typeof color !== 'string' || !/^#[0-9a-f]{6}$/i.test(color)) return color;
      const count = points.length;
      let normal = [0, 1, 0];
      if (!(2 * Math.floor(count / 4) <= 2 || count < 4)) {
        normal = unitNormal(sub(points[3], points[0]), sub(points[count - 4], points[0]));
        if (norm(normal) === 0) normal = [0, 1, 0];
      }
      const toSun = normalize(sub(three.light_source, points[0]));
      const unit = normalize(normal);
      let light = 0.5 * (unit[0] * toSun[0] + unit[1] * toSun[1] + unit[2] * toSun[2]) ** 3;
      if (light < 0) light *= 0.5;
      // ManimColor.to_hex truncates each clamped channel.
      return '#' + [1, 3, 5].map(i => Math.trunc(Math.min(1, Math.max(0, parseInt(color.slice(i, i + 2), 16) / 255 + light)) * 255)
        .toString(16).toUpperCase().padStart(2, '0')).join('');
    };
    const entries = leaves.map(leaf => {
      const fixed = Boolean(leaf._fixed_in_frame);
      const orient = point3(leaf.orient_center) ? leaf.orient_center : null;
      const out = { ...leaf };
      let world;
      if (point3(leaf.anchor3d)) {
        world = [leaf.anchor3d];
        const gc = leaf.geometry_center || [0, 0, 0];
        if (orient) {
          const shift = sub(project(orient), orient);
          out.position = leaf.position.map((v, i) => v + shift[i]);
        } else if (!fixed) {
          const projected = project(leaf.anchor3d);
          out.position = [projected[0] - gc[0], projected[1] - gc[1], 0];
          out.geometry_scale = (leaf.geometry_scale ?? 1) * factor(rotate(leaf.anchor3d)[2]) * zoom;
        }
      } else {
        const curves = leaf.curves || [];
        world = curves.flat();
        if (!fixed) {
          const shift = orient ? sub(project(orient), orient) : null;
          const map = shift ? p => [p[0] + shift[0], p[1] + shift[1], (p[2] ?? 0) + shift[2]] : project;
          out.curves = curves.map(curve => curve.map(map));
          if (leaf.vertices) out.vertices = leaf.vertices.map(map);
          for (const key of ['start', 'end', 'shaft_start', 'shaft_end']) {
            if (point3(leaf[key])) out[key] = map(leaf[key]);
          }
          if (three.shading && leaf.shade_in_3d && world.length) {
            out.fill_color = shade(leaf.fill_color, world);
            out.stroke_color = shade(leaf.stroke_color, world);
          }
        }
        world = world.concat(leaf.vertices || []);
      }
      // Community sorts shaded paths by the rotated depth of their center; others
      // (text, fixed-in-frame leaves) keep their order at the front.
      let key = Infinity;
      if (!fixed && leaf.shade_in_3d && !point3(leaf.anchor3d)) {
        key = rotate(point3(leaf.depth_center) ? leaf.depth_center : center(world))[2];
      }
      return { out, key, z: leaf.z_index ?? 0 };
    });
    const order = (a, b) => (a < b ? -1 : a > b ? 1 : 0);
    entries.sort((a, b) => order(a.z, b.z));
    entries.sort((a, b) => order(a.key, b.key));
    return entries.map((entry, rank) => ({ ...entry.out, z_index: rank }));
  },

  /**
   * A ZoomedScene display: the scene seen through its camera frame, stretched to the
   * display box like Community's camera image, over the camera background.
   */
  renderCameraView(view, display, layers, mathGlyphs) {
    const unit = this.UNIT_SCALE;
    const [left, bottom, right, top] = view.display;
    const [sourceLeft, sourceBottom, sourceRight, sourceTop] = view.source;
    const group = document.createElementNS(this.SVG_NS, 'g');
    group.setAttribute('opacity', display.opacity ?? 1);
    group.setAttribute('data-camera-view', view.id);
    const id = `manim-view-${this._viewSerial = (this._viewSerial || 0) + 1}`;
    const clip = document.createElementNS(this.SVG_NS, 'clipPath');
    clip.setAttribute('id', id);
    const box = () => {
      const rect = document.createElementNS(this.SVG_NS, 'rect');
      rect.setAttribute('x', left * unit);
      rect.setAttribute('y', bottom * unit);
      rect.setAttribute('width', (right - left) * unit);
      rect.setAttribute('height', (top - bottom) * unit);
      return rect;
    };
    clip.appendChild(box());
    const defs = document.createElementNS(this.SVG_NS, 'defs');
    defs.appendChild(clip);
    group.appendChild(defs);
    const body = document.createElementNS(this.SVG_NS, 'g');
    body.setAttribute('clip-path', `url(#${id})`);
    const backdrop = box();
    backdrop.setAttribute('fill', view.background);
    backdrop.setAttribute('fill-opacity', view.background_opacity);
    body.appendChild(backdrop);
    const content = document.createElementNS(this.SVG_NS, 'g');
    const scaleX = (right - left) / (sourceRight - sourceLeft);
    const scaleY = (top - bottom) / (sourceTop - sourceBottom);
    content.setAttribute('transform', `translate(${(left + right) / 2 * unit}, ${(bottom + top) / 2 * unit}) ` +
      `scale(${scaleX}, ${scaleY}) translate(${-(sourceLeft + sourceRight) / 2 * unit}, ${-(sourceBottom + sourceTop) / 2 * unit})`);
    for (const layer of layers) {
      // Other displays' own boxes stay out of a view: no recursive cameras.
      if (layer.views.includes(view.id) || Number.isInteger(layer.leaf.camera_screen)) continue;
      const element = this.renderMobject(layer.branch, mathGlyphs);
      if (element) content.appendChild(element);
    }
    body.appendChild(content);
    group.appendChild(body);
    return group;
  },

  /**
   * Render a single mobject
   */
  renderMobject(mobject, mathGlyphs, inheritedScale = 1) {
    const type = mobject.type;
    if (type === 'valuetracker' || type === 'mobject') return null;
    const position = mobject.position || [0, 0, 0];

    let element = null;

    switch (type) {
      case 'circle':
        element = this.renderCircle(mobject);
        break;
      case 'annulus':
        element = this.renderAnnulus(mobject);
        break;
      case 'ellipse':
        element = this.renderEllipse(mobject);
        break;
      case 'arc':
        element = this.renderArc(mobject);
        break;
      case 'square':
        element = this.renderSquare(mobject);
        break;
      case 'rectangle':
        element = this.renderRectangle(mobject);
        break;
      case 'line':
        element = this.renderLine(mobject);
        break;
      case 'arrow':
        element = this.renderArrow(mobject);
        break;
      case 'triangle':
        element = this.renderTriangle(mobject);
        break;
      case 'polyline':
        element = this.renderCornerPath(mobject);
        break;
      case 'bezierpath':
        element = this.renderBezierPath(mobject);
        break;
      case 'polygon':
        element = this.renderPolygon(mobject);
        break;
      case 'text':
        element = this.renderText(mobject);
        break;
      case 'image':
        element = this.renderImage(mobject);
        break;
      case 'pointcloud':
        element = this.renderPointCloud(mobject, Math.abs(inheritedScale * (mobject.geometry_scale ?? 1)));
        break;
      case 'mathtex':
        element = this.renderMathTex(mobject, mathGlyphs);
        break;
      case 'vgroup':
        element = this.renderVGroup(mobject, mathGlyphs, inheritedScale);
        break;
      default:
        console.warn(`Unknown mobject type: ${type}`);
        return null;
    }

    let paintDefs = null;
    const paint = (color, opacities) => {
      // Community draws color and opacity lists as gradients; make_even pairs their stops.
      const alphas = Array.isArray(opacities) && opacities.length > 1 && opacities.length <= 64 &&
        opacities.every(Number.isFinite) ? opacities : null;
      if (!Array.isArray(color) && !alphas) return color;
      if (!Array.isArray(color)) color = [color];
      if (!color.length || color.length > 64 || !color.every(stop => /^#[0-9a-f]{6}$/i.test(stop))) {
        throw new Error('Gradient colors require 1 to 64 six-digit hex colors');
      }
      if (color.length === 1 && !alphas) return color[0];
      const count = Math.max(color.length, alphas ? alphas.length : 1);
      const even = list => Array.from({ length: count }, (_, i) => list[Math.floor(i * list.length / count)]);
      const stopColors = even(color);
      const stopAlphas = alphas ? even(alphas) : null;
      paintDefs ||= document.createElementNS(this.SVG_NS, 'defs');
      const gradient = document.createElementNS(this.SVG_NS, 'linearGradient');
      const id = `manim-gradient-${this._gradientSerial = (this._gradientSerial || 0) + 1}`;
      gradient.setAttribute('id', id);
      const ends = mobject.gradient_points;
      if (Array.isArray(ends) && ends.length === 2 && ends.every(point => Array.isArray(point) &&
          Number.isFinite(point[0]) && Number.isFinite(point[1])) &&
          (ends[0][0] !== ends[1][0] || ends[0][1] !== ends[1][1])) {
        // Local geometry endpoints, e.g. a stream line's chord, in the path's own coordinates.
        gradient.setAttribute('gradientUnits', 'userSpaceOnUse');
        gradient.setAttribute('x1', ends[0][0] * this.UNIT_SCALE);
        gradient.setAttribute('y1', ends[0][1] * this.UNIT_SCALE);
        gradient.setAttribute('x2', ends[1][0] * this.UNIT_SCALE);
        gradient.setAttribute('y2', ends[1][1] * this.UNIT_SCALE);
      } else {
        gradient.setAttribute('x1', '0%');
        gradient.setAttribute('y1', '0%');
        gradient.setAttribute('x2', '100%');
        gradient.setAttribute('y2', '0%');
      }
      stopColors.forEach((stopColor, index) => {
        const stop = document.createElementNS(this.SVG_NS, 'stop');
        stop.setAttribute('offset', `${100 * index / (count - 1)}%`);
        stop.setAttribute('stop-color', stopColor);
        if (stopAlphas) stop.setAttribute('stop-opacity', Math.max(0, Math.min(1, stopAlphas[index])));
        gradient.appendChild(stop);
      });
      paintDefs.appendChild(gradient);
      return `url(#${id})`;
    };
    if (element) {
      element.setAttribute('opacity', mobject.opacity ?? 1);
      // Group styles live on each child, avoiding compounded group opacity.
      if (type !== 'vgroup') {
        const fill = paint(mobject.fill_color ?? mobject.color ?? '#FFFFFF', mobject.fill_opacities);
        const stroke = paint(mobject.stroke_color ?? mobject.color ?? '#FFFFFF', mobject.stroke_opacities);
        for (const leaf of [element, ...element.querySelectorAll('*')]) {
          if (leaf.getAttribute('fill') && leaf.getAttribute('fill') !== 'none') {
            leaf.setAttribute('fill', fill);
          }
          if (leaf.getAttribute('stroke')) {
            leaf.setAttribute('stroke', stroke);
            leaf.setAttribute('stroke-opacity', mobject.stroke_opacity ?? 1);
            // Community's CapStyleType/LineJointType; AUTO (0) keeps the butt/miter defaults.
            const cap = { 1: 'round', 2: 'butt', 3: 'square' }[mobject.cap_style];
            const join = { 1: 'round', 2: 'bevel', 3: 'miter' }[mobject.joint_type];
            if (cap) leaf.setAttribute('stroke-linecap', cap);
            if (join) leaf.setAttribute('stroke-linejoin', join);
          }
        }
      }
      if (this._strokeUnit === undefined) {
        // Standalone rendering keeps screen-pixel strokes.
        for (const leaf of [element, ...element.querySelectorAll('*')]) {
          leaf.setAttribute('vector-effect', leaf.getAttribute('stroke-dasharray') ? 'none' : 'non-scaling-stroke');
        }
      } else if (type !== 'vgroup') {
        // Scene strokes are in local units, undoing this object's scale chain.
        const scale = Math.abs(inheritedScale * (mobject.geometry_scale ?? 1)) *
          (type === 'mathtex' ? (mobject.font_size || 48) / 96 * this.UNIT_SCALE / 1000 : 1);
        for (const leaf of [element, ...element.querySelectorAll('*')]) {
          const width = parseFloat(leaf.getAttribute('stroke-width'));
          if (Number.isFinite(width)) leaf.setAttribute('stroke-width', scale > 0 ? width * this._strokeUnit / scale : 0);
        }
      }
    }

    if (element && (type === 'text' || type === 'mathtex') && Array.isArray(mobject.glyph_matrix) &&
        mobject.glyph_matrix.length === 4 && mobject.glyph_matrix.every(Number.isFinite)) {
      // A general local glyph map [[a, b], [c, d]] in the y-up scene frame (e.g. ApplyMatrix).
      const [a, b, c, d] = mobject.glyph_matrix;
      element.setAttribute('transform', `matrix(${a}, ${c}, ${b}, ${d}, 0, 0) ${element.getAttribute('transform') || ''}`.trim());
    } else if (element && (type === 'text' || type === 'mathtex') && Array.isArray(mobject.glyph_stretch)) {
      // Axis-aligned glyph stretching happens in the glyph's own frame.
      const [sx, sy] = mobject.glyph_stretch;
      if (Number.isFinite(sx) && Number.isFinite(sy)) {
        element.setAttribute('transform', `scale(${sx}, ${sy}) ${element.getAttribute('transform') || ''}`.trim());
      }
    }

    if (element && mobject.draw_progress !== undefined) {
      const progress = Math.max(0, Math.min(1, mobject.draw_progress));
      for (const path of [element, ...element.querySelectorAll('line, path')]) {
        // Normalized dashes must scale with the path, including preview resizing.
        // A non-scaling stroke makes the visible fraction depend on viewport size.
        if (this._strokeUnit === undefined) path.setAttribute('vector-effect', 'none');
        path.setAttribute('pathLength', 1);
        path.setAttribute('stroke-dasharray', '1 1');
        path.setAttribute('stroke-dashoffset', 1 - progress);
      }
    }

    if (element && type !== 'vgroup' && mobject.background_stroke_width > 0) {
      // Community's background stroke is painted behind the fill: a stroke-only copy first.
      const back = element.cloneNode(true);
      const scale = this._strokeUnit === undefined ? 1 : Math.abs(inheritedScale * (mobject.geometry_scale ?? 1)) *
        (type === 'mathtex' ? (mobject.font_size || 48) / 96 * this.UNIT_SCALE / 1000 : 1);
      const width = this._strokeUnit === undefined ? mobject.background_stroke_width :
        (scale > 0 ? mobject.background_stroke_width * this._strokeUnit / scale : 0);
      for (const leaf of [back, ...back.querySelectorAll('*')]) {
        if (leaf.localName === 'g' || leaf.localName === 'defs') continue;
        leaf.setAttribute('fill', 'none');
        leaf.setAttribute('stroke', mobject.background_stroke_color || '#000000');
        leaf.setAttribute('stroke-width', width);
        leaf.setAttribute('stroke-opacity', mobject.background_stroke_opacity ?? 1);
        leaf.setAttribute('stroke-linejoin', 'round');
      }
      const pair = document.createElementNS(this.SVG_NS, 'g');
      pair.setAttribute('opacity', element.getAttribute('opacity') ?? 1);
      element.setAttribute('opacity', 1);
      back.setAttribute('opacity', 1);
      pair.appendChild(back);
      pair.appendChild(element);
      element = pair;
    }

    if (element && paintDefs) {
      const wrapper = document.createElementNS(this.SVG_NS, 'g');
      wrapper.appendChild(paintDefs);
      wrapper.appendChild(element);
      element = wrapper;
    }
    if (element && position) {
      const x = position[0] * this.UNIT_SCALE;
      const y = position[1] * this.UNIT_SCALE;
      const currentTransform = element.getAttribute('transform') || '';
      const center = mobject.geometry_center || [0, 0, 0];
      const cx = center[0] * this.UNIT_SCALE;
      const cy = center[1] * this.UNIT_SCALE;
      const angle = (mobject.angle || 0) * 180 / Math.PI;
      const size = mobject.geometry_scale ?? 1;
      element.setAttribute('transform', `translate(${x}, ${y}) translate(${cx}, ${cy}) rotate(${angle}) scale(${size}) translate(${-cx}, ${-cy}) ${currentTransform}`);
    }

    return element;
  },

  /**
   * Point clouds: one filled path of fixed-size squares per color/opacity, sized like
   * Community's pixel thickening (not scaled with the object).
   */
  renderPointCloud(mobject, scale) {
    const group = document.createElementNS(this.SVG_NS, 'g');
    const cloud = Array.isArray(mobject.cloud) ? mobject.cloud : [];
    const colors = Array.isArray(mobject.cloud_colors) ? mobject.cloud_colors : [];
    const opacities = Array.isArray(mobject.cloud_opacities) ? mobject.cloud_opacities : [];
    const side = (Number(mobject.point_size) || 0) * this.UNIT_SCALE / (scale > 0 ? scale : 1);
    if (!(side > 0)) return group;
    const half = side / 2;
    const batches = new Map();
    cloud.forEach((point, index) => {
      const color = /^#[0-9a-f]{6}$/i.test(colors[index]) ? colors[index] : '#FFFFFF';
      const opacity = Number.isFinite(opacities[index]) ? opacities[index] : 1;
      const key = `${color}|${opacity}`;
      const x = point[0] * this.UNIT_SCALE - half;
      const y = point[1] * this.UNIT_SCALE - half;
      if (!Number.isFinite(x) || !Number.isFinite(y)) return;
      if (!batches.has(key)) batches.set(key, []);
      batches.get(key).push(`M${x} ${y}h${side}v${side}h${-side}z`);
    });
    for (const [key, parts] of batches) {
      const [color, opacity] = key.split('|');
      const path = document.createElementNS(this.SVG_NS, 'path');
      path.setAttribute('d', parts.join(''));
      // Point colors are per point, so they are set here rather than by the shared paint step.
      path.setAttribute('data-point-color', color);
      path.setAttribute('style', `fill:${color};fill-opacity:${opacity}`);
      group.appendChild(path);
    }
    return group;
  },

  /** Raster images: only inline base64 image data, drawn upright in local units. */
  renderImage(mobject) {
    const href = typeof mobject.href === 'string' ? mobject.href : '';
    if (!/^data:image\/(png|jpeg|jpg|gif|webp);base64,[A-Za-z0-9+/=]+$/.test(href)) {
      throw new Error('Images must be inline base64 PNG, JPEG, GIF or WebP data.');
    }
    const width = (mobject.width ?? 0) * this.UNIT_SCALE;
    const height = (mobject.height ?? 0) * this.UNIT_SCALE;
    const image = document.createElementNS(this.SVG_NS, 'image');
    image.setAttribute('href', href);
    image.setAttribute('x', -width / 2);
    image.setAttribute('y', -height / 2);
    image.setAttribute('width', width);
    image.setAttribute('height', height);
    image.setAttribute('preserveAspectRatio', 'none');
    // The scene is drawn y-up; flip the bitmap back upright like text.
    image.setAttribute('transform', 'scale(1, -1)');
    if (mobject.resampling_algorithm === 'nearest') image.setAttribute('style', 'image-rendering: pixelated');
    return image;
  },

  /**
   * Render a circle
   */
  renderCircle(mobject) {
    const circle = document.createElementNS(this.SVG_NS, 'circle');
    const radius = (mobject.radius ?? 1) * this.UNIT_SCALE;
    circle.setAttribute('r', radius);
    circle.setAttribute('cx', 0);
    circle.setAttribute('cy', 0);
    circle.setAttribute('fill', mobject.color || '#FFFFFF');
    circle.setAttribute('fill-opacity', mobject.fill_opacity !== undefined ? mobject.fill_opacity : 0);
    circle.setAttribute('stroke', mobject.color || '#FFFFFF');
    circle.setAttribute('stroke-width', mobject.stroke_width ?? 2);
    return circle;
  },

  /** Opposite closed contours leave a hole without a radial stroke. */
  renderAnnulus(mobject) {
    const path = document.createElementNS(this.SVG_NS, 'path');
    const contour = (radius, sweep) => {
      const r = radius * this.UNIT_SCALE;
      return `M ${r},0 A ${r},${r} 0 1 ${sweep} ${-r},0 A ${r},${r} 0 1 ${sweep} ${r},0 Z`;
    };
    path.setAttribute('d', contour(mobject.outer_radius ?? 2, 1) + ' ' + contour(mobject.inner_radius ?? 1, 0));
    path.setAttribute('fill-rule', 'nonzero');
    path.setAttribute('fill', mobject.color || '#FFFFFF');
    path.setAttribute('fill-opacity', mobject.fill_opacity ?? 1);
    path.setAttribute('stroke', mobject.color || '#FFFFFF');
    path.setAttribute('stroke-width', mobject.stroke_width ?? 0);
    return path;
  },

  /** Render an oval with independent horizontal and vertical radii. */
  renderEllipse(mobject) {
    const ellipse = document.createElementNS(this.SVG_NS, 'ellipse');
    ellipse.setAttribute('rx', (mobject.width ?? 2) * this.UNIT_SCALE / 2);
    ellipse.setAttribute('ry', (mobject.height ?? 1) * this.UNIT_SCALE / 2);
    ellipse.setAttribute('cx', 0);
    ellipse.setAttribute('cy', 0);
    ellipse.setAttribute('fill', mobject.color || '#FFFFFF');
    ellipse.setAttribute('fill-opacity', mobject.fill_opacity ?? 0);
    ellipse.setAttribute('stroke', mobject.color || '#FFFFFF');
    ellipse.setAttribute('stroke-width', mobject.stroke_width ?? 2);
    return ellipse;
  },

  /** Render a circular arc as bounded SVG arc segments, including a full turn. */
  renderArc(mobject) {
    const path = document.createElementNS(this.SVG_NS, 'path');
    const radius = (mobject.radius ?? 1) * this.UNIT_SCALE;
    const start = mobject.start_angle ?? 0;
    const angle = mobject.arc_angle ?? Math.PI / 2;
    const point = a => `${radius * Math.cos(a)},${radius * Math.sin(a)}`;
    let d = `M ${point(start)}`;
    const segments = Math.ceil(Math.abs(angle) / Math.PI);
    if (radius > 0) {
      for (let i = 1; i <= segments; i++) {
        d += ` A ${radius},${radius} 0 0 ${angle >= 0 ? 1 : 0} ${point(start + angle * i / segments)}`;
      }
    }
    path.setAttribute('d', d);
    path.setAttribute('fill', mobject.color || '#FFFFFF');
    path.setAttribute('fill-opacity', mobject.fill_opacity ?? 0);
    path.setAttribute('stroke', mobject.color || '#FFFFFF');
    path.setAttribute('stroke-width', mobject.stroke_width ?? 2);
    return path;
  },

  /**
   * Render a square
   */
  renderSquare(mobject) {
    const rect = document.createElementNS(this.SVG_NS, 'rect');
    const size = (mobject.side_length ?? 2) * this.UNIT_SCALE;
    rect.setAttribute('x', -size / 2);
    rect.setAttribute('y', -size / 2);
    rect.setAttribute('width', size);
    rect.setAttribute('height', size);
    rect.setAttribute('fill', mobject.color || '#FFFFFF');
    rect.setAttribute('fill-opacity', mobject.fill_opacity !== undefined ? mobject.fill_opacity : 0);
    rect.setAttribute('stroke', mobject.color || '#FFFFFF');
    rect.setAttribute('stroke-width', mobject.stroke_width ?? 2);
    return rect;
  },

  /**
   * Render a rectangle
   */
  renderRectangle(mobject) {
    const rect = document.createElementNS(this.SVG_NS, 'rect');
    const width = (mobject.width ?? 4) * this.UNIT_SCALE;
    const height = (mobject.height ?? 2) * this.UNIT_SCALE;
    rect.setAttribute('x', -width / 2);
    rect.setAttribute('y', -height / 2);
    rect.setAttribute('width', width);
    rect.setAttribute('height', height);
    rect.setAttribute('fill', mobject.color || '#FFFFFF');
    rect.setAttribute('fill-opacity', mobject.fill_opacity !== undefined ? mobject.fill_opacity : 0);
    rect.setAttribute('stroke', mobject.color || '#FFFFFF');
    rect.setAttribute('stroke-width', mobject.stroke_width ?? 2);
    return rect;
  },

  /**
   * Render a line
   */
  renderLine(mobject) {
    const line = document.createElementNS(this.SVG_NS, 'line');
    const start = mobject.shaft_start || mobject.start || [-1, 0, 0];
    const end = mobject.shaft_end || mobject.end || [1, 0, 0];
    line.setAttribute('x1', start[0] * this.UNIT_SCALE);
    line.setAttribute('y1', start[1] * this.UNIT_SCALE);
    line.setAttribute('x2', end[0] * this.UNIT_SCALE);
    line.setAttribute('y2', end[1] * this.UNIT_SCALE);
    line.setAttribute('stroke', mobject.color || '#FFFFFF');
    line.setAttribute('stroke-width', mobject.stroke_width ?? 2);
    return line;
  },

  /**
   * Render an arrow
   */
  renderArrow(mobject) {
    if (mobject.explicit_tips) return this.renderLine(mobject);
    const group = document.createElementNS(this.SVG_NS, 'g');
    const start = mobject.start || [-1, 0, 0];
    const end = mobject.end || [1, 0, 0];
    const color = mobject.color || '#FFFFFF';

    // Line
    const line = document.createElementNS(this.SVG_NS, 'line');
    line.setAttribute('x1', start[0] * this.UNIT_SCALE);
    line.setAttribute('y1', start[1] * this.UNIT_SCALE);
    line.setAttribute('x2', end[0] * this.UNIT_SCALE);
    line.setAttribute('y2', end[1] * this.UNIT_SCALE);
    line.setAttribute('stroke', color);
    line.setAttribute('stroke-width', mobject.stroke_width ?? 2);
    group.appendChild(line);

    // Arrowhead
    const dx = end[0] - start[0];
    const dy = end[1] - start[1];
    const angle = Math.atan2(dy, dx);
    const headLength = 0.3 * this.UNIT_SCALE;
    const headAngle = Math.PI / 6;

    const endX = end[0] * this.UNIT_SCALE;
    const endY = end[1] * this.UNIT_SCALE;

    const path = document.createElementNS(this.SVG_NS, 'path');
    const x1 = endX - headLength * Math.cos(angle - headAngle);
    const y1 = endY - headLength * Math.sin(angle - headAngle);
    const x2 = endX - headLength * Math.cos(angle + headAngle);
    const y2 = endY - headLength * Math.sin(angle + headAngle);

    path.setAttribute('d', `M ${endX} ${endY} L ${x1} ${y1} M ${endX} ${endY} L ${x2} ${y2}`);
    path.setAttribute('stroke', color);
    path.setAttribute('stroke-width', mobject.stroke_width ?? 2);
    path.setAttribute('fill', 'none');
    group.appendChild(path);

    return group;
  },

  /**
   * Render a triangle
   */
  renderTriangle(mobject) {
    const polygon = document.createElementNS(this.SVG_NS, 'polygon');
    const size = this.UNIT_SCALE;
    const height = size * Math.sqrt(3) / 2;
    const points = [
      [0, height * 2 / 3],
      [-size / 2, -height / 3],
      [size / 2, -height / 3]
    ].map(p => p.join(',')).join(' ');
    polygon.setAttribute('points', points);
    polygon.setAttribute('fill', mobject.color || '#FFFFFF');
    polygon.setAttribute('fill-opacity', mobject.fill_opacity !== undefined ? mobject.fill_opacity : 0);
    polygon.setAttribute('stroke', mobject.color || '#FFFFFF');
    polygon.setAttribute('stroke-width', mobject.stroke_width ?? 2);
    return polygon;
  },

  /**
   * Render a polygon
   */
  renderCornerPath(mobject) {
    const path = document.createElementNS(this.SVG_NS, 'path');
    const points = mobject.vertices || [];
    path.setAttribute('d', points.map((point, i) => `${i ? 'L' : 'M'} ${point[0] * this.UNIT_SCALE},${point[1] * this.UNIT_SCALE}`).join(' '));
    path.setAttribute('fill', mobject.fill_color ?? mobject.color ?? '#FFFFFF');
    path.setAttribute('fill-opacity', mobject.fill_opacity ?? 0);
    path.setAttribute('stroke', mobject.stroke_color ?? mobject.color ?? '#FFFFFF');
    path.setAttribute('stroke-width', mobject.stroke_width ?? 4);
    return path;
  },

  renderBezierPath(mobject) {
    const path = this.renderCornerPath({ ...mobject, vertices: [] });
    const curves = mobject.shaft_curves || mobject.curves || [];
    const xy = point => `${point[0] * this.UNIT_SCALE},${point[1] * this.UNIT_SCALE}`;
    const commands = [];
    let start = null, end = null, offset = 0;
    const boundaries = new Set();
    for (const length of mobject.subpath_lengths || []) {
      boundaries.add(offset);
      offset += length;
    }
    const close = () => { if (start !== null && start === end) commands.push('Z'); };
    curves.forEach((curve, index) => {
      const anchor = xy(curve[0]);
      if (start === null || (boundaries.size ? boundaries.has(index) : anchor !== end)) {
        close();
        commands.push(`M ${anchor}`);
        start = anchor;
      }
      commands.push(`C ${curve.slice(1).map(xy).join(' ')}`);
      end = xy(curve[3]);
    });
    close();
    if (mobject.vertices?.length) commands.push(`M ${xy(mobject.vertices[0])}`);
    path.setAttribute('d', commands.join(' '));
    return path;
  },

  renderPolygon(mobject) {
    const polygon = document.createElementNS(this.SVG_NS, 'polygon');
    const vertices = mobject.vertices || [];
    const points = vertices.map(v => {
      const x = v[0] * this.UNIT_SCALE;
      const y = v[1] * this.UNIT_SCALE;
      return `${x},${y}`;
    }).join(' ');
    polygon.setAttribute('points', points);
    polygon.setAttribute('fill', mobject.color || '#FFFFFF');
    polygon.setAttribute('fill-opacity', mobject.fill_opacity !== undefined ? mobject.fill_opacity : 0);
    polygon.setAttribute('stroke', mobject.color || '#FFFFFF');
    polygon.setAttribute('stroke-width', mobject.stroke_width ?? 2);
    return polygon;
  },

  /**
   * Render text
   */
  renderText(mobject) {
    const text = document.createElementNS(this.SVG_NS, 'text');
    text.setAttribute('x', 0);
    text.setAttribute('y', 0);
    text.setAttribute('fill', mobject.color || '#FFFFFF');
    text.setAttribute('stroke', mobject.stroke_color ?? mobject.color ?? '#FFFFFF');
    text.setAttribute('stroke-width', mobject.stroke_width ?? 0);
    // Flip text back since canvas is y-inverted
    text.setAttribute('transform', 'scale(1, -1)');
    text.setAttribute('fill-opacity', mobject.fill_opacity ?? 1);
    const layout = mobject.layout;
    if (!layout || !Array.isArray(layout.lines)) {
      text.setAttribute('font-size', mobject.font_size || 24);
      text.setAttribute('font-family', 'Arial, sans-serif');
      text.setAttribute('text-anchor', 'middle');
      text.setAttribute('dominant-baseline', 'middle');
      text.textContent = mobject.text || '';
      return text;
    }
    // Python lays out lines on the ink-centered origin with Liberation Sans or
    // Computer Modern metrics; textLength pins each advance to that layout.
    const family = layout.family === 'serif'
      ? "'Latin Modern Roman', 'CMU Serif', 'Computer Modern', 'Times New Roman', serif"
      : layout.family === 'mono'
        ? "'DejaVu Sans Mono', 'Liberation Mono', Menlo, Consolas, monospace"
        : "'Liberation Sans', Arial, Helvetica, sans-serif";
    const font = typeof mobject.font === 'string' && /^[\w .-]{1,128}$/.test(mobject.font) ? `'${mobject.font}', ` : '';
    text.setAttribute('font-family', font + family);
    text.setAttribute('font-size', layout.em * this.UNIT_SCALE);
    const weights = { THIN: 100, ULTRALIGHT: 200, LIGHT: 300, SEMILIGHT: 350, BOOK: 380, MEDIUM: 500,
      SEMIBOLD: 600, BOLD: 700, ULTRABOLD: 800, HEAVY: 900, ULTRAHEAVY: 950 };
    if (weights[mobject.weight]) text.setAttribute('font-weight', weights[mobject.weight]);
    if (mobject.slant === 'ITALIC' || mobject.slant === 'OBLIQUE') text.setAttribute('font-style', mobject.slant.toLowerCase());
    text.setAttribute('xml:space', 'preserve');
    text.setAttribute('style', 'white-space: pre');
    for (const line of layout.lines) {
      const span = document.createElementNS(this.SVG_NS, 'tspan');
      span.setAttribute('x', line.x * this.UNIT_SCALE);
      span.setAttribute('y', -line.y * this.UNIT_SCALE);
      if (line.length > 0) {
        span.setAttribute('textLength', line.length * this.UNIT_SCALE);
        span.setAttribute('lengthAdjust', 'spacingAndGlyphs');
      }
      // TeX numbers use a true minus sign; the advance is pinned by textLength.
      span.textContent = layout.family === 'serif' ? line.text.replace(/-/g, '\u2212') : line.text;
      text.appendChild(span);
    }
    return text;
  },

  /**
   * Render a VGroup (container)
   */
  renderMathTex(mobject, mathGlyphs) {
    const whole = mathGlyphs && mathGlyphs.get(mobject.text);
    if (!whole) throw new Error('MathTex glyphs have not been prepared.');
    // A multi-part MathTex draws each \class part from the shared formula; a glyph
    // submobject draws one leaf of it.
    const asset = Number.isInteger(mobject.glyph) ? whole.glyphs?.[mobject.glyph] :
      mobject.part === undefined ? whole : whole.parts?.[mobject.part];
    if (!asset) throw new Error('MathTex part glyphs have not been prepared.');
    const parsed = new DOMParser().parseFromString(asset.svg, 'image/svg+xml');
    const group = document.createElementNS(this.SVG_NS, 'g');
    // Community's TeX em is font_size/96 scene units; MathJax uses 1000 units per em.
    const scale = (mobject.font_size || 48) / 96 * this.UNIT_SCALE / 1000;
    // Center the measured ink box, as Community centers dvisvgm output.
    const [x, y, width, height] = asset.bbox || whole.viewBox;
    group.setAttribute('transform', `scale(1, -1) scale(${scale}) translate(${-x - width / 2}, ${-y - height / 2})`);
    group.setAttribute('fill', mobject.color || '#FFFFFF');
    group.setAttribute('fill-opacity', mobject.fill_opacity ?? 1);
    group.setAttribute('stroke', mobject.color || '#FFFFFF');
    group.setAttribute('stroke-width', mobject.stroke_width || 0);
    // Copy only inert vector geometry. No links, scripts, styles or font references.
    // Nested svg viewports clip the extension pieces of stretchy delimiters.
    const tags = new Set(['g', 'svg', 'path', 'rect', 'line', 'polygon', 'polyline', 'circle', 'ellipse']);
    const attributes = ['d', 'transform', 'x', 'y', 'x1', 'y1', 'x2', 'y2', 'width', 'height', 'points', 'cx', 'cy', 'r', 'rx', 'ry',
      'viewBox'];
    function copyGeometry(node) {
      if (!tags.has(node.localName)) throw new Error('Unsupported math SVG geometry: ' + node.localName);
      const element = document.createElementNS('http://www.w3.org/2000/svg', node.localName);
      for (const name of attributes) {
        if (node.hasAttribute(name)) element.setAttribute(name, node.getAttribute(name));
      }
      for (const child of node.children) element.appendChild(copyGeometry(child));
      return element;
    }
    for (const child of parsed.documentElement.children) group.appendChild(copyGeometry(child));
    group.setAttribute('aria-label', mobject.text);
    return group;
  },

  renderVGroup(mobject, mathGlyphs, inheritedScale = 1) {
    const group = document.createElementNS(this.SVG_NS, 'g');
    if (mobject.children) {
      for (const child of mobject.children) {
        const element = this.renderMobject(child, mathGlyphs, Math.abs(inheritedScale * (mobject.geometry_scale ?? 1)));
        if (element) {
          group.appendChild(element);
        }
      }
    }
    return group;
  }
};

// Export for use in modules or global scope
if (typeof module !== 'undefined' && module.exports) {
  module.exports = ManimRenderer;
} else {
  window.ManimRenderer = ManimRenderer;
}
