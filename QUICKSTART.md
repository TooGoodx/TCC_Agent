# 🚀 Guia de Início Rápido - TCC Agent

## ⏱️ 5 Minutos para Começar

### 1️⃣ Instalar Dependências (2 min)

```bash
# Navegue até o diretório
cd /Users/bruno/Projects/TCC_Agent

# Crie ambiente virtual
python3 -m venv venv

# Ative o ambiente
source venv/bin/activate

# Instale dependências
pip install -r requirements.txt
```

⏳ **Aguarde**: Instalação pode levar 2-3 minutos

---

### 2️⃣ Iniciar Aplicação (10 seg)

```bash
streamlit run app.py
```

✅ Aplicação abrirá automaticamente em `http://localhost:8501`

---

### 3️⃣ Setup Inicial na Interface (2-3 min)

**Na primeira vez:**

1. Na sidebar, clique em **"📥 Baixar PDFs do Drive"**
   - ⏳ Aguarde download (pode levar 1-2 min)

2. Depois, clique em **"🔄 Reindexar PDFs"**
   - ⏳ Aguarde processamento e criação de embeddings (1-2 min)

3. Quando aparecer **"✅ X chunks indexados"** → Pronto!

---

### 4️⃣ Primeiro Teste (1 min)

**Digite na área de texto:**
```
Escreva um parágrafo sobre a importância da análise tática no futebol moderno.
```

**Clique em: 🚀 Gerar Texto**

⏳ Aguarde 10-20 segundos

✅ **Sucesso!** Texto acadêmico com citações ABNT será gerado!

---

## 🎯 Próximos Passos

Agora você pode:

- 📝 Gerar diferentes seções do TCC (Introdução, Revisão, etc.)
- 🎛️ Ajustar parâmetros na sidebar
- 💾 Salvar histórico
- 📥 Exportar para DOCX
- 🔍 Analisar citações

---

## ❓ Problemas?

### Erro de instalação?
```bash
# Tente atualizar pip
pip install --upgrade pip

# Reinstale
pip install -r requirements.txt
```

### Erro ao baixar PDFs?
- Verifique conexão com internet
- Certifique-se que pastas do Google Drive estão públicas
- Alternativa: Baixe manualmente e coloque em `referencias/`

### Streamlit não abre?
```bash
# Abra manualmente
open http://localhost:8501
```

---

## 📚 Documentação Completa

Veja [README.md](README.md) para:
- Funcionalidades detalhadas
- Exemplos de prompts
- Boas práticas
- Troubleshooting completo

---

**Boa sorte com seu TCC!** ⚽🎓
