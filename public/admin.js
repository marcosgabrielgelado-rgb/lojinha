const $ = selector => document.querySelector(selector);
const $$ = selector => [...document.querySelectorAll(selector)];
let csrf = '';
let currentUser = '';
let allProducts = [];
let currentProductId = null;
let toastTimer = null;
const BRAND_OPTIONS = ['Nike','Adidas','Puma','New Balance','Vans','Asics','Reebok','Fila','Converse'];
const STATUS_OPTIONS = ['Novo','Em atendimento','Aguardando pagamento','Pago','Enviado','Entregue','Cancelado'];
const TITLES = {dashboard:'Visão geral',products:'Produtos',orders:'Pedidos',customers:'Clientes','settings':'Loja e aparência'};
const money = value => new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(Number(value||0));
const dateTime = value => { if(!value)return '—'; const d=new Date(value); return Number.isNaN(d.valueOf())?String(value):d.toLocaleString('pt-BR',{dateStyle:'short',timeStyle:'short'}); };
function escapeHTML(value){return String(value??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));}
function showToast(message, error=false){const el=$('#adminToast');el.textContent=message;el.classList.toggle('error',error);el.classList.add('show');clearTimeout(toastTimer);toastTimer=setTimeout(()=>el.classList.remove('show'),3500);}
async function api(url, options={}){
  const headers={...(options.headers||{})};
  if(options.body && !(options.body instanceof FormData) && !headers['Content-Type']) headers['Content-Type']='application/json';
  if(!['GET','HEAD'].includes((options.method||'GET').toUpperCase()) && !url.endsWith('/login') && csrf) headers['X-CSRF-Token']=csrf;
  const response=await fetch(url,{...options,headers,credentials:'same-origin'});
  let data={};try{data=await response.json()}catch{}
  if(!response.ok){if(response.status===401){showLogin('Sua sessão expirou. Entre novamente.',false);throw new Error(data.error||'Sessão expirada.')}throw new Error(data.error||'Não foi possível concluir a operação.')}
  return data;
}
function showLogin(message='', configured=true){
  $('#adminApp').classList.add('hidden');$('#loginView').classList.remove('hidden');
  $('#loginError').textContent=message;$('#setupNote').classList.toggle('hidden',configured);
  if(!configured)$('#loginError').textContent='A loja está pronta, mas o acesso administrativo ainda não foi configurado.';
}
function showApp(username){
  currentUser=username;$('#loginView').classList.add('hidden');$('#adminApp').classList.remove('hidden');
  $('#todayLabel').textContent=new Date().toLocaleDateString('pt-BR',{weekday:'short',day:'2-digit',month:'short',year:'numeric'});
  showView('dashboard');
}
async function boot(){
  try{const data=await fetch('/api/admin/me',{credentials:'same-origin'}).then(r=>r.json());
    if(data.authenticated){csrf=data.csrf;showApp(data.username)}else showLogin('',data.configured);
  }catch{showLogin('Não foi possível conectar ao servidor da loja.',false)}
}
$('#loginForm').addEventListener('submit',async e=>{
  e.preventDefault();const button=$('#loginButton');button.disabled=true;$('#loginError').textContent='';
  try{const result=await api('/api/admin/login',{method:'POST',body:JSON.stringify({username:$('#loginUsername').value.trim(),password:$('#loginPassword').value})});csrf=result.csrf;$('#loginPassword').value='';showApp(result.username);}
  catch(err){$('#loginError').textContent=err.message||'Falha ao entrar.'}
  finally{button.disabled=false;}
});
async function logout(){try{await api('/api/admin/logout',{method:'POST'});}catch{}csrf='';showLogin('',true);}
$('#logoutButton').addEventListener('click',logout);
$$('[data-view]').forEach(button=>button.addEventListener('click',()=>showView(button.dataset.view)));
async function showView(view){
  $$('.nav-item').forEach(btn=>btn.classList.toggle('active',btn.dataset.view===view));
  $('#pageTitle').textContent=TITLES[view]||'Painel';
  $('#adminView').innerHTML='<div class="loading-card">Carregando informações...</div>';
  try{
    if(view==='dashboard')await renderDashboard();
    if(view==='products')await renderProducts();
    if(view==='orders')await renderOrders();
    if(view==='customers')await renderCustomers();
    if(view==='settings')await renderSettings();
  }catch(err){$('#adminView').innerHTML=`<div class="empty-panel"><strong>Não foi possível abrir esta seção.</strong>${escapeHTML(err.message)}</div>`}
}
async function renderDashboard(){
 const d=await api('/api/admin/dashboard');const c=d.counts;
 $('#navProductCount').textContent=c.products;$('#navOrderCount').textContent=c.pending;
 $('#adminView').innerHTML=`<div class="view-heading"><div><h2>Resumo da operação ✦</h2><p>O que acontece na sua loja, sem ficar caçando dado em cinco lugares.</p></div><div class="toolbar"><button class="secondary-button" data-goto="orders">Ver pedidos ↗</button></div></div>
 <div class="stats-grid">
  <article class="stat-card"><div class="stat-top">FATURAMENTO CONFIRMADO <span class="stat-icon">R$</span></div><strong class="stat-value">${money(c.confirmedRevenue)}</strong><span class="stat-foot">Pedidos pagos, enviados ou entregues</span></article>
  <article class="stat-card"><div class="stat-top">PEDIDOS RECEBIDOS <span class="stat-icon">▤</span></div><strong class="stat-value">${c.orders}</strong><span class="stat-foot">${c.pending} aguardando acompanhamento</span></article>
  <article class="stat-card"><div class="stat-top">PRODUTOS VISÍVEIS <span class="stat-icon">👟</span></div><strong class="stat-value">${c.visibleProducts}<small style="font:700 13px 'Nunito Sans';color:#998ba5"> / ${c.products}</small></strong><span class="stat-foot">Itens disponíveis na vitrine</span></article>
  <article class="stat-card"><div class="stat-top">CLIENTES CADASTRADOS <span class="stat-icon">♙</span></div><strong class="stat-value">${c.customers}</strong><span class="stat-foot">Contatos que já fizeram pedido</span></article>
 </div>
 <div class="dashboard-grid"><section class="panel"><div class="panel-heading"><h3>Pedidos recentes</h3><button class="subtle-link" data-goto="orders">Todos os pedidos ↗</button></div><div class="table-wrap"><table class="data-table"><thead><tr><th>Pedido</th><th>Cliente</th><th>Data</th><th>Total</th><th>Status</th></tr></thead><tbody>${d.recentOrders.length?d.recentOrders.map(o=>`<tr><td><strong>${escapeHTML(o.number)}</strong></td><td>${escapeHTML(o.customer_name)}</td><td>${dateTime(o.created_at)}</td><td><strong>${money(o.total)}</strong></td><td>${statusPill(o.status)}</td></tr>`).join(''):'<tr><td colspan="5" class="empty-row">Ainda não chegaram pedidos.</td></tr>'}</tbody></table></div></section>
 <section class="panel"><div class="panel-heading"><h3>Mais vendidos</h3><span class="pill">Confirmados</span></div>${d.topProducts.length?`<div>${d.topProducts.map((p,i)=>`<div style="display:flex;gap:12px;align-items:center;padding:12px 0;border-bottom:1px solid #f3eff7"><span style="width:30px;height:30px;display:grid;place-items:center;background:#f1eaff;border-radius:10px;color:#6d28d9;font-weight:900">${i+1}</span><div style="flex:1;min-width:0"><strong style="display:block;font-size:12px">${escapeHTML(p.name)}</strong><small class="muted">${escapeHTML(p.brand)} · ${p.sold} pares</small></div><strong style="font-size:11px">${money(p.value)}</strong></div>`).join('')}</div>`:'<div class="empty-panel">Produtos vendidos aparecem aqui depois que você marcar os pedidos como pagos.</div>'}<p class="muted" style="font-size:10px;line-height:1.6;margin:15px 0 0">O faturamento confirmado considera somente pedidos com status Pago, Enviado ou Entregue. Pedido criado não é sinônimo de dinheiro recebido.</p></section></div>`;
 $$('[data-goto]').forEach(btn=>btn.addEventListener('click',()=>showView(btn.dataset.goto)));
}
function statusPill(status){const cl=['Pago','Enviado','Entregue'].includes(status)?'ok':['Novo','Em atendimento','Aguardando pagamento'].includes(status)?'warn':status==='Cancelado'?'bad':'';return `<span class="pill ${cl}">${escapeHTML(status)}</span>`}
async function renderProducts(){
 const data=await api('/api/admin/products');allProducts=data.products;$('#navProductCount').textContent=allProducts.length;
 $('#adminView').innerHTML=`<div class="view-heading"><div><h2>Catálogo de tênis</h2><p>Edite preços, fotos, tamanhos e disponibilidade da vitrine.</p></div><div class="toolbar"><a class="small-button" href="/api/admin/export/products" target="_blank">Exportar CSV ↓</a><button class="primary-button" id="newProductButton">＋ Novo produto</button></div></div>
 <div class="toolbar" style="margin-bottom:16px"><label class="search-field"><span>⌕</span><input id="productSearch" placeholder="Buscar por modelo ou marca"></label><select class="status-select" id="brandFilter"><option value="">Todas as marcas</option>${[...new Set(allProducts.map(p=>p.brand))].sort().map(b=>`<option>${escapeHTML(b)}</option>`).join('')}</select><select class="status-select" id="visibilityFilter"><option value="">Visíveis e ocultos</option><option value="visible">Somente visíveis</option><option value="hidden">Somente ocultos</option></select><span class="pill">${allProducts.length} itens</span></div>
 <div class="table-wrap"><table class="data-table"><thead><tr><th>Produto</th><th>Marca</th><th>Preço atual</th><th>Estoque</th><th>Visibilidade</th><th>Ações</th></tr></thead><tbody id="productRows"></tbody></table></div>
 <p class="muted" style="font-size:11px;line-height:1.6;margin-top:13px">O catálogo inicial tem nomes e preços ilustrativos e fotos de referência. Substitua por fotos correspondentes ao modelo exato, preços reais e estoque confirmado antes de divulgar.</p>`;
 const update=()=>{const q=$('#productSearch').value.trim().toLowerCase(),brand=$('#brandFilter').value,visibility=$('#visibilityFilter').value;const filtered=allProducts.filter(p=>(!brand||p.brand===brand)&&(!visibility||(visibility==='visible'?p.visible:!p.visible))&&[p.brand,p.name,p.description].join(' ').toLowerCase().includes(q));$('#productRows').innerHTML=filtered.length?filtered.map(p=>`<tr><td><div class="product-cell"><img class="product-thumb" src="${escapeHTML(p.image||'')}" alt="" onerror="this.style.visibility='hidden'"><div><div class="product-name">${escapeHTML(p.name)}</div><small class="muted">${escapeHTML(p.badge||'Sem selo')}</small></div></div></td><td>${escapeHTML(p.brand)}</td><td><strong>${money(p.price)}</strong>${p.oldPrice?`<div class="muted" style="font-size:10px;text-decoration:line-through">${money(p.oldPrice)}</div>`:''}</td><td>${p.stock} pares</td><td>${p.visible?'<span class="pill ok">Visível</span>':'<span class="pill">Oculto</span>'}</td><td><div class="row-actions"><button class="small-button" data-edit-product="${escapeHTML(p.id)}">Editar</button><button class="small-button danger" data-delete-product="${escapeHTML(p.id)}">Excluir</button></div></td></tr>`).join(''):'<tr><td colspan="6" class="empty-row">Nenhum produto corresponde ao filtro.</td></tr>'};
 update();$('#productSearch').addEventListener('input',update);$('#brandFilter').addEventListener('change',update);$('#visibilityFilter').addEventListener('change',update);$('#newProductButton').addEventListener('click',()=>openProductForm(null));
 $('#productRows').addEventListener('click',async e=>{const edit=e.target.closest('[data-edit-product]'),del=e.target.closest('[data-delete-product]');if(edit){openProductForm(allProducts.find(p=>p.id===edit.dataset.editProduct));return}if(del){const p=allProducts.find(p=>p.id===del.dataset.deleteProduct);if(!p||!confirm(`Excluir ${p.name}? O produto sairá do catálogo, mas os pedidos antigos mantêm seu histórico.`))return;try{await api('/api/admin/products/'+encodeURIComponent(p.id),{method:'DELETE'});showToast('Produto excluído.');await renderProducts()}catch(err){showToast(err.message,true)}}});
}
function openProductForm(product){
 currentProductId=product?.id||null;const form=$('#productForm');form.reset();$('#productFormError').textContent='';$('#productDialogTitle').textContent=product?'Editar produto':'Novo produto';$('#saveProductButton').textContent=product?'Salvar alterações':'Cadastrar produto';
 const fields=['name','brand','description','price','oldPrice','stock','sizes','image','badge','tone'];const values={name:product?.name||'',brand:product?.brand||'Nike',description:product?.description||'',price:product?.price??0,oldPrice:product?.oldPrice??'',stock:product?.stock??0,sizes:product?.sizes?.join(',')||'37,38,39,40,41,42,43',image:product?.image||'',badge:product?.badge||'',tone:product?.tone||'lilac'};
 for(const key of fields){const input=form.elements.namedItem(key);if(input)input.value=values[key]}
 form.elements.namedItem('visible').checked=product?product.visible:true;form.elements.namedItem('hot').checked=product?product.hot:false;form.elements.namedItem('photo').value='';$('#productDialog').showModal();
}
$('#closeProductDialog').addEventListener('click',()=>$('#productDialog').close());$('#cancelProductForm').addEventListener('click',()=>$('#productDialog').close());
$('#productForm').addEventListener('submit',async e=>{
 e.preventDefault();const form=e.currentTarget,button=$('#saveProductButton');button.disabled=true;$('#productFormError').textContent='';
 try{const fd=new FormData(form);let image=String(fd.get('image')||'').trim();const file=fd.get('photo');if(file&&file.size){const uploaded=await api('/api/admin/upload',{method:'POST',body:(()=>{const u=new FormData();u.append('image',file);return u})()});image=uploaded.url;}
 const sizes=String(fd.get('sizes')||'').split(',').map(s=>Number(s.trim())).filter(Boolean);const payload={name:fd.get('name'),brand:fd.get('brand'),description:fd.get('description'),price:Number(fd.get('price')),oldPrice:fd.get('oldPrice')===''?null:Number(fd.get('oldPrice')),stock:Number(fd.get('stock')),sizes,image,badge:fd.get('badge'),tone:fd.get('tone'),visible:form.elements.namedItem('visible').checked,hot:form.elements.namedItem('hot').checked};
 if(currentProductId)await api('/api/admin/products/'+encodeURIComponent(currentProductId),{method:'PUT',body:JSON.stringify(payload)});else await api('/api/admin/products',{method:'POST',body:JSON.stringify(payload)});
 $('#productDialog').close();showToast(currentProductId?'Produto atualizado.':'Produto cadastrado.');await renderProducts();
 }catch(err){$('#productFormError').textContent=err.message||'Não foi possível salvar.'}finally{button.disabled=false;}
});
async function renderOrders(){
 const data=await api('/api/admin/orders');$('#navOrderCount').textContent=data.orders.filter(o=>['Novo','Em atendimento','Aguardando pagamento'].includes(o.status)).length;
 $('#adminView').innerHTML=`<div class="view-heading"><div><h2>Pedidos da loja</h2><p>Pedidos ficam salvos no servidor e podem ser atualizados por aqui.</p></div><div class="toolbar"><a class="small-button" href="/api/admin/export/orders" target="_blank">Exportar CSV ↓</a></div></div><div class="toolbar" style="margin-bottom:15px"><label class="search-field"><span>⌕</span><input id="orderSearch" placeholder="Buscar pedido, cliente ou WhatsApp"></label><select id="orderStatusFilter" class="status-select"><option value="">Todos os status</option>${data.statuses.map(s=>`<option>${escapeHTML(s)}</option>`).join('')}</select></div><div class="table-wrap"><table class="data-table"><thead><tr><th>Pedido</th><th>Cliente / contato</th><th>Itens</th><th>Data</th><th>Total</th><th>Situação (editar)</th></tr></thead><tbody id="orderRows"></tbody></table></div>`;
 const update=()=>{const q=$('#orderSearch').value.toLowerCase().trim(),status=$('#orderStatusFilter').value;const filtered=data.orders.filter(o=>(!status||o.status===status)&&[o.number,o.customer_name,o.phone].join(' ').toLowerCase().includes(q));$('#orderRows').innerHTML=filtered.length?filtered.map(o=>`<tr><td><strong>${escapeHTML(o.number)}</strong><div class="muted" style="font-size:10px">${money(o.subtotal)} + frete ${money(o.shipping)}</div></td><td><strong>${escapeHTML(o.customer_name)}</strong><div class="muted">${escapeHTML(o.phone)}</div><details style="margin-top:5px"><summary class="subtle-link" style="cursor:pointer">Entrega e itens</summary><div style="min-width:180px;white-space:normal;line-height:1.6;padding:7px 0;font-size:11px">${escapeHTML(o.address)}, CEP ${escapeHTML(o.cep)}<br>Pagamento: ${escapeHTML(o.payment)}<br>${o.items.map(i=>`${i.qty}× ${escapeHTML(i.brand)} ${escapeHTML(i.product_name)} tam. ${i.size}`).join('<br>')}</div></details></td><td>${o.items.reduce((s,i)=>s+i.qty,0)} par(es)</td><td>${dateTime(o.created_at)}</td><td><strong>${money(o.total)}</strong>${o.discount?`<div class="muted" style="font-size:10px">Cupom −${money(o.discount)}</div>`:''}</td><td><select class="status-select" data-order-status="${o.id}">${data.statuses.map(s=>`<option ${s===o.status?'selected':''}>${escapeHTML(s)}</option>`).join('')}</select></td></tr>`).join(''):'<tr><td colspan="6" class="empty-row">Nenhum pedido neste filtro.</td></tr>'};
 update();$('#orderSearch').addEventListener('input',update);$('#orderStatusFilter').addEventListener('change',update);$('#orderRows').addEventListener('change',async e=>{const select=e.target.closest('[data-order-status]');if(!select)return;select.disabled=true;try{await api('/api/admin/orders/'+select.dataset.orderStatus,{method:'PATCH',body:JSON.stringify({status:select.value})});showToast('Situação do pedido atualizada.');await renderOrders()}catch(err){showToast(err.message,true);select.disabled=false}});
}
async function renderCustomers(){
 const data=await api('/api/admin/customers');$('#adminView').innerHTML=`<div class="view-heading"><div><h2>Clientes</h2><p>Contatos reunidos a partir dos pedidos recebidos.</p></div><span class="pill">${data.customers.length} clientes</span></div><label class="search-field" style="margin-bottom:15px"><span>⌕</span><input id="customerSearch" placeholder="Buscar por nome ou WhatsApp"></label><div class="table-wrap"><table class="data-table"><thead><tr><th>Cliente</th><th>WhatsApp</th><th>Endereço mais recente</th><th>Pedidos</th><th>Valor registrado</th><th>Último pedido</th></tr></thead><tbody id="customerRows"></tbody></table></div><p class="muted" style="font-size:11px;line-height:1.6;margin-top:12px">A lista contém dados pessoais usados para atender pedidos. Acesse apenas quando necessário e não compartilhe exportações publicamente.</p>`;
 const update=()=>{const q=$('#customerSearch').value.toLowerCase().trim(),filtered=data.customers.filter(c=>[c.name,c.phone,c.address,c.cep].join(' ').toLowerCase().includes(q));$('#customerRows').innerHTML=filtered.length?filtered.map(c=>`<tr><td><strong>${escapeHTML(c.name)}</strong></td><td>${escapeHTML(c.phone)}</td><td>${escapeHTML(c.address)}<div class="muted" style="font-size:10px">CEP ${escapeHTML(c.cep)}</div></td><td>${c.orders_count}</td><td><strong>${money(c.order_value)}</strong></td><td>${dateTime(c.last_order)}</td></tr>`).join(''):'<tr><td colspan="6" class="empty-row">Nenhum cliente encontrado.</td></tr>'};update();$('#customerSearch').addEventListener('input',update);
}
async function renderSettings(){
 const s=await api('/api/admin/settings');$('#adminView').innerHTML=`<div class="view-heading"><div><h2>Personalizar a loja</h2><p>Altere o texto da vitrine, contato comercial, cupom e frete.</p></div></div><div class="settings-layout"><form class="settings-form" id="settingsForm"><h3>Identidade da Magrão</h3><p class="section-note">Essas informações são salvas no banco de dados e refletem no site público depois de atualizar a página.</p><div class="field-grid">
 <label>Nome principal da marca<input name="store_name" value="${escapeHTML(s.store_name)}" maxlength="80" required></label><label>Frase do rodapé<input name="tagline" value="${escapeHTML(s.tagline)}" maxlength="250"></label><label class="full-span">Texto da faixa superior<input name="announcement" value="${escapeHTML(s.announcement)}" maxlength="160"></label><label class="full-span">Título principal da vitrine<textarea name="hero_title" rows="3" maxlength="300">${escapeHTML(s.hero_title)}</textarea><small>Use quebras de linha para dividir as linhas do título.</small></label><label class="full-span">Descrição principal<textarea name="hero_subtitle" rows="3" maxlength="350">${escapeHTML(s.hero_subtitle)}</textarea></label><label class="full-span">WhatsApp comercial<input name="whatsapp" inputmode="numeric" value="${escapeHTML(s.whatsapp)}" placeholder="5531999999999"><small>Inclua país + DDD + número, somente dígitos. O pedido abre uma conversa para confirmação.</small></label>
 <label>Código do cupom<input name="coupon_code" value="${escapeHTML(s.coupon_code)}" maxlength="30"></label><label>Desconto do cupom (%)<input name="coupon_percent" type="number" min="0" max="50" step="1" value="${escapeHTML(s.coupon_percent)}"></label><label>Frete grátis a partir de (R$)<input name="free_shipping_from" type="number" min="0" step="0.01" value="${escapeHTML(s.free_shipping_from)}"></label><label>Frete estimado (R$)<input name="shipping_estimate" type="number" min="0" step="0.01" value="${escapeHTML(s.shipping_estimate)}"></label></div><p id="settingsError" class="form-error"></p><button type="submit" class="primary-button" id="saveSettingsButton">Salvar configurações</button></form>
 <aside class="settings-aside"><span class="eyebrow">ANTES DE ABRIR AS PORTAS</span><h3>Deixa tudo redondo.</h3><p>O painel controla conteúdo e pedidos. Para começar a vender de verdade, ainda há alguns pontos comerciais que dependem dos dados da sua loja.</p><ul><li>Use fotos que correspondam ao modelo exato e que você possa publicar.</li><li>Confirme preços, estoque, frete e prazo de entrega.</li><li>Publique políticas de troca, devolução e privacidade.</li><li>Configure um provedor de pagamento seguro se quiser receber pelo site.</li><li>Faça backups periódicos do banco e das fotos enviadas.</li></ul><p style="border-top:1px solid #ffffff3b;padding-top:15px"><strong>Pagamento:</strong> no momento, o pedido é registrado para atendimento. Não há cobrança automática por cartão ou Pix.</p></aside></div>`;
 $('#settingsForm').addEventListener('submit',async e=>{e.preventDefault();const button=$('#saveSettingsButton'),fd=new FormData(e.currentTarget),payload=Object.fromEntries(fd.entries());button.disabled=true;$('#settingsError').textContent='';try{const result=await api('/api/admin/settings',{method:'PUT',body:JSON.stringify(payload)});showToast('Configurações salvas.');}catch(err){$('#settingsError').textContent=err.message}finally{button.disabled=false}});
}

boot();
