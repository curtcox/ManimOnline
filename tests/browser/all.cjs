const{spawnSync}=require('node:child_process'),base=process.env.BASE_URL||'http://127.0.0.1:8000/',browser=process.env.BROWSER||'chromium';
for(const script of ['gallery','smoke','languages','modl-zoom','sharing','touch']){const result=spawnSync(process.execPath,['tests/browser/'+script+'.cjs',base,browser],{stdio:'inherit'});if(result.status)process.exit(result.status);}
const result=spawnSync(process.execPath,['tests/browser/upgrade.cjs',browser],{stdio:'inherit'});process.exitCode=result.status;
