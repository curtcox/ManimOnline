/**
 * Content Type Detector for ManimOnline
 * Automatically detects whether input is Graphviz DOT or Manim Python
 */

const ContentDetector = {
  /**
   * Detect the content type of the given code
   * @param {string} code - The code to analyze
   * @returns {{ type: 'graphviz' | 'manim' | 'unknown', confidence: number, reason: string }}
   */
  detect(code) {
    if (!code || !code.trim()) {
      return { type: 'unknown', confidence: 0, reason: 'Empty input' };
    }

    const dotScore = this.scoreDot(code);
    const manimScore = this.scoreManim(code);

    if (dotScore.score > manimScore.score && dotScore.score > 0) {
      return {
        type: 'graphviz',
        confidence: Math.min(100, dotScore.score * 10),
        reason: dotScore.reasons.join(', ')
      };
    }

    if (manimScore.score > dotScore.score && manimScore.score > 0) {
      return {
        type: 'manim',
        confidence: Math.min(100, manimScore.score * 10),
        reason: manimScore.reasons.join(', ')
      };
    }

    return { type: 'unknown', confidence: 0, reason: 'No clear indicators' };
  },

  /**
   * Score code for DOT language indicators
   */
  scoreDot(code) {
    let score = 0;
    const reasons = [];

    // Strong indicators
    if (/\b(di)?graph\s+(\w+\s*)?\{/.test(code)) {
      score += 10;
      reasons.push('graph/digraph keyword');
    }

    if (/\bsubgraph\s+/.test(code)) {
      score += 5;
      reasons.push('subgraph keyword');
    }

    // Edge operators
    if (/->/.test(code)) {
      score += 5;
      reasons.push('directed edge (->)');
    }

    if (/--/.test(code) && !/"""/.test(code) && !/'''/.test(code)) {
      score += 3;
      reasons.push('undirected edge (--)');
    }

    // Attribute syntax [key=value]
    if (/\[\s*\w+\s*=/.test(code)) {
      score += 3;
      reasons.push('attribute syntax');
    }

    // DOT-specific keywords
    if (/\b(node|edge)\s*\[/.test(code)) {
      score += 4;
      reasons.push('node/edge defaults');
    }

    // DOT-specific attributes
    if (/\b(shape|label|color|style|fillcolor|fontname|fontsize|rankdir)\s*=/.test(code)) {
      score += 3;
      reasons.push('DOT attributes');
    }

    // Cluster syntax
    if (/cluster_\w+/.test(code)) {
      score += 3;
      reasons.push('cluster naming');
    }

    // Reduce score if Python indicators present
    if (/^(from|import)\s+\w+/.test(code.trim())) {
      score -= 5;
    }

    if (/def\s+\w+\s*\(/.test(code)) {
      score -= 3;
    }

    if (/class\s+\w+/.test(code)) {
      score -= 3;
    }

    return { score: Math.max(0, score), reasons };
  },

  /**
   * Score code for Manim Python indicators
   */
  scoreManim(code) {
    let score = 0;
    const reasons = [];

    // Strong Manim indicators
    if (/from\s+manim\s+import/.test(code)) {
      score += 10;
      reasons.push('manim import');
    }

    if (/import\s+manim/.test(code)) {
      score += 8;
      reasons.push('manim import');
    }

    // Scene class
    if (/class\s+\w+\s*\(\s*Scene\s*\)/.test(code)) {
      score += 10;
      reasons.push('Scene class');
    }

    // construct method
    if (/def\s+construct\s*\(\s*self\s*\)/.test(code)) {
      score += 8;
      reasons.push('construct method');
    }

    // Manim objects
    const manimObjects = ['Circle', 'Square', 'Rectangle', 'Line', 'Arrow', 'Triangle', 'Polygon', 'Text', 'MathTex', 'Tex', 'VGroup', 'Mobject', 'Axes', 'NumberPlane'];
    for (const obj of manimObjects) {
      if (new RegExp(`\\b${obj}\\s*\\(`).test(code)) {
        score += 3;
        reasons.push(`${obj} object`);
        break; // Only count once
      }
    }

    // Manim methods
    if (/self\.(play|add|remove|wait)\s*\(/.test(code)) {
      score += 5;
      reasons.push('scene methods');
    }

    // Manim animations
    const animations = ['Create', 'FadeIn', 'FadeOut', 'Transform', 'ReplacementTransform', 'Write', 'DrawBorderThenFill'];
    for (const anim of animations) {
      if (new RegExp(`\\b${anim}\\s*\\(`).test(code)) {
        score += 4;
        reasons.push(`${anim} animation`);
        break;
      }
    }

    // Manim colors
    if (/\b(BLUE|RED|GREEN|YELLOW|PURPLE|ORANGE|WHITE|BLACK|GRAY|GREY|PINK)\b/.test(code)) {
      score += 2;
      reasons.push('Manim colors');
    }

    // Manim directions
    if (/\b(UP|DOWN|LEFT|RIGHT|ORIGIN|UL|UR|DL|DR)\b/.test(code)) {
      score += 2;
      reasons.push('Manim directions');
    }

    // General Python indicators (weaker)
    if (/^(from|import)\s+\w+/.test(code.trim()) && !reasons.includes('manim import')) {
      score += 2;
      reasons.push('Python import');
    }

    if (/def\s+\w+\s*\(/.test(code) && !reasons.includes('construct method')) {
      score += 1;
      reasons.push('Python function');
    }

    if (/class\s+\w+/.test(code) && !reasons.includes('Scene class')) {
      score += 1;
      reasons.push('Python class');
    }

    return { score: Math.max(0, score), reasons };
  },

  /**
   * Check if URL has type override
   */
  getTypeFromURL() {
    const params = new URLSearchParams(window.location.search);
    const type = params.get('type');
    if (type === 'dot' || type === 'graphviz') {
      return 'graphviz';
    }
    if (type === 'manim' || type === 'python') {
      return 'manim';
    }
    return null;
  }
};

// Export for use in modules or global scope
if (typeof module !== 'undefined' && module.exports) {
  module.exports = ContentDetector;
} else {
  window.ContentDetector = ContentDetector;
}
