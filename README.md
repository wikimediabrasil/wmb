<img src="https://img.shields.io/github/issues/WikiMovimentoBrasil/wmb?style=for-the-badge"/> <img src="https://img.shields.io/github/license/WikiMovimentoBrasil/wmb?style=for-the-badge"/> <img src="https://img.shields.io/github/languages/top/WikiMovimentoBrasil/wmb?style=for-the-badge"/>
<h1 align="center">WMB</h1> 
<p align="center">Esta aplicação tem como objetivo executar tarefas administrativas do grupo de usuários Wiki Movimento Brasil</p>
<p align="center">A ferramenta em execução pode ser encontrada em https://wmb.toolforge.org</p>

<h2>Instalação</h2>
<p>Para rodar este programa, é necessário criar algumas tabelas de bancos de dados, nomeadamente <i>wmb_admin</i> e <i>users</i>.</p>
Para criá-las, basta, no terminal de Python, executar os seguintes comandos:
<pre>
from app import db
db.create_all()
</pre>

Seguido da criação de um usuário admin. Por exemplo:
<pre>
from app import WMBUser, generate_password_hash
admin = WMBUser(username="username",email="email@email.com",password=generate_password_hash("password", method='sha256'))
db.session.add(admin)
db.session.commit()
</pre>