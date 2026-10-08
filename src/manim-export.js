/** Rasterize a snapshot, never the changing live player DOM. */
const ManimExport = {
  png(source, width = 800, height = 450, env = globalThis) {
    return new Promise((resolve, reject) => {
      const image = new env.Image();
      const url = env.URL.createObjectURL(new env.Blob([source], { type: 'image/svg+xml' }));
      let settled = false;
      const finish = (error, blob) => {
        if (settled) return;
        settled = true;
        env.clearTimeout(timer);
        image.onload = image.onerror = null;
        env.URL.revokeObjectURL(url);
        if (error) reject(error); else resolve(blob);
      };
      const timer = env.setTimeout(() => finish(new Error('PNG export timed out. Please try again.')), 10000);
      image.onerror = () => finish(new Error('Could not read the animation frame for PNG export.'));
      image.onload = () => {
        try {
          const canvas = env.document.createElement('canvas');
          canvas.width = width;
          canvas.height = height;
          const context = canvas.getContext('2d');
          if (!context) throw new Error('PNG export requires a browser canvas.');
          context.fillStyle = '#000000';
          context.fillRect(0, 0, width, height);
          context.drawImage(image, 0, 0, width, height);
          canvas.toBlob(blob => finish(blob ? null : new Error('Could not encode the PNG frame.'), blob), 'image/png');
        } catch (error) { finish(error); }
      };
      image.src = url;
    });
  }
};
if (typeof module !== 'undefined') module.exports = ManimExport;
else globalThis.ManimExport = ManimExport;
