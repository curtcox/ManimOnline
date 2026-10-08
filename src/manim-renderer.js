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
    const frameHeight = camera.frame_height ?? 9;
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

    // Sort drawable leaves globally, keeping each leaf's ancestor transforms.
    // A child can sit behind or in front of a shape outside its VGroup.
    const layers = [];
    const collect = (mobject, ancestors = []) => {
      if (mobject.type === 'vgroup') {
        for (const child of mobject.children || []) collect(child, [...ancestors, mobject]);
      } else {
        let branch = mobject;
        for (let i = ancestors.length - 1; i >= 0; i--) {
          branch = { ...ancestors[i], children: [branch] };
        }
        layers.push({ branch, z: mobject.z_index ?? 0 });
      }
    };
    for (const mobject of sceneData.mobjects || []) collect(mobject);
    // Stable sorting preserves scene/family order for equal z_index values.
    layers.sort((a, b) => a.z - b.z);
    for (const { branch } of layers) {
      const element = this.renderMobject(branch, mathGlyphs);
      if (element) mainGroup.appendChild(element);
    }

    return svg;
  },

  /**
   * Render a single mobject
   */
  renderMobject(mobject, mathGlyphs) {
    const type = mobject.type;
    if (type === 'valuetracker') return null;
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
      case 'mathtex':
        element = this.renderMathTex(mobject, mathGlyphs);
        break;
      case 'vgroup':
        element = this.renderVGroup(mobject, mathGlyphs);
        break;
      default:
        console.warn(`Unknown mobject type: ${type}`);
        return null;
    }

    if (element) {
      element.setAttribute('opacity', mobject.opacity ?? 1);
      // Group styles live on each child, avoiding compounded group opacity.
      if (type !== 'vgroup') {
        for (const leaf of [element, ...element.querySelectorAll('*')]) {
          if (leaf.getAttribute('fill') && leaf.getAttribute('fill') !== 'none') {
            leaf.setAttribute('fill', mobject.fill_color ?? mobject.color ?? '#FFFFFF');
          }
          if (leaf.getAttribute('stroke')) {
            leaf.setAttribute('stroke', mobject.stroke_color ?? mobject.color ?? '#FFFFFF');
            leaf.setAttribute('stroke-opacity', mobject.stroke_opacity ?? 1);
          }
        }
      }
      for (const leaf of [element, ...element.querySelectorAll('*')]) {
        leaf.setAttribute('vector-effect', leaf.getAttribute('stroke-dasharray') ? 'none' : 'non-scaling-stroke');
      }
    }

    if (element && mobject.draw_progress !== undefined) {
      const progress = Math.max(0, Math.min(1, mobject.draw_progress));
      for (const path of [element, ...element.querySelectorAll('line, path')]) {
        // Normalized dashes must scale with the path, including preview resizing.
        // A non-scaling stroke makes the visible fraction depend on viewport size.
        path.setAttribute('vector-effect', 'none');
        path.setAttribute('pathLength', 1);
        path.setAttribute('stroke-dasharray', '1 1');
        path.setAttribute('stroke-dashoffset', 1 - progress);
      }
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
    const start = mobject.start || [-1, 0, 0];
    const end = mobject.end || [1, 0, 0];
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
    const curves = mobject.curves || [];
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
    text.setAttribute('font-size', mobject.font_size || 24);
    text.setAttribute('font-family', 'Arial, sans-serif');
    text.setAttribute('text-anchor', 'middle');
    text.setAttribute('dominant-baseline', 'middle');
    // Flip text back since canvas is y-inverted
    text.setAttribute('transform', 'scale(1, -1)');
    text.setAttribute('fill-opacity', mobject.fill_opacity ?? 1);
    text.textContent = mobject.text || '';
    return text;
  },

  /**
   * Render a VGroup (container)
   */
  renderMathTex(mobject, mathGlyphs) {
    const asset = mathGlyphs && mathGlyphs.get(mobject.text);
    if (!asset) throw new Error('MathTex glyphs have not been prepared.');
    const parsed = new DOMParser().parseFromString(asset.svg, 'image/svg+xml');
    const group = document.createElementNS(this.SVG_NS, 'g');
    const scale = (mobject.font_size || 48) / 1000;
    const [x, y, width, height] = asset.viewBox;
    group.setAttribute('transform', `scale(1, -1) scale(${scale}) translate(${-x - width / 2}, ${-y - height / 2})`);
    group.setAttribute('fill', mobject.color || '#FFFFFF');
    group.setAttribute('fill-opacity', mobject.fill_opacity ?? 1);
    group.setAttribute('stroke', mobject.color || '#FFFFFF');
    group.setAttribute('stroke-width', mobject.stroke_width || 0);
    // Copy only inert vector geometry. No links, scripts, styles or font references.
    const tags = new Set(['g', 'path', 'rect', 'line', 'polygon', 'polyline', 'circle', 'ellipse']);
    const attributes = ['d', 'transform', 'x', 'y', 'x1', 'y1', 'x2', 'y2', 'width', 'height', 'points', 'cx', 'cy', 'r', 'rx', 'ry'];
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

  renderVGroup(mobject, mathGlyphs) {
    const group = document.createElementNS(this.SVG_NS, 'g');
    if (mobject.children) {
      for (const child of mobject.children) {
        const element = this.renderMobject(child, mathGlyphs);
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
