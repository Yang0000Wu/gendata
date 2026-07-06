(function(){
  try {
    var pid = '_dg';
    var ex = document.getElementById(pid);
    if (ex) { ex.style.display = ex.style.display === 'none' ? 'block' : 'none'; return; }

    var STORE_URL = 'http://124.221.149.20/diag-store.html';
    var iframe = null;
    var ready = false;
    var queue = [];
    var log = [];

    // 创建隐藏 iframe 作为跨站存储
    function initStore(cb) {
      if (iframe) { if (ready) cb(); return; }
      iframe = document.createElement('iframe');
      iframe.style.cssText = 'position:fixed;left:-9999px;top:-9999px;width:1px;height:1px;border:none';
      iframe.src = STORE_URL;
      document.body.appendChild(iframe);

      var loaded = false;
      function onMsg(e) {
        if (e.source !== iframe.contentWindow) return;
        if (e.data.cmd === 'ready') { ready = true; cb(); }
        else if (e.data.cmd === 'data') { log = e.data.data || []; up(); cb(); }
        else if (e.data.cmd === 'added' || e.data.cmd === 'counted') { /* ok */ }
      }
      window.addEventListener('message', onMsg);

      // 超时保护
      setTimeout(function() { if (!ready) { ready = true; cb(); } }, 2000);

      // 先获取已有数据
      setTimeout(function() {
        if (iframe && iframe.contentWindow) {
          iframe.contentWindow.postMessage({ cmd: 'get' }, '*');
        }
      }, 500);
    }

    function sendToStore(tp, dt, sev, url) {
      var msg = { cmd: 'add', tp: tp, dt: String(dt).slice(0,300), sev: sev||'warn', url: url||location.href };
      if (ready && iframe && iframe.contentWindow) {
        iframe.contentWindow.postMessage(msg, '*');
      } else {
        queue.push(msg);
      }
    }

    // 定期发送队列中的消息
    setInterval(function() {
      if (ready && iframe && iframe.contentWindow && queue.length) {
        queue.forEach(function(msg) { iframe.contentWindow.postMessage(msg, '*'); });
        queue = [];
      }
    }, 1000);

    function add(tp, dt, sev) {
      log.push({ tp: tp, dt: String(dt).slice(0,300), sev: sev||'warn', ts: new Date().toISOString(), url: location.href });
      up();
      sendToStore(tp, dt, sev);
    }

    function up() {
      ['t','c','r'].forEach(function(id) {
        var el = document.getElementById(pid + id);
        if (!el) return;
        if (id === 't') el.textContent = log.length;
        else if (id === 'c') el.textContent = log.filter(function(x){return x.sev==='crit';}).length;
        else if (id === 'r') {
          var items = log.slice(-8).reverse();
          el.innerHTML = items.length
            ? items.map(function(x) {
                var c = x.sev === 'crit' ? '#ef4444' : x.sev === 'warn' ? '#f59e0b' : '#94a3b8';
                return '<div style="padding:2px 0;border-bottom:1px solid #1e293b;font-size:10px">' +
                  '<span style="color:'+c+'">['+x.sev+']</span> '+(x.tp||'')+'<br>' +
                  '<span style="color:#475569">'+((x.dt||'').slice(0,50))+'</span></div>';
              }).join('')
            : '<div style="color:#475569;padding:4px;font-size:11px">暂无记录</div>';
        }
      });
    }

    function exp() {
      var r = '===== 诊断报告 =====\n';
      r += '时间:'+new Date().toISOString()+'\n页面:'+location.href+'\n总记录:'+log.length+'条\n\n';
      log.forEach(function(x,i){ r += (i+1)+'. ['+(x.ts||'').slice(11,19)+'] ['+x.sev+'] '+(x.tp||'')+'\n   '+(x.dt||'')+'\n   '+(x.url||'')+'\n'; });
      r += '\n===== 结束 =====';
      if (navigator.clipboard) { navigator.clipboard.writeText(r).then(function(){alert('已复制！');}); }
      else { prompt('复制报告:', r); }
    }

    // 创建面板
    var p = document.createElement('div');
    p.id = pid;
    p.style.cssText = 'position:fixed;top:8px;right:8px;z-index:9999999;background:#0f172a;color:#e2e8f0;padding:10px;border-radius:10px;font-family:system-ui;width:210px;box-shadow:0 4px 24px rgba(0,0,0,0.7);border:1px solid #1e293b;font-size:12px';
    p.innerHTML =
      '<div style="display:flex;justify-content:space-between;margin-bottom:4px">' +
      '<span style="font-weight:700;font-size:13px">\uD83D\uDC49 \u8DE8\u7AD9\u8BCA\u65AD</span>' +
      '<span style="color:#4ade80;font-size:10px">\u25CF</span></div>' +
      '<div style="font-size:10px;color:#64748b;margin-bottom:2px">\u8DE8\u7AD9\u8BB0\u5F55 \u00B7 \u8DF3\u8F6C\u4E0D\u4E22</div>' +
      '<div style="margin-bottom:4px;color:#94a3b8;font-size:11px">' +
      '\u5DF2\u8BB0\u5F55 <b id="'+pid+'t" style="color:#fff">0</b> \u4E2A\u00B7' +
      '\u4E25\u91CD <b id="'+pid+'c" style="color:#ef4444">0</b></div>' +
      '<div id="'+pid+'r" style="background:#0a0f1e;border-radius:4px;padding:4px;margin-bottom:4px;max-height:130px;overflow:auto"></div>' +
      '<div style="display:flex;gap:4px">' +
      '<button onclick="(function(){var d=document.getElementById(\''+pid+'\');d.style.display=\'none\'})()" style="flex:1;padding:4px;border:none;border-radius:4px;background:#374151;color:#aaa;cursor:pointer;font-size:11px">\u2715 \u9690\u85CF</button>' +
      '<button onclick="localStorage.removeItem(\'_dg_xlog\');location.reload()" style="padding:4px 8px;border:none;border-radius:4px;background:#ef4444;color:#fff;cursor:pointer;font-size:11px">\uD83D\uDDD1</button>' +
      '</div>' +
      '<div style="margin-top:4px"><button onclick="('+exp.toString().replace(/"/g,"'")+')()" style="width:100%;padding:5px;border:none;border-radius:4px;background:#4a6cf7;color:#fff;cursor:pointer;font-size:11px">\uD83D\uDCCB \u5BFC\u51FA\u62A5\u544A</button></div>';
    document.body.appendChild(p);

    // 初始化存储
    initStore(function() {
      add('sys', '\u76D1\u63A7\u5DF2\u542F\u52A8 - ' + location.href, 'info');
    });

    // 监控事件
    window.addEventListener('error', function(e) {
      var el = e.target;
      add(el&&(el.tagName==='IMG'||el.tagName==='SCRIPT')?'\u8D44\u6E90\u5931\u8D25':'JS\u9519\u8BEF', e.message||el.src||'', 'crit');
    }, true);

    document.addEventListener('click', function(e) {
      var el = e.target;
      var txt = (el.innerText||el.value||'').replace(/\s+/g,' ').trim().slice(0,35);
      var href = el.href||'';
      if (el.tagName === 'A' && href && !href.startsWith('javascript:')) {
        add('\u2192 \u94FE\u63A5', '"'+txt+'" -> '+href, 'warn');
      } else if (el.tagName === 'BUTTON'||(el.tagName==='INPUT'&&el.type==='submit')) {
        add('\u25B6 \u6309\u94AE', '"'+txt+'"', 'info');
      } else {
        add('\u70B9\u51FB', '<'+el.tagName+'> "'+txt+'"', 'info');
      }
    }, true);

    setTimeout(function() {
      document.querySelectorAll('img').forEach(function(img) {
        if (!img.complete||img.naturalWidth===0) add('\u56FE\u7247\u5931\u8D25', img.src, 'crit');
      });
    }, 1500);

    up();
  } catch(e) { alert('\u8BCA\u65AD\u9519\u8BEF: '+e.message); }
})();
