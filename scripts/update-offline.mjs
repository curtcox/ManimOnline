import {generateOffline} from '../vendor/fragment-kit-v0.5.0/tools/offline-assets.mjs';
const manifest=await generateOffline('offline.config.json',process.argv.includes('--check'));console.log(manifest.version+': '+manifest.assets.length+' verified assets');
