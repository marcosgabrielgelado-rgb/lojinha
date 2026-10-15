from __future__ import annotations
import csv, io, json, os, re, secrets, sqlite3, unicodedata, uuid, urllib.request, urllib.error
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from flask import Flask, jsonify, request, session, redirect, send_from_directory, make_response
from dotenv import load_dotenv
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / '.env')
PUBLIC = ROOT / 'public'
INSTANCE = Path(os.getenv('INSTANCE_DIR', ROOT / 'instance'))
INSTANCE.mkdir(parents=True, exist_ok=True)
DATABASE = Path(os.getenv('DATABASE_PATH', INSTANCE / 'magrao.db'))
DATABASE.parent.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR = Path(os.getenv('UPLOAD_FOLDER', INSTANCE / 'uploads'))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__, static_folder=str(PUBLIC), static_url_path='')
app.config.update(
    SECRET_KEY=os.getenv('SECRET_KEY') or secrets.token_hex(32),
    MAX_CONTENT_LENGTH=5 * 1024 * 1024,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=os.getenv('COOKIE_SECURE', '0') == '1',
    PERMANENT_SESSION_LIFETIME=60 * 60 * 8,
)

STATUSES = ['Novo', 'Em atendimento', 'Aguardando pagamento', 'Pago', 'Enviado', 'Entregue', 'Cancelado']
ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}

# URLs são fotos de referência para o protótipo. Cada item pode receber a foto correta no painel.
IMAGE_POOL = [
 'https://images.unsplash.com/photo-1683860296392-23a70637d7ef?auto=format&fit=crop&w=950&q=85',
 'https://images.unsplash.com/photo-1695552836616-37fd42c5d8e9?auto=format&fit=crop&w=950&q=85',
 'https://images.unsplash.com/photo-1715003132895-b10a23d3c90f?auto=format&fit=crop&w=950&q=85',
 'https://vladimir.kedred.ru/wp-content/uploads/2021/05/krossovki-new-balance-x90-1.jpg',
 'https://images.complex.com/complex/image/upload/v1723871841/sanity-new/bz4xwf4occhoj4p1yxt3.jpg-135009534.jpg',
 'https://images.unsplash.com/photo-1718220095476-7916e897fc55?auto=format&fit=crop&w=950&q=85',
 'https://images.unsplash.com/photo-1738005162616-9413427ac64a?auto=format&fit=crop&w=950&q=85',
 'https://images.unsplash.com/photo-1663179046056-538a182cfa8a?auto=format&fit=crop&w=950&q=85',
]


# Fotos de referência mapeadas por modelo (marca + nome). URLs externas podem mudar;
# o painel administrativo continua permitindo trocar uma foto manualmente.
PRODUCT_IMAGE_URLS = {
    'nike-air-force-1-07': 'https://static.nike.com/a/images/t_web_pdp_535_v2/f_auto%2Cu_9ddf04c7-2a9a-4d76-add1-d15af8f0263d%2Cc_scale%2Cfl_relative%2Cw_1.0%2Ch_1.0%2Cfl_layer_apply/b7d9211c-26e7-431a-ac24-b0540fb3c00f/AIR%2BFORCE%2B1%2B%2707.png',
    'nike-dunk-low-retro': 'https://static.nike.com/a/images/t_PDP_1728_v1/f_auto%2Cq_auto%3Aeco%2Cc_scale%2Cw_300%2Cu_9ddf04c7-2a9a-4d76-add1-d15af8f0263d%2Cc_scale%2Cfl_relative%2Cw_1.0%2Ch_1.0%2Cfl_layer_apply/3f8c5b05-6d0f-49f4-b472-7425357e6a52/NIKE%2BDUNK%2BLOW%2BRETRO.png',
    'nike-air-max-90': 'https://www.nike.qa/dw/image/v2/BDVB_PRD/on/demandware.static/-/Sites-akeneo-master-catalog/default/dw8c0c32d1/nk/d0b/2/d/a/6/e/d0b2da6e_42a0_4328_9ea1_89e81c2281bb.jpg',
    'nike-air-max-97': 'https://images-beta.laced.com/products/05551e4f-88af-4e01-8703-a5d4a2ef6e06.jpg?width=3840',
    'nike-air-max-dn': 'https://statics.whentocop.fr/drops/6403/gallery/7D7F8A_Nike-Air-Max-Dn_WHITE-METALLIC-SILVER_DV3337-101_img0-1000x1000.webp',
    'nike-p-6000': 'https://www.crepslocker.com/cdn/shop/files/nike-p-6000-white-metallic-silver-black-cd6404-107-Side.webp?v=1749120515',
    'nike-v2k-run': 'https://cdn.shopify.com/s/files/1/0603/3031/1875/files/3_c299f4a1-9530-4943-9b5f-0e13cd639e18_3840x.jpg?=75&v=1772267968',
    'nike-cortez': 'https://imgnike-a.akamaihd.net/1300x1300/02884153A1.jpg',
    'nike-blazer-mid-77': 'https://intersportgrazure.lhscdn.com/uploads/resources/365432/cz1055-100-phsrh000-1500-huge.jpg?lm=6F9664D9568A7C96FFBB4D288DD9BC75',
    'nike-air-jordan-1-low': 'https://static.nike.com/a/images/t_PDP_1728_v1/f_auto%2Cq_auto%3Aeco%2Cc_scale%2Cw_300%2Cu_126ab356-44d8-4a06-89b4-fcdcc8df0245%2Cc_scale%2Cfl_relative%2Cw_1.0%2Ch_1.0%2Cfl_layer_apply/ab3ec819-7808-4cd8-ba1c-b1e9386c8540/AIR%2BJORDAN%2B1%2BLOW.png',
    'nike-air-jordan-1-mid': 'https://www.nike.ae/dw/image/v2/BDVB_PRD/on/demandware.static/-/Sites-akeneo-master-catalog/default/dw02708126/nk/0dd/e/9/9/4/6/0dde9946_f6fd_4a13_a149_1c2f11ca0b11.jpg',
    'nike-air-zoom-pegasus-41': 'https://static.nike.com/a/images/c_limit%2Ch_2500%2Cw_2500%2Cf_png/e0c9ffd0-607f-41c1-8c9b-8e10b8a3b6e7/image.png?a=1',
    'nike-vomero-5': 'https://www.nike.ae/dw/image/v2/BDVB_PRD/on/demandware.static/-/Sites-akeneo-master-catalog/default/dw85605c0d/nk/695/4/a/5/f/f/6954a5ff_a97a_4c4a_9303_53030aa63818.jpg?sh=2000&sm=fit&sw=2000',
    'nike-court-vision-low': 'https://cdn-product.stadium.com/eb200337-aa76-4ae2-a7e3-75cfa1116b37/6a6120ac-a953-455e-8ce8-eb67bd84b6ee/30o3exy5iRIvUHPMvbfm3Qhcf/3B8g9wHl5DRSvWs6Dy7xAWdKN.png?f=webp&h=2000&targetFileName=352033_103_d2.webp&w=2000',
    'nike-reactx-infinity-run': 'https://static.nike.com/a/images/t_PDP_1728_v1/f_auto%2Cq_auto%3Aeco%2Cc_scale%2Cw_300%2Cu_9ddf04c7-2a9a-4d76-add1-d15af8f0263d%2Cc_scale%2Cfl_relative%2Cw_1.0%2Ch_1.0%2Cfl_layer_apply/083db8cd-ef0f-4fbb-9fbf-9da0be98f802/NIKE%2BREACTX%2BINFINITY%2BRUN%2B4.png',
    'adidas-samba-og': 'https://assets.adidas.com/images/w_500%2Cf_auto%2Cq_auto/1b91804db204496b9783a6ee5b37a525_9366/Tenis_Samba_OG_Branco_KK2277_01_00_standard.jpg',
    'adidas-gazelle-indoor': 'https://static.ftshp.digital/img/p/1/0/0/8/3/6/7/1008367.jpg',
    'adidas-campus-00s': 'https://assets.adidas.com/images/w_500%2Cf_auto%2Cq_auto/475f293b99c74963aca7b77bbf55893a_9366/Tenis_Campus_00s_Preto_JK3370_01_00_standard.jpg',
    'adidas-handball-spezial': 'https://assets.adidas.com/images/w_600%2Cf_auto%2Cq_auto/237264d18bb14f108f80e83ba4644ffb_9366/Handball_Spezial_Shoes_Grey_IF7086_01_standard.jpg',
    'adidas-superstar-ii': 'https://assets.adidas.com/images/w_940%2Cf_auto%2Cq_auto/9817183346704f8f9c55b52dc9b71929_9366/IH8659_04_standard.jpg',
    'adidas-forum-low': 'https://assets.adidas.com/images/h_2000%2Cf_auto%2Cq_auto%2Cfl_lossy%2Cc_fill%2Cg_auto/2622b6525fae4d349bb6af9e002ee277_9366/Forum_Low_Shoes_White_IF2733_01_standard.jpg',
    'adidas-stan-smith': 'https://assets.adidas.com/images/w_600%2Cf_auto%2Cq_auto/db0ea48a69aa469c9024dc4e6a622b1a_faec/Stan_Smith_Shoes_White_ID0268_db04_standard.jpg',
    'adidas-ultraboost-5': 'https://www.misterrunning.com/images/2024-media-05/id8813_A.jpg',
    'adidas-supernova-rise': 'https://www.lepape.com/media/catalog/product/cache/473b5c523945596881637071664ad3a7/m/a/main_ID3588_b2b012_plp_2a54.png',
    'adidas-adizero-sl2': 'https://assets.adidas.com/images/w_1880%2Cf_auto%2Cq_auto/89a033dc5b034460b72af5de78ebe4bf_9366/JQ3124_09_standard.jpg',
    'adidas-response-cl': 'https://assets.adidas.com/images/w_600%2Cf_auto%2Cq_auto/3ffd676634914212909faf5d00bbc328_faec/Response_CL_Shoes_Grey_ID4290_db01_standard.jpg',
    'adidas-ozweego': 'https://assets.adidas.com/images/w_1880%2Cf_auto%2Cq_auto/d8ceea3711cc44519b2eaa7600ff47e8_9366/EE6464_04_standard.jpg',
    'adidas-zx-22-boost': 'https://resources.mandmdirect.com/Images/_default/a/o/3/ao34500_1_cloudzoom.jpg',
    'adidas-grand-court-2-0': 'https://cdn-product.stadium.com/eb200337-aa76-4ae2-a7e3-75cfa1116b37/76cdf66c-9786-48bb-9334-6235c3b21923/WgQyPLC2lzaDJBqPgKwU1bGLJ/r5zDnwlXHU7e3ho8ugIDtATEV.png?f=webp&h=2000&targetFileName=703936_102.webp&w=2000',
    'adidas-adistar-3': 'https://assets.adidas.com/images/w_1880%2Cf_auto%2Cq_auto/2ba2c7e36ac64288b889cc967facdf7b_9366/ID6162_01_00_standard.jpg',
    'puma-speedcat-og': 'https://images.puma.com/image/upload/f_auto%2Cq_auto%2Cb_rgb%3Afafafa%2Cw_600%2Ch_600/global/398846/01/sv01/fnd/PNA/fmt/png/Speedcat-OG-Sneakers',
    'puma-suede-classic': 'https://www.monpiedceheros.fr/57019-verylarge_default/puma-suede-classic.jpg',
    'puma-palermo': 'https://images.puma.net/images/396463/63/sv01/fnd/BRA/w/2000/h/2000/',
    'puma-rs-x-reinvention': 'https://images.puma.com/image/upload/f_auto%2Cq_auto%2Cb_rgb%3Afafafa%2Ce_sharpen/global/369579/28/w/1000/h/1000/fnd/TUR/fmt/png',
    'puma-ca-pro-classic': 'https://backwash.fbitsstatic.net/img/p/tenis-puma-ca-pro-classic-branco-96538/362383-4.jpg?h=800&qs=ignore&v=no-change&w=800',
    'puma-future-rider': 'https://images.puma.com/image/upload/f_auto%2Cq_auto%2Cb_rgb%3Afafafa%2Cw_2000%2Ch_2000/global/380639/02/sv01/fnd/SEA/fmt/png/Future-Rider-Double-Trainers',
    'puma-slipstream-lo': 'https://image.goat.com/transform/v1/attachments/product_template_pictures/images/084/616/699/original/393223_01.png.png?background=255%2C255%2C255&type=webp',
    'puma-caven-2-0': 'https://www.sportvision.mk/files/thumbs/files/images/slike_proizvoda/media/392/392290-02/images/thumbs_1200/392290-02_1_1200_1200px.jpg',
    'puma-velocity-nitro-3': 'https://startfitness.co.uk/cdn/shop/files/Puma-Velocity-Nitro-3-380080-01.jpg?v=1705927304&width=1920',
    'puma-deviate-nitro-3': 'https://cdn.evrysz.net/1000x1000/34/puma-deviate-nitro-3-30970715.png',
    'puma-softride-enzo': 'https://images.puma.com/image/upload/f_auto%2Cq_auto%2Cb_rgb%3Afafafa/global/311098/02/sv01/fnd/UKR/w/1000/h/1000/fmt/png',
    'puma-axelion': 'https://planetasport.rs/media/catalog/product/cache/730df358d17d054d41286016a848c691/3/7/377911-01_1.jpg?v=b763bc02d2',
    'puma-pacer-future': 'https://2app.kicksonfire.com/kofapp/upload/events_master_images/ipad_puma-pacer-future-black.png',
    'puma-rbd-game-low': 'https://images.puma.net/images/386373/02/sv01/fnd/KSA/',
    'puma-tackle': 'https://images.puma.com/image/upload/f_auto%2Cq_auto%2Cb_rgb%3Afafafa%2Cw_2000%2Ch_2000/global/404456/05/sv01/fnd/IDN/fmt/png/PUMA-Tackle-Sneakers-Unisex',
    'new-balance-9060': 'https://kanadadankapina.com/cdn/shop/files/IMG-7126.webp?v=1708125443',
    'new-balance-2002r': 'https://fimsbury.com/17099-superlarge_default/m2002-grey.jpg',
    'new-balance-530': 'https://newbrasil.vtexassets.com/arquivos/ids/228382-3840-auto/NB530_U53017S_00.webp?quality=10&v=639225687270070000',
    'new-balance-550': 'https://cdn.grupoelcorteingles.es/SGFM/dctm/MEDIA03/202410/01/00182869624104____20__1200x1200.jpg',
    'new-balance-574-core': 'https://image-raw.reversible.com/raw_images/8438972142c2c081b71d98debdf90e9b9cf03cf93bb21a9e3ee6a5f7fff3d383',
    'new-balance-1906r': 'https://www.newbalance.pt/dw/image/v2/AASY_PRD/on/demandware.static/-/Library-Sites-NBUK-NBEU/default/dwecc3823a/Bestseller%20strip%20-%20homepage/m1906ree_nb_02_i.jpg',
    'new-balance-327': 'https://imagedelivery.net/2DfovxNet9Syc-4xYpcsGg/f8bc4cb2-2eeb-487f-959a-f828e62dbc00/product',
    'new-balance-990v6': 'https://newbalance.ua/img/photos/photo44947.jpg',
    'new-balance-991v2': 'https://www.consortium.co.uk/media/catalog/product/cache/1/image/040ec09b1e35df139433887a97daa66f/n/e/new-balance-991v2-made-in-uk-dove-alloy-silver-u991gl2_0000_cat.jpg',
    'new-balance-860v2': 'https://newbalance.ua/img/photos/d14d8be70b32c820f39a97ba6c91ede7.jpg',
    'new-balance-1000': 'https://nb.scene7.com/is/image/NB/m1000te_nb_02_i?%24dw_detail_main_lg%24=&bgc=f1f1f1&bgcolor=f1f1f1&blendMode=mult&hei=1600&layer=1&scale=10&wid=1600',
    'new-balance-480': 'https://nb.scene7.com/is/image/NB/bb480lgm_nb_02_i?%24dw_detail_main_lg%24=&bgc=f1f1f1&bgcolor=f1f1f1&blendMode=mult&hei=1600&layer=1&scale=10&wid=1600',
    'new-balance-fresh-foam-x-1080v14': 'https://www.run4it.com/cdn/shop/files/M1080C14-M-NewBalance-FreshFoamX1080V14-lateral-view.jpg?v=1738087712',
    'new-balance-725': 'https://newbalance.ua/img/photos/photo39109.jpg',
    'new-balance-608v5': 'https://michelsonshoes.com/media/catalog/product/cache/b946126271a550b31ba79bcf948cb6d9/rdi/rdi/mens-new-balance-608v5-white-with-navy-mx608wn_1.jpg',
    'vans-old-skool': 'https://secure-static.vans.com.br/medias/sys_master/vans/vans/hdc/ha7/h00/h00/12898471903262/Midres-Vans-V1002001070011-01.jpg?q=100&w=1920',
    'vans-knu-skool': 'https://espacocon.fbitsstatic.net/img/p/tenis-vans-knu-skool-black-true-white-vn0009qc6bt-152946/371611-2.jpg?h=1200&v=no-value&w=1200',
    'vans-authentic': 'https://images.tcdn.com.br/img/img_prod/473150/tenis_vans_authentic_branco_1724_2_20190301193513.png',
    'vans-era': 'https://acdn.mitiendanube.com/stores/004/350/808/products/tenis-vans-era-true-white-vans-1-65ea88f204222258c817101671763220-640-0.jpg',
    'vans-sk8-hi': 'https://f.fcdn.app/imgs/a26570/www.inboxstore.com.uy/inbouy/084c/original/catalogo/VN000D5IB8C_6742_1/2000-2000/championes-vans-sk8-hi-negro.jpg',
    'vans-slip-on-checkerboard': 'https://content.backcountry.com/images/items/1200/VAN/VAN00TL/BKANWHCH.jpg',
    'vans-ultrarange-neo-vr3': 'https://http2.mlstatic.com/D_NQ_NP_640963-MLB111758496916_062026-O-tnis-vans-ultrarange-vr3-neo-preto-azul-branco-34-ao-43.webp',
    'vans-skate-old-skool': 'https://cdn.shoplightspeed.com/shops/645344/files/35890813/950x950x2/vans-skate-old-skool-black-white.jpg',
    'vans-half-cab': 'https://www.daddiesboardshop.com/cdn/shop/products/194901610212-1_1280x.jpg?v=1624039260',
    'vans-old-skool-stackform': 'https://cdn.shoplightspeed.com/shops/613683/files/52538651/old-skool-stackform-true-white-vsp2wmo-vn0a7q5mw00.jpg',
    'vans-cruze-too': 'https://www.tradeinn.com/f/13957/139579641/vans-chaussures-cruze-too-cc.jpg',
    'vans-lowland-cc': 'https://cdn.shopify.com/s/files/1/0187/5180/products/ONENESS_0020_VANS-LOWLAND-CC-JMP-R-COURT-GREEN_WHITE-VN0007P2Y9H_1445x.jpg?v=1676576214',
    'vans-sport-low': 'https://i.ebayimg.com/images/g/rK8AAOSw8mhl9sLz/s-l1200.jpg',
    'vans-authentic-stackform': 'https://i5-mx.walmartimages.com/mg/gm/3pp/asr/8f5b91ca-4826-473f-b7c1-507a3f66f811.ed505bd306acd6c76a5a0fb2595e5fd5.jpeg?odnBg=ffffff&odnHeight=2000&odnWidth=2000',
    'vans-hylane': 'https://fun-sport-vision.com/media/image/eb/91/7b/van_hylane_vn000d819x1_black_white_gum_01_gross2uZqaK7cAivrq.jpg',
}


# Atualiza URLs padrão antigas somente quando ainda estão no produto.
# Uma imagem personalizada pelo administrador nunca é sobrescrita.
PRODUCT_COLOR_OPTIONS = {
    'nike-air-force-1-07': {'Branco/Branco', 'Branco/Azul Royal', 'Preto/Branco'},
    'nike-dunk-low-retro': {'Verde Mica/Off-white', 'Branco/Cinza Grey Fog'},
    'nike-air-max-90': {'Branco/Cinza/Verde Neon', 'Preto/Cinza/Rosa Neon'},
    'nike-air-max-97': {'Preto/Prata Metálico', 'Branco/Prata Metálico'},
    'nike-air-max-dn': {'Branco/Prata Metálico', 'Preto/Vermelho University'},
    'nike-p-6000': {'Branco/Prata/Preto', 'Preto/Prata'},
    'nike-cortez': {'Branco/Vermelho/Gum', 'Branco/Preto'},
    'nike-air-zoom-pegasus-41': {'Preto/Branco', 'Azul/Royal/Branco'},
    'nike-vomero-5': {'Preto/Prata', 'Branco/Prata Metálico'},
    'adidas-samba-og': {'Creme/Verde/Gum', 'Preto/Verde/Creme', 'Verde/Creme/Gum', 'Verde Collegiate/Branco/Gum'},
    'adidas-gazelle-indoor': {'Azul Marinho/Off-white/Gum', 'Azul/Branco/Gum'},
    'adidas-campus-00s': {'Preto/Branco/Off-white', 'Cinza/Prata/Preto', 'Preto/Branco/Rosa', 'Cinza/Goma'},
    'adidas-handball-spezial': {'Cinza/Branco/Gum', 'Azul Marinho/Branco/Gum'},
    'adidas-superstar-ii': {'Branco/Preto/Off-white', 'Preto/Branco'},
    'adidas-supernova-rise': {'Preto/Branco', 'Branco/Azul/Aqua'},
    'adidas-grand-court-2-0': {'Preto/Branco', 'Branco/Preto'},
    'puma-speedcat-og': {'Preto/Branco', 'Vermelho/Branco', 'Cinza/Branco', 'Rosa/Branco'},
    'puma-suede-classic': {'Preto/Branco', 'Azul Olimpião/Branco'},
    'puma-palermo': {'Verde/Branco/Gum', 'Branco/Preto/Gum'},
    'new-balance-530': {'Branco/Prata', 'Bege Claro/Marinho', 'Preto/Branco', 'Bege'},
    'new-balance-9060': {'Preto/Branco', 'Branco/Off-white/Prata'},
    'new-balance-1000': {'Preto/Prata Metálico', 'Prata/Branco'},
    'new-balance-550': {'Preto/Branco', 'Branco/Verde'},
    'new-balance-991v2': {'Preto/Cinza', 'Cinza/Prata'},
    'new-balance-327': {'Preto/Branco', 'Branco/Verde'},
    'new-balance-725': {'Preto/Bege', 'Branco/Prata/Cinza'},
    'vans-old-skool': {'Preto/Branco', 'Branco/Branco'},
    'vans-knu-skool': {'Preto/Branco', 'Azul Marinho/Branco'},
    'vans-era': {'Azul Marinho/Branco', 'Branco/Branco'},
}

IMAGE_REPAIR_URLS = {
    'nike-air-force-1-07': ('https://nikeclprod.vtexassets.com/arquivos/ids/160793/CW2288_111_A_PREM.jpg?v=637654399803530000', 'https://static.nike.com/a/images/t_web_pdp_535_v2/f_auto%2Cu_9ddf04c7-2a9a-4d76-add1-d15af8f0263d%2Cc_scale%2Cfl_relative%2Cw_1.0%2Ch_1.0%2Cfl_layer_apply/b7d9211c-26e7-431a-ac24-b0540fb3c00f/AIR%2BFORCE%2B1%2B%2707.png'),
    'adidas-samba-og': ('https://www.fast-forward-fashion.de/media/1a/79/43/1686026985/adidas-sneaker-ig1024_1.webp?ts=1686026985', 'https://assets.adidas.com/images/w_500%2Cf_auto%2Cq_auto/1b91804db204496b9783a6ee5b37a525_9366/Tenis_Samba_OG_Branco_KK2277_01_00_standard.jpg'),
    'adidas-campus-00s': ('https://assets.adidas.com/images/w_500%2Cf_auto%2Cq_auto/f8cd44c1639044588c6edadefaaf56c4_faec/Campus_00s_Shoes_Black_JP9163_db06_standard.jpg', 'https://assets.adidas.com/images/w_500%2Cf_auto%2Cq_auto/475f293b99c74963aca7b77bbf55893a_9366/Tenis_Campus_00s_Preto_JK3370_01_00_standard.jpg'),
    'puma-speedcat-og': ('https://images.vegnonveg.com/resized/1400X1146/11674/speedcat-og-puma-blackpuma-white-black-66e29982925bb.jpg?format=webp', 'https://images.puma.com/image/upload/f_auto%2Cq_auto%2Cb_rgb%3Afafafa%2Cw_600%2Ch_600/global/398846/01/sv01/fnd/PNA/fmt/png/Speedcat-OG-Sneakers'),
    'new-balance-530': ('https://shelta.se/pub_images/large/MR530SG_1.jpg?timestamp=1628001245', 'https://newbrasil.vtexassets.com/arquivos/ids/228382-3840-auto/NB530_U53017S_00.webp?quality=10&v=639225687270070000'),
    'vans-old-skool': ('https://prodigyskateshop.com/cdn/shop/products/OS_1200x1200.png?v=1739229131', 'https://secure-static.vans.com.br/medias/sys_master/vans/vans/hdc/ha7/h00/h00/12898471903262/Midres-Vans-V1002001070011-01.jpg?q=100&w=1920'),
}

def product_image_for(brand, name, fallback=None):
    return PRODUCT_IMAGE_URLS.get(slugify(f"{brand}-{name}"), fallback or IMAGE_POOL[0])

BRANDS = [
 ('Nike', 15, [
  ('Air Force 1 \'07', 699.90), ('Dunk Low Retro', 729.90), ('Air Max 90', 749.90), ('Air Max 97', 999.90), ('Air Max DN', 1099.90),
  ('P-6000', 699.90), ('V2K Run', 799.90), ('Cortez', 499.90), ('Blazer Mid \'77', 599.90), ('Air Jordan 1 Low', 899.90),
  ('Air Jordan 1 Mid', 999.90), ('Air Zoom Pegasus 41', 849.90), ('Vomero 5', 999.90), ('Court Vision Low', 449.90), ('ReactX Infinity Run', 899.90)]),
 ('Adidas', 15, [
  ('Samba OG', 599.90), ('Gazelle Indoor', 649.90), ('Campus 00s', 649.90), ('Handball Spezial', 599.90), ('Superstar II', 549.90),
  ('Forum Low', 499.90), ('Stan Smith', 499.90), ('Ultraboost 5', 999.90), ('Supernova Rise', 799.90), ('Adizero SL2', 699.90),
  ('Response CL', 699.90), ('Ozweego', 749.90), ('ZX 22 Boost', 799.90), ('Grand Court 2.0', 349.90), ('Adistar 3', 599.90)]),
 ('Puma', 15, [
  ('Speedcat OG', 599.90), ('Suede Classic', 449.90), ('Palermo', 499.90), ('RS-X Reinvention', 599.90), ('CA Pro Classic', 499.90),
  ('Future Rider', 449.90), ('Slipstream Lo', 549.90), ('Caven 2.0', 349.90), ('Velocity Nitro 3', 799.90), ('Deviate Nitro 3', 999.90),
  ('Softride Enzo', 399.90), ('Axelion', 449.90), ('Pacer Future', 379.90), ('RBD Game Low', 399.90), ('Tackle', 429.90)]),
 ('New Balance', 15, [
  ('9060', 999.90), ('2002R', 899.90), ('530', 699.90), ('550', 699.90), ('574 Core', 599.90),
  ('1906R', 999.90), ('327', 649.90), ('990v6', 1599.90), ('991v2', 1699.90), ('860v2', 849.90),
  ('1000', 899.90), ('480', 499.90), ('Fresh Foam X 1080v14', 1099.90), ('725', 749.90), ('608v5', 649.90)]),
 ('Vans', 15, [
  ('Old Skool', 399.90), ('Knu Skool', 449.90), ('Authentic', 299.90), ('Era', 329.90), ('Sk8-Hi', 449.90),
  ('Slip-On Checkerboard', 349.90), ('Ultrarange Neo VR3', 699.90), ('Skate Old Skool', 449.90), ('Half Cab', 499.90), ('Old Skool Stackform', 499.90),
  ('Cruze Too', 399.90), ('Lowland CC', 399.90), ('Sport Low', 349.90), ('Authentic Stackform', 449.90), ('Hylane', 499.90)]),
]

DESCRIPTIONS = [
 'Silhueta versátil para compor o visual do dia a dia.',
 'Conforto, personalidade e presença para o corre urbano.',
 'Um clássico casual que combina com diferentes estilos.',
 'Design marcante para quem gosta de chegar com atitude.',
 'Modelo esportivo com visual atual e uso versátil.',
]
TONES = ['lilac','mint','pink','stone','cream','sand','lavender','violet']
BADGES = ['DROP NOVO','MAIS PEDIDO','EM ALTA','ESCOLHA DO MAGRÃO','CLÁSSICO','DESTAQUE']

DEFAULT_SETTINGS = {
 'store_name': 'MAGRÃO',
 'tagline': 'Seu estilo começa pelo chão. Termina lá em cima.',
 'announcement': 'PISA FORTE. CHEGA NO ESTILO.',
 'hero_title': 'O SEU ESTILO\nPEDE OUTRO\nNÍVEL.',
 'hero_subtitle': 'Nike, Adidas, Puma, New Balance e mais. Tênis que fecham o visual, do rolê de todo dia ao destaque no feed.',
 'whatsapp': '',
 'coupon_code': 'MAGRAO10',
 'coupon_percent': '10',
 'free_shipping_from': '299',
 'shipping_estimate': '19.90',
}


def connect_db():
    connection = sqlite3.connect(DATABASE, timeout=15)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA foreign_keys = ON')
    connection.execute('PRAGMA busy_timeout = 15000')
    return connection


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def send_whatsapp_template(template_name: str, parameters: list[str]) -> bool:
    """Send a pre-approved WhatsApp Cloud API template to the store owner.

    Secrets are read only from server environment variables and never returned to clients.
    Template approval is required because these notifications are business-initiated.
    """
    token = os.getenv('WHATSAPP_ACCESS_TOKEN', '').strip()
    phone_id = os.getenv('WHATSAPP_PHONE_NUMBER_ID', '').strip()
    recipient = re.sub(r'\D', '', os.getenv('WHATSAPP_ADMIN_PHONE', ''))
    if not (token and phone_id and recipient):
        app.logger.info('WhatsApp notification skipped: integration is not configured.')
        return False
    version = os.getenv('WHATSAPP_GRAPH_API_VERSION', 'v23.0').strip() or 'v23.0'
    url = f'https://graph.facebook.com/{version}/{phone_id}/messages'
    payload = {
        'messaging_product': 'whatsapp', 'to': recipient, 'type': 'template',
        'template': {
            'name': template_name,
            'language': {'code': os.getenv('WHATSAPP_TEMPLATE_LANGUAGE', 'pt_BR')},
            'components': [{'type': 'body', 'parameters': [
                {'type': 'text', 'text': str(value)[:900]} for value in parameters
            ]}]
        }
    }
    request_obj = urllib.request.Request(
        url, data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
        headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}, method='POST'
    )
    try:
        with urllib.request.urlopen(request_obj, timeout=8) as response:
            response.read()
        return True
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as exc:
        # Avoid logging tokens, customer phone numbers, or full request payloads.
        app.logger.warning('WhatsApp notification failed (%s).', type(exc).__name__)
        return False


def notify_new_order(order: dict) -> None:
    items = '; '.join(
        f"{item['brand']} {item['product']}" + (f" (cor {item['color']})" if item.get('color') else '') + f" tam. {item['size']} x{item['qty']}"
        for item in order.get('items', [])
    ) or 'Itens não informados'
    send_whatsapp_template(
        os.getenv('WHATSAPP_NEW_ORDER_TEMPLATE', 'magrao_novo_pedido'),
        [order.get('number', ''), order.get('customer', {}).get('name', 'Cliente'),
         f"R$ {order.get('total', 0):.2f}".replace('.', ','), items, order.get('customer', {}).get('payment', '')]
    )


def notify_payment_confirmed(order: dict) -> None:
    send_whatsapp_template(
        os.getenv('WHATSAPP_PAYMENT_TEMPLATE', 'magrao_pagamento_confirmado'),
        [order.get('number', ''), order.get('customer_name', 'Cliente'),
         f"R$ {float(order.get('total', 0)):.2f}".replace('.', ',')]
    )


def slugify(value):
    norm = unicodedata.normalize('NFKD', str(value)).encode('ascii', 'ignore').decode('ascii').lower()
    return re.sub(r'[^a-z0-9]+', '-', norm).strip('-') or 'produto'


def create_schema():
    db = connect_db()
    db.executescript('''
    PRAGMA journal_mode=WAL;
    CREATE TABLE IF NOT EXISTS products (
      id TEXT PRIMARY KEY, brand TEXT NOT NULL, name TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
      price REAL NOT NULL CHECK(price >= 0), old_price REAL, badge TEXT NOT NULL DEFAULT '', hot INTEGER NOT NULL DEFAULT 0,
      rating TEXT NOT NULL DEFAULT '4.8', sizes TEXT NOT NULL DEFAULT '[37,38,39,40,41,42,43]', image TEXT NOT NULL DEFAULT '',
      tone TEXT NOT NULL DEFAULT 'lilac', stock INTEGER NOT NULL DEFAULT 0, visible INTEGER NOT NULL DEFAULT 1,
      created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS customers (
      id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, phone TEXT NOT NULL UNIQUE,
      address TEXT NOT NULL DEFAULT '', cep TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS orders (
      id INTEGER PRIMARY KEY AUTOINCREMENT, number TEXT NOT NULL UNIQUE, customer_id INTEGER NOT NULL,
      payment TEXT NOT NULL, subtotal REAL NOT NULL, shipping REAL NOT NULL, discount REAL NOT NULL, total REAL NOT NULL,
      status TEXT NOT NULL DEFAULT 'Novo', notes TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL,
      FOREIGN KEY(customer_id) REFERENCES customers(id)
    );
    CREATE TABLE IF NOT EXISTS order_items (
      id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER NOT NULL, product_id TEXT,
      product_name TEXT NOT NULL, brand TEXT NOT NULL, size INTEGER NOT NULL, qty INTEGER NOT NULL,
      unit_price REAL NOT NULL, line_total REAL NOT NULL,
      FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE,
      FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE SET NULL
    );
    CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS push_subscriptions (id INTEGER PRIMARY KEY AUTOINCREMENT, endpoint TEXT NOT NULL UNIQUE, subscription_json TEXT NOT NULL, created_at TEXT NOT NULL);
    CREATE INDEX IF NOT EXISTS idx_orders_created ON orders(created_at);
    CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
    CREATE INDEX IF NOT EXISTS idx_products_brand ON products(brand);
    ''')
    for key, value in DEFAULT_SETTINGS.items():
        db.execute('INSERT OR IGNORE INTO settings(key,value) VALUES (?,?)', (key, value))
    count = db.execute('SELECT COUNT(*) AS n FROM products').fetchone()['n']
    if count == 0:
        products = []
        for brand_index, (brand, _, models) in enumerate(BRANDS):
            for i, (name, price) in enumerate(models):
                product_id = slugify(f'{brand}-{name}')
                old_price = round(price * 1.12, 2) if i % 3 != 1 else None
                products.append((
                    product_id, brand, name, DESCRIPTIONS[(i + brand_index) % len(DESCRIPTIONS)], price, old_price,
                    BADGES[(i + brand_index) % len(BADGES)], int(i in (0, 4, 9)), f'{4.6 + ((i + brand_index) % 4) / 10:.1f}',
                    json.dumps([36,37,38,39,40,41,42,43,44] if brand in ('Adidas','Vans','New Balance') else [37,38,39,40,41,42,43],
                               separators=(',',':')), product_image_for(brand, name), TONES[(i + brand_index) % len(TONES)],
                    6 + (i % 9), 1, now_iso()
                ))
        db.executemany('''INSERT INTO products
          (id,brand,name,description,price,old_price,badge,hot,rating,sizes,image,tone,stock,visible,created_at)
          VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', products)
    # Corrige apenas as imagens que vieram do antigo conjunto aleatório.
    # Fotos personalizadas (URL própria ou upload) são mantidas intactas.
    legacy_images = set(IMAGE_POOL)
    for row in db.execute('SELECT id,brand,name,image FROM products').fetchall():
        # Corrige imagem vazia ou uma das antigas imagens genéricas.
        # URLs personalizadas e uploads feitos pelo administrador são preservados.
        if not str(row['image'] or '').strip() or row['image'] in legacy_images:
            corrected = product_image_for(row['brand'], row['name'], row['image'])
            if corrected and corrected != row['image']:
                db.execute('UPDATE products SET image=? WHERE id=?', (corrected, row['id']))
        repair = IMAGE_REPAIR_URLS.get(row['id'])
        if repair and row['image'] == repair[0]:
            db.execute('UPDATE products SET image=? WHERE id=?', (repair[1], row['id']))
    db.commit(); db.close()


def get_settings():
    db = connect_db()
    values = {row['key']: row['value'] for row in db.execute('SELECT key,value FROM settings')}
    db.close()
    return {**DEFAULT_SETTINGS, **values}


def product_from_row(row):
    return {
      'id': row['id'], 'brand': row['brand'], 'name': row['name'], 'description': row['description'],
      'price': float(row['price']), 'oldPrice': float(row['old_price']) if row['old_price'] is not None else None,
      'badge': row['badge'], 'hot': bool(row['hot']), 'rating': row['rating'],
      'sizes': json.loads(row['sizes']), 'image': row['image'], 'tone': row['tone'],
      'stock': int(row['stock']), 'visible': bool(row['visible']),
    }


def require_admin(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not session.get('admin_user'):
            return jsonify({'error': 'Faça login para continuar.'}), 401
        return fn(*args, **kwargs)
    return wrapped


def require_csrf(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        provided = request.headers.get('X-CSRF-Token', '')
        saved = session.get('csrf_token', '')
        if not saved or not provided or not secrets.compare_digest(saved, provided):
            return jsonify({'error': 'Sessão expirada. Atualize a página e entre novamente.'}), 403
        return fn(*args, **kwargs)
    return wrapped


def json_error(message, code=400):
    return jsonify({'error': message}), code


@app.after_request
def secure_headers(response):
    response.headers.setdefault('X-Content-Type-Options', 'nosniff')
    response.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')
    response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
    response.headers.setdefault('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
    return response


@app.get('/')
def home():
    return send_from_directory(PUBLIC, 'index.html')


@app.get('/admin')
@app.get('/admin/')
def admin_home():
    return redirect('/admin.html')


@app.get('/admin.html')
def admin_page():
    return send_from_directory(PUBLIC, 'admin.html')


@app.get('/app')
@app.get('/app/')
def admin_app_page():
    return send_from_directory(PUBLIC, 'app-admin.html')


@app.get('/manifest.webmanifest')
def pwa_manifest():
    return send_from_directory(PUBLIC, 'manifest.webmanifest', mimetype='application/manifest+json')


@app.get('/sw.js')
def pwa_service_worker():
    response = make_response(send_from_directory(PUBLIC, 'sw.js'))
    response.headers['Service-Worker-Allowed'] = '/'
    response.headers['Cache-Control'] = 'no-cache'
    return response


@app.get('/api/admin/push/public-key')
@require_admin
def push_public_key():
    return jsonify({'publicKey': os.getenv('VAPID_PUBLIC_KEY', '')})


@app.post('/api/admin/push/subscribe')
@require_admin
@require_csrf
def push_subscribe():
    data = request.get_json(silent=True) or {}
    sub = data.get('subscription') or {}
    endpoint = str(sub.get('endpoint', ''))
    if not endpoint.startswith('https://') or not isinstance(sub.get('keys'), dict):
        return json_error('Assinatura de notificação inválida.')
    db = connect_db()
    db.execute('INSERT INTO push_subscriptions(endpoint,subscription_json,created_at) VALUES (?,?,?) ON CONFLICT(endpoint) DO UPDATE SET subscription_json=excluded.subscription_json', (endpoint, json.dumps(sub), now_iso()))
    db.commit()
    db.close()
    return jsonify({'ok': True})


def send_push_notification(title: str, body: str, tag: str) -> None:
    private_key = os.getenv('VAPID_PRIVATE_KEY', '').strip()
    public_key = os.getenv('VAPID_PUBLIC_KEY', '').strip()
    subject = os.getenv('VAPID_SUBJECT', 'mailto:admin@example.com').strip()
    if not (private_key and public_key):
        app.logger.info('Push notifications skipped: VAPID is not configured.')
        return
    try:
        from pywebpush import webpush, WebPushException
    except ImportError:
        app.logger.warning('Push notifications unavailable: install pywebpush.')
        return
    db = connect_db()
    rows = db.execute('SELECT id,endpoint,subscription_json FROM push_subscriptions').fetchall()
    stale = []
    payload = json.dumps({'title': title, 'body': body, 'tag': tag, 'url': '/app/'}, ensure_ascii=False)
    for row in rows:
        try:
            webpush(subscription_info=json.loads(row['subscription_json']), data=payload,
                    vapid_private_key=private_key, vapid_claims={'sub': subject}, ttl=60)
        except WebPushException as exc:
            if getattr(getattr(exc, 'response', None), 'status_code', None) in (404, 410):
                stale.append(row['id'])
            else:
                app.logger.warning('Push delivery failed (%s).', type(exc).__name__)
        except Exception as exc:
            app.logger.warning('Push delivery failed (%s).', type(exc).__name__)
    if stale:
        db.executemany('DELETE FROM push_subscriptions WHERE id=?', [(i,) for i in stale])
        db.commit()
    db.close()


@app.get('/health')
def health():
    return jsonify({'status': 'ok'})


@app.get('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_DIR, filename)


@app.get('/api/settings')
def public_settings():
    return jsonify(get_settings())


@app.get('/api/products')
def public_products():
    db = connect_db()
    rows = db.execute('SELECT * FROM products WHERE visible=1 ORDER BY hot DESC, brand, name').fetchall()
    db.close()
    return jsonify({'products': [product_from_row(r) for r in rows]})


@app.post('/api/orders')
def create_order():
    data = request.get_json(silent=True) or {}
    customer = data.get('customer') or {}
    items = data.get('items') or []
    name = str(customer.get('name', '')).strip()[:120]
    phone = re.sub(r'[^0-9+() .-]', '', str(customer.get('phone', '')).strip())[:30]
    address = str(customer.get('address', '')).strip()[:300]
    cep = re.sub(r'[^0-9-]', '', str(customer.get('cep', '')).strip())[:10]
    payment = str(customer.get('payment', '')).strip()[:80]
    if not name or len(phone) < 8 or not address or len(re.sub(r'\D', '', cep)) != 8 or not payment:
        return json_error('Confira nome, WhatsApp, endereço, CEP e forma de pagamento.')
    if not isinstance(items, list) or not items or len(items) > 30:
        return json_error('O carrinho está vazio ou tem itens demais.')
    settings = get_settings()
    subtotal, safe_items = 0.0, []
    db = connect_db()
    try:
        for item in items:
            pid = str(item.get('id', ''))
            try:
                size, qty = int(item.get('size')), int(item.get('qty'))
            except (ValueError, TypeError):
                db.close(); return json_error('Tamanho ou quantidade inválida.')
            if qty < 1 or qty > 10:
                db.close(); return json_error('A quantidade por modelo deve ficar entre 1 e 10 pares.')
            product = db.execute('SELECT * FROM products WHERE id=? AND visible=1', (pid,)).fetchone()
            if not product:
                db.close(); return json_error('Um produto do carrinho não está mais disponível.')
            sizes = json.loads(product['sizes'])
            if size not in sizes:
                db.close(); return json_error(f'O tamanho {size} não está disponível para {product["name"]}.')
            if int(product['stock']) < qty:
                db.close(); return json_error(f'Estoque insuficiente para {product["name"]}; estoque atual: {product["stock"]}.')
            color = str(item.get('color', '') or '').strip()[:60]
            if color not in PRODUCT_COLOR_OPTIONS.get(pid, set()):
                color = ''
            price = float(product['price']); line_total = round(price * qty, 2); subtotal += line_total
            safe_items.append({'id': pid, 'product': product['name'], 'brand': product['brand'], 'size': size,
                               'color': color, 'qty': qty, 'unitPrice': price, 'lineTotal': line_total})
        subtotal = round(subtotal, 2)
        free_from = float(settings.get('free_shipping_from', 299) or 299)
        shipping = 0.0 if subtotal == 0 or subtotal >= free_from else float(settings.get('shipping_estimate', 19.90) or 19.90)
        configured_coupon = str(settings.get('coupon_code', 'MAGRAO10')).strip().upper()
        coupon_valid = bool(configured_coupon) and str(data.get('coupon', '')).strip().upper() == configured_coupon
        discount = round(subtotal * max(0, min(50, float(settings.get('coupon_percent', 10) or 0))) / 100, 2) if coupon_valid else 0.0
        total = round(max(0, subtotal - discount + shipping), 2)
        db.execute('INSERT INTO customers(name,phone,address,cep,created_at,updated_at) VALUES (?,?,?,?,?,?) ON CONFLICT(phone) DO UPDATE SET name=excluded.name,address=excluded.address,cep=excluded.cep,updated_at=excluded.updated_at', (name, phone, address, cep, now_iso(), now_iso()))
        customer_id = db.execute('SELECT id FROM customers WHERE phone=?', (phone,)).fetchone()['id']
        number = 'MI-' + uuid.uuid4().hex[:8].upper()
        cursor = db.execute('INSERT INTO orders(number,customer_id,payment,subtotal,shipping,discount,total,status,created_at) VALUES (?,?,?,?,?,?,?,?,?)', (number, customer_id, payment, subtotal, shipping, discount, total, 'Novo', now_iso()))
        order_id = cursor.lastrowid
        for item in safe_items:
            db.execute('INSERT INTO order_items(order_id,product_id,product_name,brand,size,qty,unit_price,line_total) VALUES (?,?,?,?,?,?,?,?)',
                       (order_id, item['id'], item['product'] + (f" - {item['color']}" if item.get('color') else ''), item['brand'], item['size'], item['qty'], item['unitPrice'], item['lineTotal']))
            stock_update = db.execute('UPDATE products SET stock=stock-? WHERE id=? AND stock>=?', (item['qty'], item['id'], item['qty']))
            if stock_update.rowcount != 1:
                db.rollback(); db.close()
                return json_error('O estoque mudou enquanto o pedido era registrado. Atualize o carrinho e tente novamente.', 409)
        db.commit()
        order = {'number': number, 'createdAt': now_iso(), 'customer': {'name':name,'phone':phone,'address':address,'cep':cep,'payment':payment},
                 'items': safe_items, 'subtotal': subtotal, 'shipping': shipping, 'discount': discount, 'total': total, 'status':'Novo'}
        # The order is committed first; a WhatsApp outage must never undo a valid order.
        notify_new_order(order)
        send_push_notification('Novo pedido na Magrão Imports', f"Pedido {number} recebido. Total: R$ {total:.2f}.", 'pedido-' + number)
        return jsonify({'ok': True, 'order': order}), 201
    except sqlite3.Error:
        db.rollback()
        app.logger.exception('Falha ao salvar pedido')
        return json_error('Não foi possível registrar o pedido. Tente novamente.', 500)
    finally:
        try: db.close()
        except Exception: pass


@app.post('/api/admin/login')
def admin_login():
    data = request.get_json(silent=True) or {}
    username = str(data.get('username', ''))
    password = str(data.get('password', ''))
    expected_user = os.getenv('ADMIN_USERNAME', 'admin')
    password_hash = os.getenv('ADMIN_PASSWORD_HASH', '')
    # Nunca existe senha administrativa padrão no código. Configure um hash localmente ou no Render.
    if not password_hash or username != expected_user or not check_password_hash(password_hash, password):
        return json_error('Usuário ou senha inválidos. Confira as variáveis de configuração do administrador.', 401)
    session.clear()
    session['admin_user'] = username
    session['csrf_token'] = secrets.token_urlsafe(32)
    session.permanent = True
    return jsonify({'ok': True, 'username': username, 'csrf': session['csrf_token']})


@app.post('/api/admin/logout')
@require_admin
@require_csrf
def admin_logout():
    session.clear()
    return jsonify({'ok': True})


@app.get('/api/admin/me')
def admin_me():
    if session.get('admin_user'):
        return jsonify({'authenticated': True, 'username': session['admin_user'], 'csrf': session.get('csrf_token', '')})
    return jsonify({'authenticated': False, 'configured': bool(os.getenv('ADMIN_PASSWORD_HASH'))})


@app.get('/api/admin/dashboard')
@require_admin
def admin_dashboard():
    db = connect_db()
    counts = {
      'products': db.execute('SELECT COUNT(*) FROM products').fetchone()[0],
      'visibleProducts': db.execute('SELECT COUNT(*) FROM products WHERE visible=1').fetchone()[0],
      'orders': db.execute('SELECT COUNT(*) FROM orders').fetchone()[0],
      'pending': db.execute("SELECT COUNT(*) FROM orders WHERE status IN ('Novo','Em atendimento','Aguardando pagamento')").fetchone()[0],
      'customers': db.execute('SELECT COUNT(*) FROM customers').fetchone()[0],
      'confirmedRevenue': db.execute("SELECT COALESCE(SUM(total),0) FROM orders WHERE status IN ('Pago','Enviado','Entregue')").fetchone()[0],
      'allOrderValue': db.execute("SELECT COALESCE(SUM(total),0) FROM orders WHERE status!='Cancelado'").fetchone()[0],
    }
    recent = db.execute('''SELECT o.number,o.total,o.status,o.created_at,c.name AS customer_name
       FROM orders o JOIN customers c ON c.id=o.customer_id ORDER BY o.id DESC LIMIT 8''').fetchall()
    top = db.execute('''SELECT oi.product_name AS name,oi.brand,SUM(oi.qty) AS sold,SUM(oi.line_total) AS value
       FROM order_items oi JOIN orders o ON o.id=oi.order_id WHERE o.status IN ('Pago','Enviado','Entregue')
       GROUP BY oi.product_name,oi.brand ORDER BY sold DESC,value DESC LIMIT 5''').fetchall()
    db.close()
    return jsonify({'counts': {k: round(float(v),2) if k in ('confirmedRevenue','allOrderValue') else int(v) for k,v in counts.items()},
                    'recentOrders':[dict(r) for r in recent], 'topProducts':[dict(r) for r in top]})


@app.get('/api/admin/products')
@require_admin
def admin_products():
    db = connect_db(); rows = db.execute('SELECT * FROM products ORDER BY brand,name').fetchall(); db.close()
    return jsonify({'products':[product_from_row(r) for r in rows]})


def validate_product(data, existing=None):
    data = data if isinstance(data, dict) else {}
    brand = str(data.get('brand','')).strip()[:60]
    name = str(data.get('name','')).strip()[:120]
    description = str(data.get('description','')).strip()[:600]
    try: price = round(float(data.get('price')), 2)
    except (TypeError,ValueError): return None, 'Informe um preço válido.'
    if not brand or not name or price < 0 or price > 1000000: return None, 'Marca, nome e preço válido são obrigatórios.'
    try:
        old_raw = data.get('oldPrice', data.get('old_price'))
        old_price = None if old_raw in ('', None) else round(float(old_raw),2)
        stock = int(data.get('stock',0))
    except (TypeError,ValueError): return None, 'Preço anterior ou estoque inválido.'
    if (old_price is not None and old_price < 0) or stock < 0 or stock > 100000: return None, 'Preço anterior ou estoque fora do limite.'
    sizes_raw = data.get('sizes', [37,38,39,40,41,42,43])
    if isinstance(sizes_raw, str):
        try: sizes = [int(x.strip()) for x in sizes_raw.split(',') if x.strip()]
        except ValueError: return None, 'Use tamanhos separados por vírgula, como 37,38,39.'
    elif isinstance(sizes_raw, list):
        try: sizes = [int(x) for x in sizes_raw]
        except (TypeError,ValueError): return None, 'Tamanhos inválidos.'
    else: return None, 'Tamanhos inválidos.'
    sizes = sorted(set(sizes))
    if not sizes or len(sizes) > 25 or any(x < 15 or x > 55 for x in sizes): return None, 'Informe tamanhos entre 15 e 55.'
    image = str(data.get('image', existing['image'] if existing else '')).strip()[:1200]
    if image and not (image.startswith('/') or image.startswith('https://') or image.startswith('http://')): return None, 'A imagem precisa ser um link HTTP(S) ou caminho de upload.'
    return {'brand':brand,'name':name,'description':description,'price':price,'old_price':old_price,
            'badge':str(data.get('badge','')).strip()[:45], 'hot':int(bool(data.get('hot',False))),
            'rating':str(data.get('rating','4.8'))[:8], 'sizes':json.dumps(sizes,separators=(',',':')), 'image':image,
            'tone':str(data.get('tone','lilac'))[:30], 'stock':stock, 'visible':int(bool(data.get('visible',True)))}, None


@app.post('/api/admin/products')
@require_admin
@require_csrf
def create_product():
    data=request.get_json(silent=True) or {}
    product, error=validate_product(data)
    if error: return json_error(error)
    pid=slugify(data.get('id') or f"{product['brand']}-{product['name']}")[:100]
    db=connect_db()
    if db.execute('SELECT 1 FROM products WHERE id=?',(pid,)).fetchone(): pid=f'{pid}-{uuid.uuid4().hex[:5]}'
    db.execute('''INSERT INTO products(id,brand,name,description,price,old_price,badge,hot,rating,sizes,image,tone,stock,visible,created_at)
      VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',(pid,product['brand'],product['name'],product['description'],product['price'],product['old_price'],product['badge'],product['hot'],product['rating'],product['sizes'],product['image'],product['tone'],product['stock'],product['visible'],now_iso()))
    db.commit(); row=db.execute('SELECT * FROM products WHERE id=?',(pid,)).fetchone(); db.close()
    return jsonify({'ok':True,'product':product_from_row(row)}),201


@app.put('/api/admin/products/<path:product_id>')
@require_admin
@require_csrf
def update_product(product_id):
    db=connect_db(); existing=db.execute('SELECT * FROM products WHERE id=?',(product_id,)).fetchone()
    if not existing: db.close(); return json_error('Produto não encontrado.',404)
    data=request.get_json(silent=True) or {}
    merged=product_from_row(existing); merged.update(data)
    product,error=validate_product(merged,existing)
    if error: db.close(); return json_error(error)
    db.execute('''UPDATE products SET brand=?,name=?,description=?,price=?,old_price=?,badge=?,hot=?,rating=?,sizes=?,image=?,tone=?,stock=?,visible=? WHERE id=?''',
      (product['brand'],product['name'],product['description'],product['price'],product['old_price'],product['badge'],product['hot'],product['rating'],product['sizes'],product['image'],product['tone'],product['stock'],product['visible'],product_id))
    db.commit(); row=db.execute('SELECT * FROM products WHERE id=?',(product_id,)).fetchone(); db.close()
    return jsonify({'ok':True,'product':product_from_row(row)})


@app.delete('/api/admin/products/<path:product_id>')
@require_admin
@require_csrf
def delete_product(product_id):
    db=connect_db(); row=db.execute('SELECT id FROM products WHERE id=?',(product_id,)).fetchone()
    if not row: db.close(); return json_error('Produto não encontrado.',404)
    db.execute('DELETE FROM products WHERE id=?',(product_id,));db.commit();db.close()
    return jsonify({'ok':True})


@app.post('/api/admin/upload')
@require_admin
@require_csrf
def upload_image():
    file=request.files.get('image')
    if not file or not file.filename: return json_error('Selecione um arquivo de imagem.')
    ext=Path(secure_filename(file.filename)).suffix.lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS: return json_error('Formato não aceito. Use JPG, PNG, WEBP ou GIF.')
    filename=f'{uuid.uuid4().hex}{ext}'
    file.save(UPLOAD_DIR/filename)
    return jsonify({'ok':True,'url':f'/uploads/{filename}'})


@app.get('/api/admin/orders')
@require_admin
def admin_orders():
    db=connect_db()
    rows=db.execute('''SELECT o.*,c.name customer_name,c.phone,c.address,c.cep FROM orders o JOIN customers c ON c.id=o.customer_id ORDER BY o.id DESC LIMIT 500''').fetchall()
    orders=[]
    for r in rows:
        item_rows=db.execute('SELECT product_name,brand,size,qty,unit_price,line_total FROM order_items WHERE order_id=?',(r['id'],)).fetchall()
        order=dict(r);order['items']=[dict(i) for i in item_rows];orders.append(order)
    db.close()
    return jsonify({'orders':orders,'statuses':STATUSES})


@app.patch('/api/admin/orders/<int:order_id>')
@require_admin
@require_csrf
def update_order(order_id):
    data=request.get_json(silent=True) or {}; status=str(data.get('status',''))
    if status not in STATUSES: return json_error('Situação do pedido inválida.')
    db=connect_db()
    order=db.execute('SELECT status,number FROM orders WHERE id=?',(order_id,)).fetchone()
    if not order: db.close(); return json_error('Pedido não encontrado.',404)
    old_status=order['status']
    items=db.execute('SELECT product_id,qty FROM order_items WHERE order_id=?',(order_id,)).fetchall()
    if old_status != 'Cancelado' and status == 'Cancelado':
        for item in items:
            if item['product_id']:
                db.execute('UPDATE products SET stock=stock+? WHERE id=?',(item['qty'],item['product_id']))
    elif old_status == 'Cancelado' and status != 'Cancelado':
        for item in items:
            if item['product_id']:
                product=db.execute('SELECT stock,name FROM products WHERE id=?',(item['product_id'],)).fetchone()
                if not product or product['stock'] < item['qty']:
                    db.rollback();db.close();return json_error('Não há estoque suficiente para reativar este pedido. Ajuste o estoque antes.')
        for item in items:
            if item['product_id']: db.execute('UPDATE products SET stock=stock-? WHERE id=?',(item['qty'],item['product_id']))
    order_notice = None
    if old_status != 'Pago' and status == 'Pago':
        notice_row = db.execute('''SELECT o.number,o.total,c.name customer_name FROM orders o JOIN customers c ON c.id=o.customer_id WHERE o.id=?''',(order_id,)).fetchone()
        if notice_row: order_notice = dict(notice_row)
    db.execute('UPDATE orders SET status=? WHERE id=?',(status,order_id));db.commit();db.close()
    # This alert fires when the administrator marks the order as paid. Until a payment
    # provider is integrated, this is a manual confirmation, not an automatic bank check.
    if order_notice:
        notify_payment_confirmed(order_notice)
        send_push_notification('Pagamento confirmado', f"Pedido {order_notice['number']} marcado como pago.", 'pago-' + order_notice['number'])
    if old_status != 'Cancelado' and status == 'Cancelado':
        send_push_notification('Pedido cancelado', f"Pedido {order['number']} foi cancelado.", 'cancelado-' + order['number'])
    return jsonify({'ok':True})


@app.get('/api/admin/customers')
@require_admin
def admin_customers():
    db=connect_db()
    rows=db.execute('''SELECT c.id,c.name,c.phone,c.address,c.cep,c.created_at,c.updated_at,COUNT(o.id) orders_count,
      COALESCE(SUM(CASE WHEN o.status!='Cancelado' THEN o.total ELSE 0 END),0) order_value,MAX(o.created_at) last_order
      FROM customers c LEFT JOIN orders o ON o.customer_id=c.id GROUP BY c.id ORDER BY last_order DESC,c.name LIMIT 1000''').fetchall()
    db.close();return jsonify({'customers':[dict(r) for r in rows]})


@app.get('/api/admin/settings')
@require_admin
def admin_settings():
    return jsonify(get_settings())


@app.put('/api/admin/settings')
@require_admin
@require_csrf
def update_settings():
    data=request.get_json(silent=True) or {}
    allowed=set(DEFAULT_SETTINGS)
    updates={}
    for key in allowed:
        if key in data:
            value=str(data[key]).strip()
            if key in ('store_name','tagline','announcement','hero_title','hero_subtitle'): value=value[:350]
            elif key=='whatsapp': value=re.sub(r'[^0-9]', '', value)[:20]
            elif key=='coupon_code': value=re.sub(r'[^A-Za-z0-9_-]', '', value).upper()[:30]
            elif key=='coupon_percent':
                try: value=str(max(0,min(50,float(value))))
                except ValueError: return json_error('Percentual do cupom inválido.')
            elif key=='free_shipping_from':
                try: value=str(max(0,min(100000,float(value))))
                except ValueError: return json_error('Valor mínimo de frete grátis inválido.')
            elif key=='shipping_estimate':
                try: value=str(max(0,min(100000,float(value))))
                except ValueError: return json_error('Estimativa de frete inválida.')
            updates[key]=value
    db=connect_db();db.executemany('INSERT INTO settings(key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',updates.items());db.commit();db.close()
    return jsonify({'ok':True,'settings':get_settings()})


@app.get('/api/admin/export/<kind>')
@require_admin
def export_csv(kind):
    db=connect_db(); output=io.StringIO(); writer=csv.writer(output)
    if kind=='products':
        writer.writerow(['id','brand','name','price','old_price','stock','visible','sizes'])
        for row in db.execute('SELECT id,brand,name,price,old_price,stock,visible,sizes FROM products ORDER BY brand,name'):
            writer.writerow(list(row))
        filename='magrao-produtos.csv'
    elif kind=='orders':
        writer.writerow(['pedido','criado_em','cliente','whatsapp','subtotal','frete','desconto','total','status','pagamento'])
        for row in db.execute('''SELECT o.number,o.created_at,c.name,c.phone,o.subtotal,o.shipping,o.discount,o.total,o.status,o.payment FROM orders o JOIN customers c ON c.id=o.customer_id ORDER BY o.id DESC'''):
            writer.writerow(list(row))
        filename='magrao-pedidos.csv'
    else:
        db.close();return json_error('Tipo de exportação inválido.',404)
    db.close(); response=make_response('\ufeff'+output.getvalue());response.headers['Content-Type']='text/csv; charset=utf-8';response.headers['Content-Disposition']=f'attachment; filename="{filename}"';return response


create_schema()

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=int(os.getenv('PORT', '5000')), debug=False)
