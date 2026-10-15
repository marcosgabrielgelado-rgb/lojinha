# Magrão Imports — loja virtual com painel administrativo

Projeto Flask responsivo com identidade visual roxa/lilás e branca, fonte cartoon, catálogo de tênis, carrinho, registro de pedidos e administração autenticada.

## Incluído nesta versão

- Catálogo inicial com **75 modelos de demonstração**: 15 Nike, 15 Adidas, 15 Puma, 15 New Balance e 15 Vans.
- Busca, filtro por marca, ordenação, tamanhos, favoritos, carrinho, cupom configurável e estimativa de frete.
- Pedido gravado no servidor com número, informações do cliente, endereço, itens e totais calculados novamente pelo servidor.
- Verificação e reserva de estoque durante a criação do pedido; a reposição de estoque acontece ao cancelar um pedido.
- Painel administrativo em `/admin`, com login privado.
- CRUD de produtos, preços, estoque, tamanhos, visibilidade, destaque e fotos por upload ou URL.
- Listas de pedidos e clientes; atualização de status; relatórios de faturamento confirmado e produtos vendidos.
- Personalização de nome, textos da vitrine, WhatsApp comercial, cupom e frete.
- Exportação CSV de catálogo e pedidos.
- SQLite e pasta de imagens configuráveis; blueprint de publicação no Render com disco persistente.
- Proteções básicas de sessão, cookie HTTP-only, SameSite, CSRF nas mudanças administrativas e headers de segurança.

## Catálogo e fotos: leia antes de vender

Os 75 nomes e preços iniciais são referências para demonstrar o sistema. As imagens do catálogo são fotos de referência reutilizadas e **não garantem mostrar exatamente o modelo ou a cor descritos**. No painel, edite cada produto e envie uma foto própria ou uma imagem cujo uso comercial você esteja autorizado a fazer. Confirme autenticidade, preço, estoque, numeração, frete e prazo antes de aceitar pedidos reais.

Este projeto identifica nomes de marcas/modelos no catálogo, mas não declara parceria oficial com Nike, Adidas, Puma, New Balance ou Vans.

## Rodar no Windows

1. Instale Python 3.11 ou superior: https://www.python.org/downloads/windows/ . Durante a instalação, marque `Add Python to PATH`.
2. Extraia o ZIP inteiro para uma pasta, por exemplo `C:\MagraoImports`.
3. Abra essa pasta no Explorador de Arquivos, clique na barra de endereço, digite `cmd` e aperte Enter.
4. Execute:

   ```bat
   python -m venv .venv
   .venv\Scripts\activate
   python -m pip install -r requirements.txt
   python setup_admin.py
   python app.py
   ```

5. Abra `http://127.0.0.1:5000` para a loja e `http://127.0.0.1:5000/admin` para a administração. A janela do terminal deve continuar aberta enquanto o site estiver rodando.

O `setup_admin.py` pede para criar usuário e senha, grava o hash da senha no `.env` e cria uma chave de sessão aleatória. Não existe uma senha administrativa padrão embutida no projeto.

## Publicar no Render

A loja precisa de um **Web Service**, pois um Static Site não executa o backend Python nem guarda pedidos num banco central. O arquivo `render.yaml` define um serviço Python, variáveis de ambiente e disco persistente em `/var/data` para o SQLite e as fotos enviadas.

1. Coloque o conteúdo do ZIP num repositório privado do GitHub.
2. No Render, use **New → Blueprint** para importar o repositório com `render.yaml`, ou crie um **Web Service** apontando para ele.
3. Configure o hash da senha administrativa como variável secreta `ADMIN_PASSWORD_HASH` e defina `ADMIN_USERNAME`.
4. Use `pip install -r requirements.txt` como comando de build e `gunicorn --bind 0.0.0.0:$PORT app:app --workers 2 --threads 4 --timeout 90` como comando de início caso esteja configurando manualmente.
5. Confirme que `DATABASE_PATH=/var/data/magrao.db`, `UPLOAD_FOLDER=/var/data/uploads`, `COOKIE_SECURE=1` e `SECRET_KEY` aleatória estão definidos. Não remova o disco persistente depois de começar a receber pedidos.
6. Quando o serviço estiver publicado, entre em `https://SEU-ENDERECO.onrender.com/admin`.

### Gerar o hash da senha para usar no Render

No seu computador, com as dependências instaladas, execute:

```bash
python -c "from getpass import getpass; from werkzeug.security import generate_password_hash; print(generate_password_hash(getpass('Nova senha: ')))"
```

Copie o hash gerado para o campo `ADMIN_PASSWORD_HASH` nas variáveis de ambiente do serviço Render. Use uma senha forte e não a compartilhe no chat nem a coloque no GitHub. `setup_admin.py` cria as credenciais locais no `.env`; no Render, as variáveis de ambiente do serviço substituem as configurações locais.

**Atenção aos custos:** discos persistentes do Render só estão disponíveis em serviços pagos. O plano gratuito tem armazenamento efêmero, portanto pode perder o banco e as imagens em reinícios, suspensão ou novo deploy. Consulte a documentação atual de discos e planos antes de publicar. Para crescer depois, considere migrar o banco para PostgreSQL gerenciado.

## Pedidos, WhatsApp e pagamentos

- Pedidos são salvos no banco central e aparecem no painel.
- Se você preencher o número comercial em **Loja e aparência**, o navegador abre o WhatsApp com o resumo do pedido. O cliente ainda precisa enviar a mensagem para iniciar o atendimento.
- O site **não cobra pagamentos** por cartão ou Pix nesta versão. Se quiser checkout online, será necessário integrar um provedor de pagamento no backend e tratar webhooks de forma segura. Nunca armazene número de cartão ou código de segurança no banco do site.
- Os status `Pago`, `Enviado` e `Entregue` contam para o faturamento confirmado dos relatórios. Atualize o status só depois da confirmação real.

## Notificações de pedidos pelo WhatsApp

O backend pode enviar avisos para o WhatsApp do dono usando a WhatsApp Cloud API oficial da Meta. Os segredos ficam em variáveis de ambiente do servidor (nunca no JavaScript, repositório público ou navegador). Configure estas variáveis no `.env` local para testes e como Environment Variables privadas no Render:

- `WHATSAPP_ACCESS_TOKEN`: token de acesso da Meta.
- `WHATSAPP_PHONE_NUMBER_ID`: ID do número de WhatsApp Business conectado à Cloud API.
- `WHATSAPP_ADMIN_PHONE`: número do dono que receberá os alertas, com código do país e DDD, só dígitos (ex.: `5531999999999`).
- `WHATSAPP_GRAPH_API_VERSION`: versão da Graph API (padrão `v23.0`).
- `WHATSAPP_TEMPLATE_LANGUAGE`: idioma aprovado dos modelos (padrão `pt_BR`).
- `WHATSAPP_NEW_ORDER_TEMPLATE`: nome do modelo aprovado para novos pedidos (padrão `magrao_novo_pedido`).
- `WHATSAPP_PAYMENT_TEMPLATE`: nome do modelo aprovado para pagamento confirmado (padrão `magrao_pagamento_confirmado`).

Crie e aprove no WhatsApp Manager da Meta dois modelos de mensagem em português com estes parâmetros de corpo, na ordem exata:

1. `magrao_novo_pedido`: `Novo pedido {{1}}. Cliente: {{2}}. Total: {{3}}. Itens: {{4}}. Forma de pagamento: {{5}}.`
2. `magrao_pagamento_confirmado`: `Pagamento confirmado para o pedido {{1}}. Cliente: {{2}}. Total: {{3}}.`

Os modelos precisam ser aprovados pela Meta antes do envio. Os alertas são enviados ao número configurado como destinatário; o site não expõe token nem encaminha dados de clientes a visitantes. O alerta de novo pedido é disparado depois de salvar o pedido. O alerta de pagamento é disparado quando o status muda para `Pago`. **Nesta versão, esse status é marcado manualmente no painel**: não há provedor de pagamento conectado, então o aviso não comprova automaticamente que Pix/cartão foi liquidado. Para confirmação automática, é necessário integrar um provedor (por exemplo, Mercado Pago) e validar a assinatura do webhook dele antes de marcar o pedido como pago.

Se as variáveis não estiverem configuradas, a loja continua registrando pedidos normalmente e grava apenas um aviso genérico no log; não vaza tokens ou dados pessoais.

## Dados persistentes e segurança

- Banco: `instance/magrao.db` por padrão ou caminho definido em `DATABASE_PATH`.
- Fotos enviadas: `instance/uploads/` por padrão ou caminho definido em `UPLOAD_FOLDER`.
- Segredos: `.env` local ou variáveis secretas do serviço de hospedagem. O `.gitignore` exclui `.env`, banco, uploads locais e ambientes virtuais.
- Faça backups do banco e das fotos de uploads; as fotos enviadas devem permanecer em armazenamento persistente.
- O projeto não inclui política jurídica pronta. Antes de divulgar, configure informações reais de contato, entrega, trocas, devoluções, privacidade e tratamento dos dados dos clientes conforme as suas obrigações legais.

## Estrutura principal

- `app.py`: backend, autenticação, API, pedidos, estoque, relatórios e banco.
- `public/index.html`, `public/styles.css`, `public/app.js`: vitrine.
- `public/admin.html`, `public/admin.css`, `public/admin.js`: painel privado.
- `setup_admin.py`: configuração inicial de senha.
- `render.yaml`: blueprint de hospedagem.

## Prévia visual sem servidor

O arquivo `preview.html` permite abrir a vitrine no navegador para conferir o layout e testar visualmente catálogo, filtros, tamanhos e carrinho sem iniciar o backend. Essa prévia usa dados falsos em memória: **pedidos feitos nela não são salvos**, não chegam ao painel e não representam vendas reais. Para testar o login, banco de dados e pedidos centralizados, siga a seção de instalação do Windows ou publique o Web Service.

## Aplicativo Magrão Imports Admin (Android e computador)

O app administrativo instalável fica em `/app/` e usa a mesma autenticação privada do painel. Em Android, abra o endereço HTTPS da loja no Chrome e escolha **Instalar app** ou **Adicionar à tela inicial**. No computador, use Chrome ou Edge e o ícone de instalação na barra de endereço. O servidor local `http://127.0.0.1:5000` serve para teste no próprio computador; push real exige HTTPS (exceto localhost).

### Configurar notificações push

O app permite ativar notificações para novo pedido, pagamento marcado como confirmado e pedido cancelado. As notificações push não contêm dados pessoais do cliente; mostram apenas o número do pedido e o evento. A lista detalhada só fica disponível após login. O status `Pago` só é automático se um provedor de pagamentos confiável for integrado; nesta versão, o aviso de pagamento é disparado quando o administrador altera o status para `Pago` no painel.

1. Gere chaves VAPID em um ambiente Python com as dependências instaladas:

   ```bash
   python -c "from py_vapid import Vapid; v=Vapid(); v.generate_keys(); print('PUBLIC_KEY=',v.public_key_urlsafe); print('PRIVATE_KEY=',v.private_key_pem().decode() if isinstance(v.private_key_pem(),bytes) else v.private_key_pem())"
   ```

   Guarde a chave privada com segurança. Se sua versão de `py_vapid` não expuser esses métodos, consulte a documentação do pacote `pywebpush` para geração VAPID.
2. Configure `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY` e `VAPID_SUBJECT` como variáveis privadas no Render (ou no `.env` local, que não deve ser publicado).
3. Faça novo deploy para instalar `pywebpush` e reinicie o serviço.
4. Acesse `https://SEU-DOMINIO/app/`, entre com seu usuário e senha e clique em **Ativar notificações** em cada dispositivo que deseja registrar.
5. Permita as notificações no navegador e teste com um pedido real de teste.

As assinaturas push são guardadas no banco de dados do servidor. Proteja o banco e use armazenamento persistente. Nunca exponha `VAPID_PRIVATE_KEY`, `SECRET_KEY`, hash/senha de administrador ou tokens em JavaScript público. O serviço push depende do navegador e do sistema operacional; modos de economia de bateria podem atrasar alertas.

### Eventos

- Pedido novo: depois de o pedido ser salvo no banco.
- Pagamento confirmado: quando o status muda para `Pago` no painel.
- Pedido cancelado: quando o status muda para `Cancelado`.

Para confirmação automática de Pix/cartão, integre um provedor de pagamento e valide webhooks assinados antes de alterar o status. Não marque automaticamente como pago só porque o cliente enviou um comprovante.

## Correção das imagens dos produtos

A lista completa de referências está no arquivo `URLS_IMAGENS_PRODUTOS.csv` incluído na pasta principal do projeto. Ela relaciona cada marca e modelo à URL configurada para sua foto.

O catálogo inclui uma URL de imagem para cada um dos 75 modelos. Esta versão corrige as URLs padrão de seis modelos com referências de imagem atualizadas e inclui tentativa automática de outras imagens reais do mesmo tênis quando uma foto falha. A migração troca somente URLs padrão antigas; fotos enviadas no painel e URLs personalizadas são preservadas. Como as fotos são servidas por sites externos, o fornecedor pode mudar ou bloquear um link. Para controlar isso definitivamente, envie fotos próprias pelo painel administrativo.

### Seletor de cores reais

A vitrine agora oferece **67 opções de colorway em 29 modelos**, incluindo Nike Air Force 1, Dunk Low, Air Max 90/97, Pegasus 41 e Vomero 5; adidas Samba OG, Gazelle Indoor e Campus 00s; PUMA Speedcat OG, Suede Classic e Palermo; vários New Balance; e Vans Old Skool, Knu Skool e Era. Cada opção usa uma foto própria do colorway, sem simular uma nova cor com filtro aplicado à mesma imagem. A escolha atualiza a foto do card e do modal; a cor também acompanha o item no carrinho, no resumo do checkout e no registro do pedido. As opções são validadas no servidor. O sistema também tem URLs de reserva para **50 modelos** e tenta outra foto correspondente se um link falhar.


## Imagens e variações de cores

- `public/product-colors.js` contém os colorways selecionáveis e as URLs de reserva para imagens que falharem.
- As bolinhas de cores no catálogo deslizam horizontalmente quando há muitas opções; no detalhe do produto, todas as opções ficam disponíveis.
- `app.py` valida as cores selecionadas ao registrar o pedido e corrige imagens realmente vazias na base, sem sobrescrever URLs personalizadas ou uploads feitos pelo painel.
- `URLS_VARIACOES_CORES.csv` reúne as URLs de colorways e as imagens de reserva para manutenção. Como são fotos hospedadas em sites externos, um fornecedor pode mudar uma URL; o site tenta as alternativas antes de mostrar o placeholder.
