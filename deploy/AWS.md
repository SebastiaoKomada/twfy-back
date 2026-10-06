# Deploy: Docker Hub → EC2 com SQLite → Amplify

Região: **us-east-1 (N. Virginia)**. O backend roda em uma EC2 e guarda o
SQLite em um volume persistente do Docker. O React/Vite vai para o Amplify
Hosting. RDS não é necessário neste deploy.

```text
Navegador → Amplify (React, HTTPS)
Navegador → api.seudominio.com (HTTPS) → Caddy na EC2 → FastAPI → SQLite
Docker Hub → imagem da API baixada pela EC2
```

As chamadas à API partem do navegador do aluno. Por isso, restrinja o acesso
à API pelos IPs públicos de saída da turma/instrutor; o domínio do Amplify
não é uma origem válida para regras de Security Group. A aplicação contém
vulnerabilidades intencionais para a aula de Web Hacking; use dados de teste.

## 1. Publicar a imagem no Docker Hub

Os repositórios Git são separados:
[twfy-back](https://github.com/SebastiaoKomada/twfy-back) para a API e
[twfy-front](https://github.com/SebastiaoKomada/twfy-front) para o React.

Crie o repositório `tw4y-api` no seu Docker Hub. Na raiz do clone de
`twfy-back` (ou deste workspace), com o Docker Desktop aberto:

```bash
docker login
bash deploy/publish-image.sh SEU_USUARIO/tw4y-api 1.0.0
```

O script faz build e push para `linux/amd64` e `linux/arm64`, permitindo usar
EC2 `t3` ou `t4g`, mesmo se o build for feito em um Mac com Apple Silicon.
Use uma tag nova para cada versão; por exemplo, `1.0.1` no próximo deploy.
O contexto de build é a raiz de `twfy-back`, ou `backend/` neste workspace.
O Dockerfile copia apenas dependências, código da API e entrypoint; `.env`,
banco local e material do instrutor não entram na imagem. O banco será criado
na EC2 e não inclui os dados do SQLite local. A imagem executa como usuário
sem privilégios.

## 2. Criar a EC2

No console EC2, selecione **us-east-1** e configure:

| Campo | Valor inicial para este laboratório |
| --- | --- |
| Nome | `tw4y-api` |
| AMI | Ubuntu Server 24.04 LTS, arquitetura x86_64 |
| Instância | `t3.micro` para começar; ajuste conforme memória e carga |
| Key pair | Crie/selecione uma chave para SSH e guarde o `.pem` |
| VPC/subnet | VPC padrão, subnet pública com rota para Internet Gateway |
| IP público | Habilitado; associe um Elastic IP para estabilizar o DNS |
| Disco | EBS gp3, 16 GiB, criptografado |

Crie um Security Group `tw4y-api-sg` com estas entradas:

| Porta TCP | Origem | Uso |
| --- | --- | --- |
| 22 | Seu IP público `/32` | SSH |
| 80 | `0.0.0.0/0` | Validação automática do certificado e redirecionamento HTTPS |
| 443 | IPs públicos da turma e do instrutor | API pelo navegador |

Mantenha a saída padrão para baixar imagens e emitir certificados. A porta
8000 fica somente na rede privada do Docker. `ALLOWED_CIDRS` aplica também
a restrição no Caddy. Para vários IPs, use regras de SG separadas e uma
lista separada por espaços no `.env.ec2`.

EC2, EBS, IPv4 público e Amplify têm cobrança conforme a conta e o uso.
Confira seus créditos/benefícios no Billing e configure AWS Budgets com
alerta. Um orçamento com alerta não interrompe automaticamente os serviços.

## 3. Instalar Docker e transferir os arquivos

Na sua máquina, substitua o nome da chave e o IP:

```bash
chmod 400 sua-chave.pem
ssh -i sua-chave.pem ubuntu@IP_DA_EC2 'mkdir -p ~/tw4y'
scp -i sua-chave.pem deploy/compose.ec2.yml deploy/Caddyfile \
  deploy/.env.ec2.example deploy/install-docker-ubuntu.sh \
  deploy/backup-sqlite.sh ubuntu@IP_DA_EC2:~/tw4y/
ssh -i sua-chave.pem ubuntu@IP_DA_EC2
```

Na EC2:

```bash
cd ~/tw4y
sudo bash install-docker-ubuntu.sh
sudo usermod -aG docker ubuntu
exit
```

Conecte novamente por SSH para aplicar o grupo `docker` e volte a `~/tw4y`.
O script instala pelo repositório oficial do Docker, incluindo Compose.

## 4. Configurar o domínio e a API

Quando o domínio estiver definido, crie um registro DNS **A** de
`api.seudominio.com` para o Elastic IP da EC2. Aguarde a propagação antes de
iniciar o Caddy. Se houver um registro AAAA, ele também precisa apontar para
uma configuração IPv6 funcional.

Na EC2:

```bash
cd ~/tw4y
cp .env.ec2.example .env.ec2
chmod 600 .env.ec2
nano .env.ec2
```

Preencha:

```dotenv
BACKEND_IMAGE=SEU_USUARIO/tw4y-api:1.0.0
API_DOMAIN=api.seudominio.com
ALLOWED_CIDRS="IP_PUBLICO_DA_TURMA/32 SEU_IP_PUBLICO/32"
SESSION_TTL_DAYS=7
GLOBAL_RATE_LIMIT=120/minute
```

Use os IPs reais, sem os marcadores acima. Caso o repositório no Docker Hub
seja privado, execute `docker login` também na EC2.

```bash
docker compose --env-file .env.ec2 -f compose.ec2.yml pull
docker compose --env-file .env.ec2 -f compose.ec2.yml up -d --wait backend
docker compose --env-file .env.ec2 -f compose.ec2.yml exec backend python -m app.seed
docker compose --env-file .env.ec2 -f compose.ec2.yml up -d
docker compose --env-file .env.ec2 -f compose.ec2.yml ps
```

O seed é explícito e não roda em toda atualização da imagem. Ele popula um
banco vazio e mantém um banco já populado. O Caddy emite/renova o certificado
e só inicia depois de a API estar saudável.

Do seu computador, a partir de um IP permitido:

```bash
curl -fsS https://api.seudominio.com/api/health
curl -fsS https://api.seudominio.com/api/ready
```

Ambos devem retornar `{"status":"ok"}`. `/api/ready` verifica também o banco.
Enquanto o domínio não estiver pronto, você pode iniciar somente `backend`
e checar internamente:

```bash
docker compose --env-file .env.ec2 -f compose.ec2.yml exec backend \
  python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/api/ready').read().decode())"
```

## 5. Publicar o frontend no Amplify

O repositório `twfy-front` contém o código do React, `amplify.yml` e
`amplify-rewrites.json` na raiz. No console Amplify em **us-east-1**:

1. Crie um app de Hosting, conecte o provedor Git e selecione `twfy-front`
   na branch `main`.
2. Mantenha **My app is a monorepo** desmarcado: a aplicação fica na raiz.
3. Não configure `AMPLIFY_MONOREPO_APP_ROOT`; remova a variável se tiver
   sido criada antes para a estrutura com `frontend/`.
4. Configure `VITE_API_URL=https://api.seudominio.com`, **sem `/api` e sem
   barra no final**. Os caminhos do frontend já incluem `/api`.
5. Use o `amplify.yml` da raiz: Node 22, `npm ci`, `npm run build`, saída
   `dist`. Neste workspace, o arquivo está em `frontend/amplify.yml`.
6. Em **Rewrites and redirects**, copie a regra do arquivo
   `amplify-rewrites.json` do repositório frontend para o editor JSON. Ela retorna
   `/index.html` com status 200 nas rotas React, preservando os assets.
7. Publique e teste login, catálogo e acesso direto a `/login`.

`VITE_API_URL` é inserida no JavaScript durante o build. Se alterar a URL,
faça um novo deploy do frontend. O build falha se essa variável não for uma
origem HTTPS. HTTP na API provoca bloqueio de mixed content no site HTTPS.
Variáveis `VITE_*` são públicas; não coloque segredos nelas.

O CORS atual do laboratório aceita o domínio do Amplify. O acesso à API
continua restrito aos IPs permitidos; teste de fora da turma pode falhar
mesmo se o frontend abrir normalmente.

## 6. Atualizar, fazer backup e encerrar a aula

Após publicar uma tag nova, altere `BACKEND_IMAGE` no `.env.ec2` da EC2:

```bash
docker compose --env-file .env.ec2 -f compose.ec2.yml pull backend
docker compose --env-file .env.ec2 -f compose.ec2.yml up -d --wait backend
```

O volume `backend_data` mantém o SQLite entre recriações do container. Para
voltar uma versão, restaure a tag anterior e repita esses comandos. Se uma
versão mudar o esquema do banco, planeje a migração antes do deploy:
`create_all` só cria tabelas ausentes, não altera tabelas existentes.

Na EC2, crie uma cópia consistente do SQLite:

```bash
bash backup-sqlite.sh
```

Copie `~/tw4y/backups/` para sua máquina ou outro armazenamento. O volume
Docker reside no EBS da instância: se a EC2 for terminada e o disco excluído,
o banco será perdido. Parar a EC2 preserva o EBS, que continua sendo cobrado.

Para desligar os containers ao final da aula:

```bash
docker compose --env-file .env.ec2 -f compose.ec2.yml down
```

**Não use `down -v`**: ele exclui o volume do banco e os certificados. Para
reiniciar, use `up -d`. Se precisar resetar os dados entre turmas, o comando
abaixo **apaga os dados atuais** e recria a demonstração:

```bash
docker compose --env-file .env.ec2 -f compose.ec2.yml exec backend python -m app.seed --reset
```

## Diagnóstico

```bash
docker compose --env-file .env.ec2 -f compose.ec2.yml logs --tail=100 backend caddy
```

- **Certificado não emitido:** confira DNS, IP e porta 80 no Security Group.
- **403:** confira o IP público atual e a lista `ALLOWED_CIDRS`.
- **API inacessível:** confira a porta 443 no SG e o healthcheck do backend.
- **Frontend aponta para localhost:** configure `VITE_API_URL` no Amplify e
  execute um novo build.
- **404 ao recarregar uma rota:** aplique `amplify-rewrites.json` do frontend
  no console.
- **`exec format error`:** confirme que publicou ambas as arquiteturas.
- **SQLite sem permissão num volume antigo:** imagens anteriores rodavam
  como root. Faça backup e ajuste o proprietário do volume para UID 10001
  antes de usar a nova imagem.

## Referências

- [Docker: build para múltiplas arquiteturas](https://docs.docker.com/build/building/multi-platform/)
- [Docker Engine no Ubuntu](https://docs.docker.com/engine/install/ubuntu/)
- [Amplify: configuração de monorepo](https://docs.aws.amazon.com/amplify/latest/userguide/monorepo-configuration.html)
- [Amplify: regras de rewrite para SPA](https://docs.aws.amazon.com/amplify/latest/userguide/redirect-rewrite-examples.html)
- [Caddy: HTTPS automático](https://caddyserver.com/docs/automatic-https)
- [EC2: Elastic IP](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/elastic-ip-addresses-eip.html)
- [AWS Budgets](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html)
