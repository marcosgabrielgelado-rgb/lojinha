import getpass, secrets
from pathlib import Path
from werkzeug.security import generate_password_hash

root = Path(__file__).resolve().parent
username = input('Nome de usuário do administrador [admin]: ').strip() or 'admin'
while True:
    password = getpass.getpass('Crie uma senha forte (mínimo 12 caracteres): ')
    if len(password) < 12:
        print('Use pelo menos 12 caracteres. Uma senha de quatro dígitos é um convite, não uma proteção.')
        continue
    confirm = getpass.getpass('Repita a senha: ')
    if password != confirm:
        print('As senhas não coincidem.')
        continue
    break
secret = secrets.token_urlsafe(48)
env = root / '.env'
old = {}
if env.exists():
    for line in env.read_text(encoding='utf-8').splitlines():
        if '=' in line and not line.strip().startswith('#'):
            k,v=line.split('=',1);old[k]=v
old.update({'SECRET_KEY': secret, 'ADMIN_USERNAME': username,
            'ADMIN_PASSWORD_HASH': generate_password_hash(password),
            'DATABASE_PATH': old.get('DATABASE_PATH','instance/magrao.db'),
            'UPLOAD_FOLDER': old.get('UPLOAD_FOLDER','instance/uploads'),
            'COOKIE_SECURE': old.get('COOKIE_SECURE','0')})
env.write_text('# Arquivo privado. Nao envie ao GitHub.\n'+'\n'.join(f'{k}={v}' for k,v in old.items())+'\n',encoding='utf-8')
try: env.chmod(0o600)
except OSError: pass
print(f'Configuracao salva em {env}. Guarde esse arquivo e nao o publique.')
print('Para o Render, copie ADMIN_USERNAME e ADMIN_PASSWORD_HASH para as variaveis de ambiente do servico.')
