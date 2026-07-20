import { api, downloadFile, session } from './api.js';
import { emptyState, escapeHtml, formatDate, pageHeader, skeleton, statusBadge, toast } from './components.js';
import { bindHandwritingPage, handwritingPage } from './handwriting.js';
import {
  assistantPage, bindAssistantPage, bindHandwritingLivePage, bindHtpPage, bindSandplayPage,
  bindStudioHomePage, handwritingLivePage, htpPage, sandplayPage, studioHomePage
} from './studio.js';

const app = document.querySelector('#app');
let navCache = null;

const routes = {
  '/': studioHomePage,
  '/handwriting-live': handwritingLivePage,
  '/sandplay': sandplayPage,
  '/htp': htpPage,
  '/assistant': assistantPage,
  '/tasks': tasksPage,
  '/files': filesPage,
  '/profile': profilePage,
  '/integration': integrationPage,
  '/handwriting': handwritingPage,
  '/audit': auditPage,
};

function currentPath() {
  const raw = location.hash.replace(/^#/, '') || '/';
  return raw.startsWith('/') ? raw : `/${raw}`;
}

function hasPermission(code) {
  return Boolean(session.user?.permissions?.includes(code));
}

function setBusy(button, busy, text = '处理中…') {
  if (!button) return;
  if (busy) {
    button.dataset.originalText = button.textContent;
    button.textContent = text;
    button.disabled = true;
  } else {
    button.textContent = button.dataset.originalText || button.textContent;
    button.disabled = false;
  }
}

function showError(error) {
  const suffix = error?.requestId ? `（requestId: ${error.requestId}）` : '';
  toast(`${error?.message || '操作失败'}${suffix}`, 'error');
}

async function render() {
  if (!session.token) {
    navCache = null;
    renderLogin();
    return;
  }
  try {
    if (!navCache) navCache = await api('/navigation');
    const path = currentPath();
    const page = routes[path] || notFoundPage;
    app.innerHTML = shellHtml(path, '<div class="content">' + skeleton(6) + '</div>');
    bindShell();
    const content = await page();
    const target = document.querySelector('#page-content');
    if (target) target.innerHTML = content;
    bindPage(path);
  } catch (error) {
    if (!session.token) return renderLogin();
    app.innerHTML = shellHtml(currentPath(), `<div class="content"><div class="error-box">${escapeHtml(error.message)}${error.requestId ? `<br><span class="code">${escapeHtml(error.requestId)}</span>` : ''}</div></div>`);
    bindShell();
  }
}

function renderLogin() {
  app.innerHTML = `
    <main class="login-shell">
      <section class="login-brand">
        <div class="brand"><span class="brand-mark"></span>心迹AI</div>
        <h1>多模态心理辅助与智能陪伴平台</h1>
        <p>统一整合动态笔迹、心理沙盘、房树人、AI 陪伴、行动任务与公共数据底座。</p>
        <div class="scope-note"><strong>使用说明：</strong>所有分析仅用于客观观察和自我探索，不构成心理评估、人格判断或医学诊断。</div>
      </section>
      <section class="login-card-wrap">
        <form id="login-form" class="card login-card">
          <h2>登录演示环境</h2>
          <p class="muted">全部账号和数据均为比赛模拟数据。</p>
          <div class="notice">本系统不提供医学诊断，也不替代专业心理咨询或医疗服务。</div>
          <div class="form-grid">
            <div class="field"><label for="username">用户名</label><input id="username" name="username" autocomplete="username" value="student_demo" required maxlength="80"></div>
            <div class="field"><label for="password">密码</label><input id="password" name="password" type="password" autocomplete="current-password" value="demo123" required maxlength="128"></div>
            <button class="btn btn-primary" type="submit">登录</button>
          </div>
          <div class="demo-accounts">
            学生：student_demo / demo123<br>
            咨询师：counselor_demo / demo123<br>
            管理员：admin_demo / admin123
          </div>
        </form>
      </section>
    </main>`;
  document.querySelector('#login-form').addEventListener('submit', async event => {
    event.preventDefault();
    const button = event.submitter;
    setBusy(button, true, '登录中…');
    try {
      const form = new FormData(event.currentTarget);
      const result = await api('/auth/login', { method: 'POST', body: JSON.stringify({ username: form.get('username'), password: form.get('password') }) });
      session.token = result.accessToken;
      session.user = result.user;
      navCache = null;
      location.hash = '#/';
      await render();
    } catch (error) {
      showError(error);
      setBusy(button, false);
    }
  });
}

function shellHtml(path, content) {
  const productItems = [
    { path: '/', label: '综合首页' },
    { path: '/handwriting-live', label: '动态笔迹书写' },
    { path: '/handwriting', label: '轨迹分析报告' },
    { path: '/sandplay', label: '心理沙盘' },
    { path: '/htp', label: '房树人 HTP' },
    { path: '/assistant', label: 'AI陪伴助手' }
  ];
  const productNav = productItems.map(item => `<a class="${path === item.path ? 'active' : ''}" href="#${item.path}">${escapeHtml(item.label)}</a>`).join('');
  const nav = `<div class="nav-section-label">体验工作台</div>${productNav}`;
  const roles = (session.user?.roles || []).join(' / ');
  return `
    <div class="app-shell">
      <aside class="sidebar">
        <div class="brand"><span class="brand-mark"></span>心迹AI</div>
        <nav class="nav" aria-label="主导航">${nav}</nav>
        <div class="sidebar-foot">
          <div class="user-chip"><strong>${escapeHtml(session.user?.displayName)}</strong><br><span>${escapeHtml(roles)}</span></div>
          <button id="logout-btn" class="btn" type="button">退出登录</button>
        </div>
      </aside>
      <div class="main">
        <header class="topbar"><strong>心迹AI 综合工作台</strong><span class="muted">MindLine · v1.1.0</span></header>
        <main id="page-content">${content}</main>
      </div>
    </div>`;
}

function bindShell() {
  document.querySelector('#logout-btn')?.addEventListener('click', async () => {
    try { await api('/auth/logout', { method: 'POST' }); } catch { /* local cleanup still required */ }
    session.clear(); navCache = null; location.hash = '#/'; render();
  });
}

async function homePage() {
  const [modules, info, tasks, files] = await Promise.all([
    hasPermission('module:read') ? api('/modules') : [],
    api('/public/info'),
    hasPermission('task:read') ? api('/tasks') : [],
    hasPermission('file:read') ? api('/files') : [],
  ]);
  return `<div class="content">
    ${pageHeader('首页', `欢迎回来，${session.user?.displayName || ''}`)}
    <div class="scope-note"><strong>${escapeHtml(info.name)}</strong> · ${escapeHtml(info.scope)}<br>${escapeHtml(info.medicalDisclaimer)}</div>
    <div class="grid">
      <div class="card metric"><span class="muted">已注册模块</span><strong>${modules.length}</strong></div>
      <div class="card metric"><span class="muted">可见任务</span><strong>${tasks.length}</strong></div>
      <div class="card metric"><span class="muted">可见文件</span><strong>${files.length}</strong></div>
      <div class="card metric"><span class="muted">当前角色</span><strong style="font-size:1.1rem">${escapeHtml((session.user?.roles || []).join(' / '))}</strong></div>
    </div>
    <section class="section">
      <h2>三人模块集成状态</h2>
      <div class="grid">${modules.map(moduleCard).join('') || emptyState('暂无模块')}</div>
    </section>
    <section class="section card section-card">
      <h2>统一工程底座</h2>
      <p>公共框架 + 数据底座 + 苍穹适配 + 系统集成。HANDWRITING 归 A，MULTIMODAL_AGENT 归 B；这里只显示注册与健康状态。</p>
    </section>
  </div>`;
}

function moduleCard(m) {
  return `<article class="card module-card">
    <div class="inline"><h3>${escapeHtml(m.moduleName)}</h3>${statusBadge(m.status)}</div>
    <div class="module-meta">模块：<span class="code">${escapeHtml(m.moduleCode)}</span></div>
    <div class="module-meta">负责人：${escapeHtml(m.ownerCode)} · 契约 ${escapeHtml(m.contractVersion)}</div>
    <div class="module-meta">地址：${escapeHtml(m.baseUrl || '尚未配置')}</div>
  </article>`;
}

async function tasksPage() {
  const tasks = await api('/tasks');
  const create = hasPermission('task:write') ? '<button id="new-task-btn" class="btn btn-primary">创建通用任务</button>' : '';
  return `<div class="content">
    ${pageHeader('任务状态', '跨模块通用异步任务状态机；不包含 A/B 的算法实现。', create)}
    ${tasks.length ? `<div class="table-wrap"><table class="table"><thead><tr><th>标题</th><th>模块</th><th>类型</th><th>状态</th><th>进度</th><th>更新时间</th><th>操作</th></tr></thead><tbody>
      ${tasks.map(t => `<tr><td>${escapeHtml(t.title)}</td><td><span class="code">${escapeHtml(t.moduleCode)}</span></td><td>${escapeHtml(t.taskType)}</td><td>${statusBadge(t.status)}</td><td><div class="progress"><span style="width:${Number(t.progress) || 0}%"></span></div></td><td>${formatDate(t.updatedAt)}</td><td>${taskActions(t)}</td></tr>`).join('')}
    </tbody></table></div>` : emptyState('暂无任务', '可创建 COMMON、HANDWRITING 或 MULTIMODAL_AGENT 的通用任务记录。')}
  </div>`;
}

function taskActions(t) {
  if (!hasPermission('task:write')) return '-';
  const buttons = [];
  if (t.status === 'PENDING') buttons.push(`<button class="btn btn-small task-transition" data-id="${t.id}" data-status="RUNNING">开始</button>`);
  if (t.status === 'RUNNING') {
    buttons.push(`<button class="btn btn-small task-transition" data-id="${t.id}" data-status="SUCCEEDED">完成</button>`);
    buttons.push(`<button class="btn btn-small btn-danger task-transition" data-id="${t.id}" data-status="FAILED">失败</button>`);
  }
  if (['FAILED','CANCELLED'].includes(t.status)) buttons.push(`<button class="btn btn-small task-transition" data-id="${t.id}" data-status="PENDING">重试</button>`);
  return buttons.join(' ') || '-';
}

async function filesPage() {
  const files = await api('/files');
  return `<div class="content">
    ${pageHeader('文件中心', '公共文件对象、哈希、敏感级别与权限控制。')}
    ${hasPermission('file:write') ? `<form id="file-upload-form" class="file-drop"><input id="upload-file" name="file" type="file" required accept="image/png,image/jpeg,application/pdf,text/plain,application/json"><select name="moduleCode"><option>COMMON</option><option>HANDWRITING</option><option>MULTIMODAL_AGENT</option></select><select name="sensitivityLevel"><option>L1</option><option selected>L2</option><option>L3</option><option>L4</option></select><button class="btn btn-primary" type="submit">上传</button><p class="muted">演示环境允许 PNG/JPEG/PDF/TXT/JSON，单文件不超过 20MB。</p></form>` : ''}
    <section class="section">${files.length ? `<div class="table-wrap"><table class="table"><thead><tr><th>文件名</th><th>模块</th><th>类型</th><th>大小</th><th>级别</th><th>SHA-256</th><th>操作</th></tr></thead><tbody>${files.map(f => `<tr><td>${escapeHtml(f.originalName)}</td><td>${escapeHtml(f.moduleCode)}</td><td>${escapeHtml(f.contentType)}</td><td>${formatBytes(f.sizeBytes)}</td><td>${escapeHtml(f.sensitivityLevel)}</td><td><span class="code">${escapeHtml(f.sha256.slice(0,16))}…</span></td><td><button class="btn btn-small file-download" data-id="${f.id}" data-name="${escapeHtml(f.originalName)}">下载</button>${hasPermission('file:write') ? ` <button class="btn btn-small btn-danger file-delete" data-id="${f.id}">删除</button>` : ''}</td></tr>`).join('')}</tbody></table></div>` : emptyState('暂无文件')}</section>
  </div>`;
}

function formatBytes(value) {
  const n = Number(value) || 0;
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

async function profilePage() {
  const user = await api('/me');
  return `<div class="content">
    ${pageHeader('个人中心', '仅管理公共身份资料，不展示心理内容。')}
    <form id="profile-form" class="card section-card" style="max-width:680px">
      <div class="form-grid">
        <div class="field"><label>用户名</label><input value="${escapeHtml(user.username)}" disabled></div>
        <div class="field"><label>显示名称</label><input name="displayName" value="${escapeHtml(user.displayName)}" required maxlength="100"></div>
        <div class="field"><label>邮箱</label><input name="email" type="email" value="${escapeHtml(user.email || '')}" maxlength="180"></div>
        <div class="field"><label>角色</label><input value="${escapeHtml(user.roles.join(' / '))}" disabled></div>
        <button class="btn btn-primary" type="submit">保存</button>
      </div>
    </form>
  </div>`;
}

async function integrationPage() {
  const modules = await api('/modules');
  const canWrite = hasPermission('module:write');
  return `<div class="content">
    ${pageHeader('模块集成', '维护 A/B/C 模块注册信息，测试公共 AI 网关。', canWrite ? '<button id="edit-module-btn" class="btn btn-primary">配置模块</button>' : '')}
    <div class="grid">${modules.map(moduleCard).join('')}</div>
    <section class="section card section-card">
      <h2>Mock Agent 连通性测试</h2>
      <p class="muted">只验证超时、重试、幂等和日志，不实现 B 的 Agent 工作流。</p>
      <div class="inline"><select id="agent-operation"><option value="echo">echo</option><option value="health">health</option><option value="simulate-error">simulate-error</option><option value="simulate-timeout">simulate-timeout</option></select><button id="agent-test-btn" class="btn btn-primary">调用</button></div>
      <pre id="agent-result" class="code" style="display:block;white-space:pre-wrap;margin-top:14px"></pre>
    </section>
  </div>`;
}

async function auditPage() {
  const page = await api('/audit-logs?page=0&size=50');
  const rows = page.content || [];
  return `<div class="content">
    ${pageHeader('审计日志', '只记录必要元数据与摘要；密码、令牌和敏感正文不落日志。')}
    ${rows.length ? `<div class="table-wrap"><table class="table"><thead><tr><th>时间</th><th>操作者</th><th>动作</th><th>资源</th><th>结果</th><th>requestId</th></tr></thead><tbody>${rows.map(r => `<tr><td>${formatDate(r.occurredAt)}</td><td>${escapeHtml(r.actorUsername || '-')}</td><td>${escapeHtml(r.action)}</td><td>${escapeHtml(r.resourceType)} / ${escapeHtml(r.resourceId || '-')}</td><td>${statusBadge(r.result)}</td><td><span class="code">${escapeHtml(r.requestId || '-')}</span></td></tr>`).join('')}</tbody></table></div>` : emptyState('暂无审计日志')}
  </div>`;
}

async function notFoundPage() {
  return `<div class="content">${pageHeader('页面不存在', '请从左侧导航选择公共功能。')}${emptyState('404')}</div>`;
}

function bindPage(path) {
  if (path === '/') bindStudioHomePage();
  if (path === '/handwriting-live') bindHandwritingLivePage();
  if (path === '/sandplay') bindSandplayPage();
  if (path === '/htp') bindHtpPage();
  if (path === '/assistant') bindAssistantPage();
  if (path === '/tasks') bindTasks();
  if (path === '/files') bindFiles();
  if (path === '/profile') bindProfile();
  if (path === '/integration') bindIntegration();
  if (path === '/handwriting') bindHandwritingPage();
}

function bindTasks() {
  document.querySelector('#new-task-btn')?.addEventListener('click', () => openModal(`
    <h2>创建通用任务</h2><form id="new-task-form" class="form-grid">
      <div class="field"><label>模块</label><select name="moduleCode"><option>COMMON</option><option>HANDWRITING</option><option>MULTIMODAL_AGENT</option></select></div>
      <div class="field"><label>任务类型</label><input name="taskType" value="INTEGRATION_TEST" required maxlength="80"></div>
      <div class="field"><label>标题</label><input name="title" value="模块联调任务" required maxlength="180"></div>
      <div class="field"><label>请求引用</label><input name="requestRef" placeholder="可选，不放敏感正文" maxlength="200"></div>
      <div class="modal-actions"><button class="btn modal-close" type="button">取消</button><button class="btn btn-primary" type="submit">创建</button></div>
    </form>`, modal => {
      modal.querySelector('#new-task-form').addEventListener('submit', async event => {
        event.preventDefault(); const button = event.submitter; setBusy(button, true);
        try { const f = new FormData(event.currentTarget); await api('/tasks', { method: 'POST', body: JSON.stringify(Object.fromEntries(f)) }); closeModal(); toast('任务已创建','success'); render(); } catch (e) { showError(e); setBusy(button,false); }
      });
    }));
  document.querySelectorAll('.task-transition').forEach(button => button.addEventListener('click', async () => {
    setBusy(button,true);
    try { await api(`/tasks/${button.dataset.id}/status`, { method:'PATCH', body:JSON.stringify({status:button.dataset.status, progress:button.dataset.status==='RUNNING'?20:null}) }); toast('状态已更新','success'); render(); } catch(e){showError(e);setBusy(button,false);}
  }));
}

function bindFiles() {
  document.querySelector('#file-upload-form')?.addEventListener('submit', async event => {
    event.preventDefault(); const button=event.submitter; setBusy(button,true,'上传中…');
    try {
      const f=new FormData(event.currentTarget); const file=f.get('file'); const body=new FormData(); body.append('file',file);
      await api(`/files?moduleCode=${encodeURIComponent(f.get('moduleCode'))}&sensitivityLevel=${encodeURIComponent(f.get('sensitivityLevel'))}`,{method:'POST',body});
      toast('上传成功','success'); render();
    } catch(e){showError(e);setBusy(button,false);}
  });
  document.querySelectorAll('.file-download').forEach(button=>button.addEventListener('click',()=>downloadFile(button.dataset.id,button.dataset.name).catch(showError)));
  document.querySelectorAll('.file-delete').forEach(button=>button.addEventListener('click',async()=>{
    if(!confirm('确定删除该文件记录吗？')) return;
    try{await api(`/files/${button.dataset.id}`,{method:'DELETE'});toast('已删除','success');render();}catch(e){showError(e);}
  }));
}

function bindProfile() {
  document.querySelector('#profile-form')?.addEventListener('submit',async event=>{
    event.preventDefault();const button=event.submitter;setBusy(button,true);
    try{const f=new FormData(event.currentTarget);const user=await api('/me',{method:'PATCH',body:JSON.stringify(Object.fromEntries(f))});session.user=user;toast('已保存','success');navCache=null;render();}catch(e){showError(e);setBusy(button,false);}
  });
}

function bindIntegration() {
  document.querySelector('#edit-module-btn')?.addEventListener('click',()=>openModal(`
    <h2>配置模块注册</h2><form id="module-form" class="form-grid">
      <div class="field"><label>模块代码</label><select name="moduleCode"><option>HANDWRITING</option><option>MULTIMODAL_AGENT</option><option>COMMON</option></select></div>
      <div class="field"><label>模块名称</label><input name="moduleName" required maxlength="120"></div>
      <div class="field"><label>负责人</label><select name="ownerCode"><option>A</option><option>B</option><option>C</option></select></div>
      <div class="field"><label>Base URL</label><input name="baseUrl" placeholder="http://host:port" maxlength="500"></div>
      <div class="field"><label>健康检查路径</label><input name="healthPath" value="/health" maxlength="200"></div>
      <div class="field"><label>契约版本</label><input name="contractVersion" value="1.0.0" required maxlength="30"></div>
      <label><input type="checkbox" name="enabled" checked> 启用</label>
      <div class="modal-actions"><button class="btn modal-close" type="button">取消</button><button class="btn btn-primary" type="submit">保存</button></div>
    </form>`,modal=>modal.querySelector('#module-form').addEventListener('submit',async event=>{
      event.preventDefault();const button=event.submitter;setBusy(button,true);try{const f=new FormData(event.currentTarget);const moduleCode=f.get('moduleCode');const body=Object.fromEntries(f);body.enabled=f.get('enabled')==='on';delete body.moduleCode;await api(`/modules/${moduleCode}`,{method:'PUT',body:JSON.stringify(body)});closeModal();toast('模块配置已保存','success');render();}catch(e){showError(e);setBusy(button,false);}
    })));
  document.querySelector('#agent-test-btn')?.addEventListener('click',async event=>{
    const button=event.currentTarget;setBusy(button,true,'调用中…');const result=document.querySelector('#agent-result');result.textContent='';
    try{const operation=document.querySelector('#agent-operation').value;const data=await api('/ai/invoke',{method:'POST',headers:{'Idempotency-Key':crypto.randomUUID()},body:JSON.stringify({moduleCode:'COMMON',operation,input:{message:'C infrastructure check'},timeoutMs:5000})});result.textContent=JSON.stringify(data,null,2);toast('调用完成','success');}catch(e){result.textContent=`${e.code||'ERROR'}: ${e.message}`;showError(e);}finally{setBusy(button,false);}
  });
}

function openModal(html, onReady) {
  const backdrop=document.createElement('div');backdrop.className='modal-backdrop';backdrop.innerHTML=`<div class="modal" role="dialog" aria-modal="true">${html}</div>`;document.body.appendChild(backdrop);
  backdrop.addEventListener('click',event=>{if(event.target===backdrop)closeModal();});
  backdrop.querySelectorAll('.modal-close').forEach(button=>button.addEventListener('click',closeModal));
  onReady?.(backdrop);
}
function closeModal(){document.querySelector('.modal-backdrop')?.remove();}

window.addEventListener('hashchange', render);
render();
