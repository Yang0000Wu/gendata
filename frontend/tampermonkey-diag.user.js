// ==UserScript==
// @name         全局诊断
// @namespace    diag
// @version      3.0
// @description  所有网站自动记录点击、错误、跳转，跨站持久保存，一键导出报告
// @author       GenData
// @match        *://*/*
// @grant        GM_getValue
// @grant        GM_setValue
// @grant        unsafeWindow
// @run-at       document-end
// ==/UserScript==

(function(){
  'use strict';
  if (window.__diag_v3) return; window.__diag_v3 = true;

  var KEY = 'diag_v3_log';
  var log = GM_getValue(KEY, []);

  function save() { GM_setValue(KEY, log); }

  function add(tp, dt, sev) {
    log.push({ts:new Date().toISOString(), tp:tp, dt:String(dt).slice(0,300), sev:sev||'warn', url:location.href});
    save();
    refresh();
  }

  function refresh() {
    var e = document.getElementById('_dgv3');
    if (!e) return;
    var total = document.getElementById('_dgv3t');
    var crit = document.getElementById('_dgv3c');
    var list = document.getElementById('_dgv3r');
    if (total) total.textContent = log.length;
    if (crit) crit.textContent = log.filter(function(x){return x.sev==='crit';}).length;
    if (list) {
      var items = log.slice(-10).reverse();
      list.innerHTML = items.length
        ? items.map(function(x){
            var c = x.sev==='crit'?'#ef4444':x.sev==='warn'?'#f59e0b':'#94a3b8';
            return '<div style="padding:3px 0;border-bottom:1px solid #334155;font-size:11px">'+
              '<span style="color:'+c+';font-weight:600">['+x.sev+']</span> '+(x.tp||'')+'<br>'+
              '<span style="color:#64748b;font-size:10px">'+((x.dt||'').slice(0,60))+'</span></div>';
          }).join('')
        : '<div style="color:#475569;padding:6px;text-align:center;font-size:12px">暂无记录，操作页面后自动出现</div>';
    }
  }

  function exportLog() {
    var r = '===== 诊断报告 =====\n';
    r += '导出时间: '+new Date().toISOString()+'\n当前页面: '+location.href+'\n总记录: '+log.length+'条\n\n';
    var crits = log.filter(function(x){return x.sev==='crit';});
    if (crits.length) {
      r += '【严重问题 '+crits.length+'个】\n';
      crits.forEach(function(x,i){ r += (i+1)+'. ['+(x.ts||'').slice(11,19)+'] '+x.tp+'\n   '+x.dt+'\n   页面: '+x.url+'\n'; });
      r += '\n';
    }
    log.forEach(function(x,i){ r += (i+1)+'. ['+(x.ts||'').slice(11,19)+']['+x.sev+'] '+x.tp+'\n   '+x.dt+'\n'; });
    r += '\n===== 结束 =====';
    navigator.clipboard.writeText(r).then(function(){alert('✅ 报告已复制到剪贴板！');});
  }

  function clearLog() {
    if (!confirm('确认清空所有记录？')) return;
    log = []; save(); refresh();
    add('sys', '记录已清空', 'info');
  }

  function togglePanel() {
    var e = document.getElementById('_dgv3');
    if (e) { e.style.display = e.style.display === 'none' ? 'block' : 'none'; return; }

    e = document.createElement('div');
    e.id = '_dgv3';
    e.style.cssText = 'position:fixed;top:10px;right:10px;z-index:9999999;background:#0f172a;color:#e2e8f0;padding:14px;border-radius:12px;font-family:system-ui;width:240px;box-shadow:0 8px 40px rgba(0,0,0,0.8);border:2px solid #334155;font-size:13px';
    e.innerHTML =
      '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">'+
      '<span style="font-size:15px;font-weight:700;color:#fff">🩺 全局诊断</span>'+
      '<span style="background:#22c55e;color:#fff;font-size:10px;padding:2px 8px;border-radius:4px">● 记录中</span></div>'+

      '<div style="background:#1e293b;border-radius:8px;padding:8px;margin-bottom:8px;display:flex;gap:8px;text-align:center">'+
      '<div style="flex:1"><div style="font-size:22px;font-weight:700;color:#fff" id="_dgv3t">'+log.length+'</div><div style="font-size:10px;color:#64748b">总记录</div></div>'+
      '<div style="flex:1"><div style="font-size:22px;font-weight:700;color:#ef4444" id="_dgv3c">'+log.filter(function(x){return x.sev==='crit';}).length+'</div><div style="font-size:10px;color:#64748b">严重</div></div>'+
      '<div style="flex:1"><div style="font-size:22px;font-weight:700;color:#22c55e">'+(new Set(log.map(function(x){return x.url}))).size+'</div><div style="font-size:10px;color:#64748b">页面数</div></div></div>'+

      '<div style="margin-bottom:8px;color:#94a3b8;font-size:11px;display:flex;justify-content:space-between">'+
      '<span>📝 最近记录</span>'+
      '<span style="color:#475569">跨站永久保存</span></div>'+

      '<div id="_dgv3r" style="background:#0a0f1e;border-radius:6px;padding:6px;margin-bottom:8px;max-height:150px;overflow-y:auto;border:1px solid #1e293b"></div>'+

      '<div style="display:flex;gap:6px">'+
      '<button onclick="('+exportLog.toString()+')()" style="flex:1;padding:8px;border:none;border-radius:6px;background:#4a6cf7;color:#fff;cursor:pointer;font-size:12px;font-weight:600">📋 复制报告</button>'+
      '<button onclick="('+clearLog.toString()+')()" style="padding:8px 12px;border:none;border-radius:6px;background:#ef4444;color:#fff;cursor:pointer;font-size:12px">🗑</button>'+
      '<button onclick="document.getElementById(\'_dgv3\').style.display=\'none\'" style="padding:8px 12px;border:none;border-radius:6px;background:#374151;color:#94a3b8;cursor:pointer;font-size:12px">✕</button></div>'+

      '<div style="margin-top:6px;font-size:10px;color:#475569;text-align:center">💡 再点油猴图标可重新打开面板</div>';
    document.body.appendChild(e);
    refresh();
    add('sys', '面板已打开 - '+location.href, 'info');
  }

  // 自动显示面板
  togglePanel();

  // 监控
  window.addEventListener('error', function(e){
    var el = e.target;
    if (el && (el.tagName==='IMG'||el.tagName==='SCRIPT')) add('资源加载失败', el.src||el.href, 'crit');
    else add('JS错误', (e.message||'')+' at '+(e.filename||'')+':'+(e.lineno||''), 'crit');
  }, true);
  window.addEventListener('unhandledrejection', function(e){ add('Promise异常', String(e.reason||'').slice(0,200), 'crit'); });

  document.addEventListener('click', function(e){
    var el = e.target, txt = (el.innerText||el.value||'').replace(/\s+/g,' ').trim().slice(0,35), href = el.href||'';
    if (el.tagName==='A' && href && !href.startsWith('javascript:')) add('链接点击', '"'+txt+'" -> '+href, 'warn');
    else if (el.tagName==='BUTTON'||(el.tagName==='INPUT'&&el.type==='submit')) add('按钮点击', '"'+txt+'"', 'info');
    else add('点击', '<'+el.tagName+'> "'+txt+'"', 'info');
  }, true);

  setTimeout(function(){
    document.querySelectorAll('img').forEach(function(i){ if (!i.complete||i.naturalWidth===0) add('图片加载失败', i.src, 'crit'); });
    document.querySelectorAll('a').forEach(function(a){ if (a.href&&/undefined|null/.test(a.href)) add('链接含undefined', a.href, 'crit'); });
  }, 1500);

  console.log('🩺 全局诊断已启动');
  console.log('面板在页面右上角');
})();
