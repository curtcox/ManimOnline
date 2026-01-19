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
  render(sceneData) {
    const svg = document.createElementNS(this.SVG_NS, 'svg');
    svg.setAttribute('width', this.CANVAS_WIDTH);
    svg.setAttribute('height', this.CANVAS_HEIGHT);
    svg.setAttribute('viewBox', `0 0 ${this.CANVAS_WIDTH} ${this.CANVAS_HEIGHT}`);
    svg.style.backgroundColor = '#000000';

    // Add a group for centering (origin at center of canvas)
    const mainGroup = document.createElementNS(this.SVG_NS, 'g');
    mainGroup.setAttribute('transform', `translate(${this.CANVAS_WIDTH / 2}, ${this.CANVAS_HEIGHT / 2}) scale(1, -1)`);
    svg.appendChild(mainGroup);

    // Render all mobjects
    if (sceneData.mobjects) {
      for (const mobject of sceneData.mobjects) {
        const element = this.renderMobject(mobject);
        if (element) {
          mainGroup.appendChild(element);
        }
      }
    }

    return svg;
  },

  /**
   * Render a single mobject
   */
  renderMobject(mobject) {
    const type = mobject.type;
    const position = mobject.position || [0, 0, 0];
    const color = mobject.color || '#FFFFFF';
    const fillOpacity = mobject.fill_opacity !== undefined ? mobject.fill_opacity : 1;
    const strokeWidth = mobject.stroke_width || 2;

    let element = null;

    switch (type) {
      case 'circle':
        element = this.renderCircle(mobject);
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
      case 'polygon':
        element = this.renderPolygon(mobject);
        break;
      case 'text':
        element = this.renderText(mobject);
        break;
      case 'vgroup':
        element = this.renderVGroup(mobject);
        break;
      default:
        console.warn(`Unknown mobject type: ${type}`);
        return null;
    }

    if (element && position) {
      const x = position[0] * this.UNIT_SCALE;
      const y = position[1] * this.UNIT_SCALE;
      const currentTransform = element.getAttribute('transform') || '';
      element.setAttribute('transform', `translate(${x}, ${y}) ${currentTransform}`);
    }

    return element;
  },

  /**
   * Render a circle
   */
  renderCircle(mobject) {
    const circle = document.createElementNS(this.SVG_NS, 'circle');
    const radius = (mobject.radius || 1) * this.UNIT_SCALE;
    circle.setAttribute('r', radius);
    circle.setAttribute('cx', 0);
    circle.setAttribute('cy', 0);
    circle.setAttribute('fill', mobject.color || '#FFFFFF');
    circle.setAttribute('fill-opacity', mobject.fill_opacity !== undefined ? mobject.fill_opacity : 0);
    circle.setAttribute('stroke', mobject.color || '#FFFFFF');
    circle.setAttribute('stroke-width', mobject.stroke_width || 2);
    return circle;
  },

  /**
   * Render a square
   */
  renderSquare(mobject) {
    const rect = document.createElementNS(this.SVG_NS, 'rect');
    const size = (mobject.side_length || 2) * this.UNIT_SCALE;
    rect.setAttribute('x', -size / 2);
    rect.setAttribute('y', -size / 2);
    rect.setAttribute('width', size);
    rect.setAttribute('height', size);
    rect.setAttribute('fill', mobject.color || '#FFFFFF');
    rect.setAttribute('fill-opacity', mobject.fill_opacity !== undefined ? mobject.fill_opacity : 0);
    rect.setAttribute('stroke', mobject.color || '#FFFFFF');
    rect.setAttribute('stroke-width', mobject.stroke_width || 2);
    return rect;
  },

  /**
   * Render a rectangle
   */
  renderRectangle(mobject) {
    const rect = document.createElementNS(this.SVG_NS, 'rect');
    const width = (mobject.width || 4) * this.UNIT_SCALE;
    const height = (mobject.height || 2) * this.UNIT_SCALE;
    rect.setAttribute('x', -width / 2);
    rect.setAttribute('y', -height / 2);
    rect.setAttribute('width', width);
    rect.setAttribute('height', height);
    rect.setAttribute('fill', mobject.color || '#FFFFFF');
    rect.setAttribute('fill-opacity', mobject.fill_opacity !== undefined ? mobject.fill_opacity : 0);
    rect.setAttribute('stroke', mobject.color || '#FFFFFF');
    rect.setAttribute('stroke-width', mobject.stroke_width || 2);
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
    line.setAttribute('stroke-width', mobject.stroke_width || 2);
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
    line.setAttribute('stroke-width', mobject.stroke_width || 2);
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
    path.setAttribute('stroke-width', mobject.stroke_width || 2);
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
    polygon.setAttribute('stroke-width', mobject.stroke_width || 2);
    return polygon;
  },

  /**
   * Render a polygon
   */
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
    polygon.setAttribute('stroke-width', mobject.stroke_width || 2);
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
    text.setAttribute('font-size', mobject.font_size || 24);
    text.setAttribute('font-family', 'Arial, sans-serif');
    text.setAttribute('text-anchor', 'middle');
    text.setAttribute('dominant-baseline', 'middle');
    // Flip text back since canvas is y-inverted
    text.setAttribute('transform', 'scale(1, -1)');
    text.textContent = mobject.text || '';
    return text;
  },

  /**
   * Render a VGroup (container)
   */
  renderVGroup(mobject) {
    const group = document.createElementNS(this.SVG_NS, 'g');
    if (mobject.children) {
      for (const child of mobject.children) {
        const element = this.renderMobject(child);
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
