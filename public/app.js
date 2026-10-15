/*
  MAGRÃO IMPORTS - protótipo de loja virtual
  Antes de vender de verdade:
  1) confira os produtos, preços, fotos, estoque, frete e políticas;
  2) configure CONFIG.whatsapp com país + DDD + número, só dígitos (ex.: 5531999999999);
  3) integre uma solução de pagamento e um backend se precisar registrar pedidos com segurança.
*/
const CONFIG = {
  whatsapp: "", // Ex.: "5531999999999". Deixe vazio para usar apenas o modo demonstrativo.
  currency: "BRL",
  couponCode: "MAGRAO10",
  couponPercent: 10,
  freeShippingFrom: 299,
  shippingEstimate: 19.90
};

let PRODUCTS = [];

const money = value => new Intl.NumberFormat("pt-BR", {style:"currency",currency:CONFIG.currency}).format(value);
const $ = selector => document.querySelector(selector);
const $$ = selector => [...document.querySelectorAll(selector)];
const state = {
  brand:"Todos", search:"", sort:"featured", selectedProduct:null, selectedSize:null,
  cart: readStorage("magraoCart", []), favorites: readStorage("magraoFavorites", []), couponApplied:false, selectedColors:{}
};
function readStorage(key,fallback){try{return JSON.parse(localStorage.getItem(key)) ?? fallback}catch{return fallback}}
function saveStorage(){localStorage.setItem("magraoCart",JSON.stringify(state.cart));localStorage.setItem("magraoFavorites",JSON.stringify(state.favorites))}
function escapeHTML(value){return String(value).replace(/[&<>"']/g,ch=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch]))}
function productById(id){return PRODUCTS.find(product=>product.id===id)}
function colorVariants(product){return (window.PRODUCT_COLOR_VARIANTS && window.PRODUCT_COLOR_VARIANTS[product?.id]) || []}
function selectedColorVariant(product){
  const variants=colorVariants(product);
  if(!variants.length)return null;
  return variants.find(v=>v.label===state.selectedColors[product.id]) || variants[0];
}
function variantForLabel(product,label){
  if(!label)return null;
  return colorVariants(product).find(v=>v.label===label) || null;
}
function setImageWithFallback(img,product,preferredSource){
  if(!img||!product)return;
  const rescueSources=(window.PRODUCT_IMAGE_FALLBACKS && window.PRODUCT_IMAGE_FALLBACKS[product.id]) || [];
  const sources=[preferredSource,product.image,...rescueSources,...colorVariants(product).map(v=>v.image)].filter(Boolean);
  img.__imageCandidates=[...new Set(sources)];
  img.__imageCandidateIndex=0;
  img.onerror=()=>{
    img.__imageCandidateIndex=(img.__imageCandidateIndex||0)+1;
    if(img.__imageCandidateIndex<img.__imageCandidates.length){img.src=img.__imageCandidates[img.__imageCandidateIndex];return;}
    img.onerror=null;img.src=fallbackImage(img.alt||product.name);
  };
  img.src=preferredSource||product.image||fallbackImage(product.name);
}
function updateCardColor(id,label){
  const product=productById(id);if(!product)return;
  const variant=variantForLabel(product,label);if(!variant)return;
  state.selectedColors[id]=variant.label;
  const card=document.querySelector(`.product-card[data-id="${CSS.escape(id)}"]`);if(!card)return;
  const img=card.querySelector(`[data-product-image="${CSS.escape(id)}"]`);
  if(img){img.alt=`${product.brand} ${product.name} - ${variant.label}`;setImageWithFallback(img,product,variant.image);}
  const labelNode=card.querySelector('[data-card-color-label]');if(labelNode)labelNode.textContent=variant.label;
  card.querySelectorAll('[data-card-color]').forEach(btn=>{
    const active=btn.dataset.cardColor===variant.label;
    btn.classList.toggle('selected',active);btn.setAttribute('aria-pressed',String(active));
  });
}
function renderModalColorSelector(product){
  const wrapper=$('#modalColorSelector');const variants=colorVariants(product);
  if(!wrapper)return;
  if(variants.length<2){wrapper.innerHTML='';wrapper.classList.add('hidden');return;}
  const current=selectedColorVariant(product);
  wrapper.classList.remove('hidden');
  wrapper.innerHTML=`<div class="modal-color-heading"><span>Cor</span><strong data-modal-color-label>${escapeHTML(current.label)}</strong></div><div class="color-swatch-list">${variants.map(v=>`<button type="button" class="color-swatch ${v.label===current.label?'selected':''}" data-modal-color="${escapeHTML(v.label)}" style="--swatch:${v.hex}" title="${escapeHTML(v.label)}" aria-label="Selecionar cor ${escapeHTML(v.label)}" aria-pressed="${v.label===current.label}"><span></span></button>`).join('')}</div>`;
}
function getCartCount(){return state.cart.reduce((sum,item)=>sum+item.qty,0)}
function getSubtotal(){return state.cart.reduce((sum,item)=>sum+(productById(item.id)?.price||0)*item.qty,0)}
function getDiscount(){return state.couponApplied?getSubtotal()*CONFIG.couponPercent/100:0}
function getShipping(){return getSubtotal()===0||getSubtotal()>=CONFIG.freeShippingFrom?0:CONFIG.shippingEstimate}
function getTotal(){return Math.max(0,getSubtotal()-getDiscount()+getShipping())}

function initializeProductImages(){
  $$('[data-product-image]').forEach(img=>{
    const product=productById(img.dataset.productImage);if(!product)return;
    const active=selectedColorVariant(product);
    setImageWithFallback(img,product,active?.image||product.image);
  });
}

function renderProducts(){
  let products=PRODUCTS.filter(product=>state.brand==="Todos"||product.brand===state.brand);
  if(state.search.trim()){
    const q=state.search.trim().toLowerCase();
    products=products.filter(p=>[p.brand,p.name,p.description].join(" ").toLowerCase().includes(q));
  }
  if(state.sort==="price-low")products.sort((a,b)=>a.price-b.price);
  if(state.sort==="price-high")products.sort((a,b)=>b.price-a.price);
  if(state.sort==="name")products.sort((a,b)=>a.name.localeCompare(b.name,"pt-BR"));
  const grid=$("#productGrid");
  grid.innerHTML=products.map(product=>{
    const variants=colorVariants(product), active=selectedColorVariant(product);
    const mainImage=active?.image||product.image;
    return `
    <article class="product-card" data-id="${product.id}">
      <div class="product-visual" data-open-product="${product.id}" role="button" tabindex="0" aria-label="Ver ${escapeHTML(product.name)}">
        <span class="product-badge ${product.hot?"hot":""}">${escapeHTML(product.badge||product.brand)}</span>
        <button class="favorite-button ${state.favorites.includes(product.id)?"favorited":""}" data-favorite="${product.id}" type="button" aria-label="${state.favorites.includes(product.id)?"Remover dos":"Adicionar aos"} favoritos">${state.favorites.includes(product.id)?"♥":"♡"}</button>
        <img src="${escapeHTML(mainImage)}" alt="${escapeHTML(product.brand+" "+product.name+(active?" - "+active.label:""))}" loading="lazy" data-product-image="${product.id}">
        <button class="quick-add" type="button" data-open-product="${product.id}" ${product.stock<=0?"disabled":""}>${product.stock<=0?"ESGOTADO":"ESCOLHER TAMANHO +"}</button>
      </div>
      <div class="product-info">
        <div class="product-meta"><span class="product-brand">${escapeHTML(product.brand)}</span><span class="product-rating">${product.stock<=0?"ESGOTADO":`TAM. ${product.sizes[0]}–${product.sizes[product.sizes.length-1]}`}</span></div>
        <h3 class="product-title" title="${escapeHTML(product.name)}">${escapeHTML(product.name)}</h3>
        <p class="product-description">${escapeHTML(product.description)}</p>
        ${variants.length>1?`<div class="card-colors"><div class="card-color-heading"><span>Cores</span><span data-card-color-label>${escapeHTML(active.label)}</span></div><div class="card-color-swatches">${variants.map(v=>`<button type="button" class="mini-color-swatch ${v.label===active.label?"selected":""}" data-card-color="${escapeHTML(v.label)}" data-card-product="${escapeHTML(product.id)}" style="--swatch:${v.hex}" title="${escapeHTML(v.label)}" aria-label="${escapeHTML(v.label)}" aria-pressed="${v.label===active.label}"><span></span></button>`).join("")}</div></div>`:""}
        <div class="price-row"><strong class="product-price">${money(product.price)}</strong>${product.oldPrice?`<span class="old-price">${money(product.oldPrice)}</span>`:""}<span class="price-hint">consulte condições</span></div>
        <button class="mobile-add" type="button" data-open-product="${product.id}" ${product.stock<=0?"disabled":""}>${product.stock<=0?"Esgotado":"Escolher tamanho +"}</button>
      </div>
    </article>`}).join("");
  $("#allCount").textContent=String(PRODUCTS.length).padStart(2,"0");
  $("#resultsCount").textContent=`${products.length} ${products.length===1?"produto":"produtos"}`;
  $("#emptyState").classList.toggle("hidden",products.length>0);
  initializeProductImages();
}
function fallbackImage(label){
  const title=escapeHTML(label).replace(/&/g,"and").slice(0,35);
  const svg=`<svg xmlns="http://www.w3.org/2000/svg" width="800" height="650" viewBox="0 0 800 650"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#eee4ff"/><stop offset="1" stop-color="#d3bbff"/></linearGradient></defs><rect width="800" height="650" fill="url(#g)"/><circle cx="400" cy="315" r="210" fill="#fff" opacity=".28"/><g transform="translate(120 175) rotate(-12 280 140)"><path d="M75 195 Q150 185 195 97 L262 123 Q294 182 395 189 L505 211 Q548 228 540 260 Q536 278 504 279 L104 279 Q55 279 56 244Z" fill="#fff" stroke="#8f63cb" stroke-width="10"/><path d="M190 118 L236 150 L270 161 M220 131 L262 163 L294 175 M248 145 L286 177 L314 186" fill="none" stroke="#8f63cb" stroke-width="10" stroke-linecap="round"/><path d="M66 246 Q282 270 537 250" fill="none" stroke="#b497df" stroke-width="12" stroke-linecap="round"/><path d="M100 280 L495 280" stroke="#6740a7" stroke-width="7" stroke-linecap="round"/></g><text x="400" y="560" font-family="Arial,sans-serif" font-size="22" font-weight="700" fill="#552091" text-anchor="middle">${title}</text></svg>`;
  return "data:image/svg+xml;charset=UTF-8,"+encodeURIComponent(svg);
}

function openProduct(id){
  const product=productById(id);if(!product)return;
  state.selectedProduct=id;state.selectedSize=null;
  $("#modalBrand").textContent=product.brand.toUpperCase();
  $("#modalProductName").textContent=product.name;
  $("#modalProductDescription").textContent=product.description+". Escolha seu tamanho antes de adicionar ao carrinho.";
  $("#modalProductPrice").textContent=money(product.price);
  $("#modalOldPrice").textContent=product.oldPrice?money(product.oldPrice):"";
  const image=$("#modalProductImage"),activeVariant=selectedColorVariant(product);image.alt=product.brand+" "+product.name+(activeVariant?" - "+activeVariant.label:"");setImageWithFallback(image,product,activeVariant?.image||product.image);
  renderModalColorSelector(product);
  $("#modalAddButton").disabled=product.stock<=0;$("#modalAddButton").textContent=product.stock<=0?"Produto esgotado":"Adicionar ao carrinho +";
  $("#sizeGrid").innerHTML=product.sizes.map(size=>`<button type="button" class="size-button" data-size="${size}" ${product.stock<=0?"disabled":""}>${size}</button>`).join("");
  $("#sizeError").classList.remove("visible");
  $("#productModal").classList.remove("hidden");showOverlay();
}
function addToCart(id,size){
  const product=productById(id);if(!product)return;
  const color=selectedColorVariant(product)?.label||"";
  const alreadyInCart=state.cart.filter(item=>item.id===id).reduce((sum,item)=>sum+item.qty,0);
  if(product.stock<=alreadyInCart){showToast(product.stock<=0?"Produto esgotado no momento.":`Temos ${product.stock} par(es) disponível(is) desse modelo.`);return;}
  const existing=state.cart.find(item=>item.id===id&&item.size===size&&(item.color||"")===color);
  if(existing)existing.qty++;else state.cart.push({id,size,qty:1,color});
  saveStorage();renderCart();closeModal("productModal");showToast(`${product.name}, tamanho ${size}, adicionado!`);
}
function renderCart(){
  $("#cartCount").textContent=getCartCount();
  const empty=state.cart.length===0;
  $("#cartEmpty").classList.toggle("hidden",!empty);$("#cartFooter").classList.toggle("hidden",empty);
  const items=$("#cartItems");items.innerHTML=state.cart.map(item=>{
    const p=productById(item.id);if(!p)return "";
    const chosenVariant=variantForLabel(p,item.color),cartImage=chosenVariant?.image||p.image;
    return `<article class="cart-line"><div class="cart-line-image"><img src="${escapeHTML(cartImage)}" alt="${escapeHTML(p.name+(item.color?" - "+item.color:""))}" data-cart-image="${p.id}" data-cart-color="${escapeHTML(item.color||"")}"></div><div class="cart-line-info"><small>${escapeHTML(p.brand)}</small><strong>${escapeHTML(p.name)}</strong>${item.color?`<span class="cart-color-label">Cor: ${escapeHTML(item.color)}</span>`:""}<span>Tamanho ${item.size} · ${money(p.price)} cada</span><div class="qty-control"><button type="button" data-qty="${p.id}|${item.size}|-1|${escapeHTML(item.color||"")}" aria-label="Diminuir quantidade">−</button><span>${item.qty}</span><button type="button" data-qty="${p.id}|${item.size}|1|${escapeHTML(item.color||"")}" aria-label="Aumentar quantidade">+</button></div></div><div class="cart-line-price">${money(p.price*item.qty)}<button class="cart-remove" type="button" data-remove="${p.id}|${item.size}|${escapeHTML(item.color||"")}" aria-label="Remover item">×</button></div></article>`;
  }).join("");
  $$('[data-cart-image]').forEach(img=>{
    const product=productById(img.dataset.cartImage);
    if(product)setImageWithFallback(img,product,img.src);
  });
  $("#subtotalValue").textContent=money(getSubtotal());
  $("#shippingValue").textContent=getShipping()===0?(getSubtotal()===0?"—":"Grátis"):money(getShipping());
  $("#discountLine").classList.toggle("hidden",!state.couponApplied);
  $("#discountValue").textContent="− "+money(getDiscount());
  $("#totalValue").textContent=money(getTotal());
  $("#couponFeedback").textContent=state.couponApplied?`Cupom aplicado: ${CONFIG.couponPercent}% de desconto.`:`Use ${CONFIG.couponCode} para testar ${CONFIG.couponPercent}% de desconto.`;
  $("#couponFeedback").classList.toggle("success",state.couponApplied);
}
function showOverlay(){
  $("#overlay").classList.remove("hidden");requestAnimationFrame(()=>$("#overlay").classList.add("visible"));document.body.classList.add("locked");
}
function openCart(){
  closeModal("productModal");closeModal("checkoutModal");closeModal("successModal");renderCart();$("#cartDrawer").classList.add("open");$("#cartDrawer").setAttribute("aria-hidden","false");showOverlay();
}
function closeCart(){
  $("#cartDrawer").classList.remove("open");$("#cartDrawer").setAttribute("aria-hidden","true");hideOverlayIfNothingOpen();
}
function closeModal(id){$("#"+id).classList.add("hidden");hideOverlayIfNothingOpen()}
function hideOverlayIfNothingOpen(){
  const anyOpen=$("#cartDrawer").classList.contains("open")||!["productModal","checkoutModal","successModal"].every(id=>$("#"+id).classList.contains("hidden"));
  if(!anyOpen){$("#overlay").classList.remove("visible");setTimeout(()=>$("#overlay").classList.add("hidden"),200);document.body.classList.remove("locked")}
}
function showToast(message){const toast=$("#toast");toast.textContent=message;toast.classList.add("show");clearTimeout(showToast.timeout);showToast.timeout=setTimeout(()=>toast.classList.remove("show"),2500)}
function openCheckout(){
  if(!state.cart.length){showToast("Seu carrinho ainda está vazio.");return}
  closeCart();const summary=state.cart.map(item=>{const p=productById(item.id);return `${item.qty}x ${escapeHTML(p.name)}${item.color?` · cor ${escapeHTML(item.color)}`:""} (tam. ${item.size})`}).join("<br>");
  $("#checkoutReview").innerHTML=`<strong>Resumo do pedido</strong><br>${summary}<br><strong>Total estimado: ${money(getTotal())}</strong><br><span>Frete ${getShipping()===0?"grátis":money(getShipping())}${state.couponApplied?` · cupom ${CONFIG.couponCode} aplicado`:""}.</span>`;
  $("#checkoutModal").classList.remove("hidden");showOverlay();
}
function setFilter(brand){state.brand=brand;$$('[data-brand]').forEach(button=>button.classList.toggle("active",button.classList.contains("filter-chip")&&button.dataset.brand===brand));renderProducts()}
function sendWhatsAppOrder(order,itemsText){
  if(!CONFIG.whatsapp)return "";
  const message=[`*PEDIDO MAGRÃO IMPORTS ${order.number}*`,`Cliente: ${order.customer.name}`,`WhatsApp: ${order.customer.phone}`,`Entrega: ${order.customer.address} - CEP ${order.customer.cep}`,`Pagamento: ${order.customer.payment}`,"","*Itens:",itemsText,"",`Subtotal: ${money(order.subtotal)}`,`Frete: ${order.shipping===0?"Grátis":money(order.shipping)}`,`Desconto: ${money(order.discount)}`,`*TOTAL ESTIMADO: ${money(order.total)}*`,"","Pedido gerado pelo site; confirmar estoque e pagamento com o cliente."].join("\n");
  const url=`https://wa.me/${CONFIG.whatsapp.replace(/\D/g,"")}?text=${encodeURIComponent(message)}`;
  return url;
}
async function handleOrderSubmit(event){
  event.preventDefault();
  const checkoutForm=event.currentTarget;
  const form=new FormData(checkoutForm);
  const submitButton=event.currentTarget.querySelector('button[type="submit"]');
  submitButton.disabled=true; submitButton.textContent="Registrando pedido…";
  try {
    const response=await fetch("/api/orders",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({customer:{name:form.get("name").trim(),phone:form.get("phone").trim(),address:form.get("address").trim(),cep:form.get("cep").trim(),payment:form.get("payment")},items:state.cart.map(item=>({id:item.id,size:item.size,qty:item.qty,color:item.color||""})),coupon:state.couponApplied?CONFIG.couponCode:""})});
    const result=await response.json();
    if(!response.ok) throw new Error(result.error||"Não foi possível registrar o pedido.");
    const order=result.order;
    const itemsText=order.items.map(item=>`• ${item.qty}x ${item.brand} ${item.product}${item.color?` | cor ${item.color}`:""} | tamanho ${item.size} | ${money(item.unitPrice*item.qty)}`).join("\n");
    const whatsappUrl=sendWhatsAppOrder(order,itemsText);
    const sent=Boolean(whatsappUrl);
    $("#successOrderNumber").textContent=order.number;
    $("#successMessage").textContent=sent?"Pedido registrado na loja. Use o botão abaixo para abrir o WhatsApp e enviar o resumo.":"Pedido registrado na loja. O pagamento ainda precisa ser combinado e confirmado.";
    $("#successConfigNote").innerHTML=sent?`<a class="button button-purple" style="display:inline-flex;margin-top:12px" href="${escapeHTML(whatsappUrl)}" target="_blank" rel="noopener noreferrer">Abrir WhatsApp e enviar pedido ↗</a><br><span style="display:inline-block;margin-top:10px">A venda só se conclui depois de confirmar estoque e pagamento.</span>`:"O pedido foi salvo no servidor e poderá ser consultado no painel administrativo. Nenhum pagamento foi cobrado.";
    state.cart=[];state.couponApplied=false;saveStorage();renderCart();
    try{const pr=await fetch("/api/products");if(pr.ok){PRODUCTS=(await pr.json()).products||PRODUCTS;renderProducts()}}catch{}
    $("#checkoutModal").classList.add("hidden");$("#successModal").classList.remove("hidden");showOverlay();checkoutForm.reset();
  } catch(error) { showToast(error.message||"Erro ao registrar pedido."); }
  finally { submitButton.disabled=false; submitButton.innerHTML='Gerar pedido <span>↗</span>'; }
}

// Catálogo e navegação
async function initStorefront(){
  $("#yearNow").textContent=new Date().getFullYear();
  try {
    const [productsResponse,settingsResponse]=await Promise.all([fetch("/api/products"),fetch("/api/settings")]);
    if(!productsResponse.ok) throw new Error("Não foi possível carregar o catálogo.");
    const productData=await productsResponse.json();
    PRODUCTS=productData.products||[];
    const settings=settingsResponse.ok?await settingsResponse.json():{};
    if(settings) applyStoreSettings(settings);
    state.cart=state.cart.filter(item=>PRODUCTS.some(p=>p.id===item.id));
    renderProducts();renderCart();
  } catch(error) {
    $("#productGrid").innerHTML='<p class="catalog-error">A vitrine não conseguiu carregar. Atualize a página em alguns segundos.</p>';
    console.error(error);
  }
}
function applyStoreSettings(settings){
  CONFIG.whatsapp=settings.whatsapp||"";
  CONFIG.couponCode=settings.coupon_code||CONFIG.couponCode;
  CONFIG.couponPercent=Number(settings.coupon_percent||CONFIG.couponPercent);
  CONFIG.freeShippingFrom=Number(settings.free_shipping_from||CONFIG.freeShippingFrom);
  CONFIG.shippingEstimate=Number(settings.shipping_estimate||CONFIG.shippingEstimate);
  if(settings.store_name){document.querySelectorAll(".brand-name").forEach(el=>{el.innerHTML=`${escapeHTML(settings.store_name)}<span>IMPORTS</span>`;});}
  if(settings.tagline){const el=$("#footerTagline");if(el)el.textContent=settings.tagline;}
  if(settings.hero_title){const el=$("#heroTitle");if(el)el.textContent=settings.hero_title;}
  if(settings.hero_subtitle){const el=$("#heroSubtitle");if(el)el.textContent=settings.hero_subtitle;}
  if(settings.announcement){const el=$("#announcementText");if(el)el.textContent=settings.announcement;}
}
initStorefront();
[ $(".hero-image"), $(".promo-banner > img") ].forEach(img=>img.addEventListener("error",()=>{img.src=fallbackImage(img.alt)}, {once:true}));
$("#searchInput").addEventListener("input",event=>{state.search=event.target.value;renderProducts()});
$("#sortSelect").addEventListener("change",event=>{state.sort=event.target.value;renderProducts()});
$("#filterRow").addEventListener("click",event=>{const button=event.target.closest("[data-brand]");if(button)setFilter(button.dataset.brand)});
$("#marcas").addEventListener("click",event=>{const button=event.target.closest("[data-brand]");if(button){setFilter(button.dataset.brand);$("#produtos").scrollIntoView({behavior:"smooth"})}});
$("#productGrid").addEventListener("click",event=>{
  const colorButton=event.target.closest("[data-card-color]");if(colorButton){event.preventDefault();event.stopPropagation();updateCardColor(colorButton.dataset.cardProduct,colorButton.dataset.cardColor);return}
  const favorite=event.target.closest("[data-favorite]");if(favorite){event.stopPropagation();const id=favorite.dataset.favorite;state.favorites=state.favorites.includes(id)?state.favorites.filter(value=>value!==id):[...state.favorites,id];localStorage.setItem("magraoFavorites",JSON.stringify(state.favorites));renderProducts();return}
  const open=event.target.closest("[data-open-product]");if(open)openProduct(open.dataset.openProduct);
});
$("#productGrid").addEventListener("keydown",event=>{if((event.key==="Enter"||event.key===" ")&&event.target.matches("[data-open-product][role=button]")){event.preventDefault();openProduct(event.target.dataset.openProduct)}});
$("#clearFilters").addEventListener("click",()=>{state.brand="Todos";state.search="";$("#searchInput").value="";setFilter("Todos")});
$("#sizeGrid").addEventListener("click",event=>{const btn=event.target.closest("[data-size]");if(!btn)return;state.selectedSize=Number(btn.dataset.size);$$('#sizeGrid .size-button').forEach(b=>b.classList.toggle("selected",b===btn));$("#sizeError").classList.remove("visible")});
$("#modalColorSelector").addEventListener("click",event=>{
  const btn=event.target.closest("[data-modal-color]");if(!btn||!state.selectedProduct)return;
  const product=productById(state.selectedProduct);if(!product)return;
  updateCardColor(product.id,btn.dataset.modalColor);
  const variant=selectedColorVariant(product),image=$("#modalProductImage");
  image.alt=product.brand+" "+product.name+" - "+variant.label;setImageWithFallback(image,product,variant.image);
  const label=$("#modalColorSelector [data-modal-color-label]");if(label)label.textContent=variant.label;
  $("#modalColorSelector").querySelectorAll("[data-modal-color]").forEach(b=>{const active=b.dataset.modalColor===variant.label;b.classList.toggle("selected",active);b.setAttribute("aria-pressed",String(active))});
});
$("#modalAddButton").addEventListener("click",()=>{if(!state.selectedSize){$("#sizeError").classList.add("visible");return}addToCart(state.selectedProduct,state.selectedSize)});
$("#openCart").addEventListener("click",openCart);$("#closeCart").addEventListener("click",closeCart);$("#continueShopping").addEventListener("click",()=>{closeCart();$("#produtos").scrollIntoView({behavior:"smooth"})});
$("#cartItems").addEventListener("click",event=>{
  const quantity=event.target.closest("[data-qty]");const remove=event.target.closest("[data-remove]");
  if(quantity){const [id,size,delta,...colorParts]=quantity.dataset.qty.split("|");const color=colorParts.join("|");const item=state.cart.find(entry=>entry.id===id&&entry.size===Number(size)&&(entry.color||"")===color);if(item){item.qty+=Number(delta);if(item.qty<=0)state.cart=state.cart.filter(entry=>entry!==item);saveStorage();renderCart()}}
  if(remove){const [id,size,...colorParts]=remove.dataset.remove.split("|");const color=colorParts.join("|");state.cart=state.cart.filter(item=>!(item.id===id&&item.size===Number(size)&&(item.color||"")===color));saveStorage();renderCart()}
});
$("#applyCoupon").addEventListener("click",()=>{const code=$("#couponInput").value.trim().toUpperCase();if(code===CONFIG.couponCode){state.couponApplied=true;renderCart();showToast("Cupom aplicado: 10% de desconto!")}else{state.couponApplied=false;renderCart();$("#couponFeedback").textContent="Cupom não reconhecido. Confira e tente de novo.";$("#couponFeedback").classList.remove("success")}});
$("#checkoutButton").addEventListener("click",openCheckout);$("#backToCart").addEventListener("click",()=>{closeModal("checkoutModal");openCart()});$("#checkoutForm").addEventListener("submit",handleOrderSubmit);
$$("[data-close-modal]").forEach(button=>button.addEventListener("click",()=>closeModal("productModal")));
$$("[data-close-checkout]").forEach(button=>button.addEventListener("click",()=>closeModal("checkoutModal")));
$$("[data-close-success]").forEach(button=>button.addEventListener("click",()=>closeModal("successModal")));
$("#finishOrder").addEventListener("click",()=>{closeModal("successModal");window.scrollTo({top:0,behavior:"smooth"})});
$("#overlay").addEventListener("click",()=>{closeCart();["productModal","checkoutModal","successModal"].forEach(closeModal)});
document.addEventListener("keydown",event=>{if(event.key==="Escape"){closeCart();["productModal","checkoutModal","successModal"].forEach(closeModal)}});
$("#newsletterForm").addEventListener("submit",event=>{event.preventDefault();$("#newsletterMessage").textContent="Cadastro demonstrativo concluído. A integração de e-mail ainda precisa ser configurada.";$("#newsletterEmail").value="";showToast("Cadastro demonstrativo registrado!")});
