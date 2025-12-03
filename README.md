# ⚽ TCC Agent - Assistente de Escrita Acadêmica com IA

**Assistente inteligente para auxiliar na redação de TCC sobre futebol, utilizando Claude AI e base de conhecimento de artigos acadêmicos.**

---

## 📋 Descrição

O **TCC Agent** é uma aplicação desenvolvida para auxiliar estudantes na escrita de Trabalhos de Conclusão de Curso (TCC) na área de futebol. Utilizando inteligência artificial (Claude Sonnet 4.5) e técnicas de RAG (Retrieval Augmented Generation), o sistema:

- 📚 Usa 42 artigos acadêmicos como base de conhecimento
- 🤖 Gera textos acadêmicos de alta qualidade
- 📖 Inclui citações automaticamente no padrão ABNT
- 🎯 Mantém linguagem formal e estrutura acadêmica
- 💾 Salva histórico de gerações
- 📥 Exporta para formato DOCX

---

## 🎯 Funcionalidades

### ✍️ Geração de Texto Acadêmico
- Introdução, Revisão de Literatura, Metodologia, Resultados, Conclusão
- Ajuste de tamanho (100-2000 palavras)
- Controle de tom (formal, equilibrado, direto)
- Citações ABNT automáticas

### 📚 Base de Conhecimento
- 40 artigos de base
- 2 artigos principais de referência
- Busca semântica com ChromaDB
- Download automático do Google Drive

### 🔍 Análise de Citações
- Extração de citações do texto
- Validação de formato ABNT
- Geração de referências bibliográficas
- Sugestões de melhorias

### 💾 Gerenciamento
- Histórico de gerações
- Export para DOCX
- Reindexação de PDFs
- Estatísticas da base

---

## 🛠️ Tecnologias

| Tecnologia | Uso |
|------------|-----|
| **Python 3.11+** | Linguagem principal |
| **Streamlit** | Interface web |
| **Claude API (Anthropic)** | Modelo de linguagem |
| **LangChain** | Orquestração LLM |
| **ChromaDB** | Base vetorial |
| **Sentence Transformers** | Embeddings multilíngues |
| **pdfplumber / PyPDF2** | Extração de PDFs |
| **python-docx** | Export DOCX |

---

## 📁 Estrutura do Projeto

```
TCC_Agent/
├── app.py                      # Interface Streamlit principal
├── requirements.txt            # Dependências
├── .env                        # Variáveis de ambiente (não versionado)
├── .gitignore                 # Arquivos ignorados
├── README.md                   # Este arquivo
│
├── referencias/               # Artigos em PDF
│   ├── base_40/              # 40 artigos de base
│   └── principais_2/         # 2 artigos principais
│
├── vectorstore/              # Base vetorial
│   └── chroma_db/           # ChromaDB persistente
│
├── src/                       # Código-fonte
│   ├── __init__.py
│   ├── pdf_processor.py      # Download e extração de PDFs
│   ├── vector_store.py       # Gerenciamento ChromaDB
│   ├── claude_agent.py       # Integração Claude API
│   ├── citation_manager.py   # Gerenciamento de citações ABNT
│   └── prompts.py            # Templates de prompts
│
└── outputs/                   # Saídas geradas
    └── historico/            # Histórico de textos
```

---

## 🚀 Instalação e Uso

### 1️⃣ Pré-requisitos

- **Python 3.11+** instalado
- **Git** instalado
- **API Key do Claude** (Anthropic)

### 2️⃣ Instalação

```bash
# Clone ou navegue até o diretório
cd /Users/bruno/Projects/TCC_Agent

# Crie ambiente virtual
python -m venv venv

# Ative o ambiente virtual
# No macOS/Linux:
source venv/bin/activate
# No Windows:
venv\Scripts\activate

# Instale as dependências
pip install -r requirements.txt
```

### 3️⃣ Configuração

O arquivo `.env` já está configurado com:

```env
ANTHROPIC_API_KEY=sua_chave_aqui
GOOGLE_DRIVE_FOLDER_40=ID_pasta_40_artigos
GOOGLE_DRIVE_FOLDER_2=ID_pasta_2_artigos
```

### 4️⃣ Primeira Execução

```bash
# Rode a aplicação
streamlit run app.py
```

A aplicação abrirá em `http://localhost:8501`

### 5️⃣ Setup Inicial (na interface)

1. **Baixar PDFs**: Clique em "📥 Baixar PDFs do Drive" na sidebar
2. **Indexar**: Clique em "🔄 Reindexar PDFs" (primeira vez)
3. **Aguarde**: O processo pode levar alguns minutos
4. **Pronto**: Quando o status mostrar "✅ X chunks indexados"

---

## 📖 Como Usar

### Geração de Texto Básica

1. **Digite sua solicitação** na área de texto:
   ```
   Escreva uma introdução sobre a importância da análise tática
   no futebol moderno, contextualizando com o avanço da tecnologia.
   ```

2. **Configure os parâmetros** na sidebar:
   - Tipo de seção (Introdução, Revisão, etc.)
   - Tamanho (palavras)
   - Estilo (formal, equilibrado, direto)
   - Base de conhecimento (todos, principais, base)

3. **Clique em "🚀 Gerar Texto"**

4. **Aguarde**: O Claude irá processar sua solicitação

5. **Resultado**: O texto aparecerá formatado com citações ABNT

### Exemplos de Prompts

#### 📌 Para Introdução:
```
Escreva uma introdução para um TCC sobre análise de desempenho no futebol,
abordando a evolução das métricas táticas nos últimos anos.
```

#### 📌 Para Revisão de Literatura:
```
Desenvolva uma revisão de literatura sobre os principais modelos de análise
tática no futebol, citando pelo menos 5 estudos relevantes.
```

#### 📌 Para Metodologia:
```
Descreva uma metodologia quantitativa para análise de indicadores de
desempenho em partidas de futebol profissional.
```

#### 📌 Para Resultados:
```
Discuta como a posse de bola se relaciona com o sucesso das equipes,
fundamentando com os estudos da base de conhecimento.
```

#### 📌 Para Conclusão:
```
Escreva uma conclusão sintetizando a importância da análise de dados
no futebol contemporâneo e sugerindo pesquisas futuras.
```

---

## 🎛️ Parâmetros Disponíveis

### Tipo de Seção
- **Genérico**: Texto livre
- **Introdução**: Contextualização → Problema → Objetivos
- **Revisão**: Fundamentação teórica
- **Metodologia**: Descrição de métodos
- **Resultados**: Análise e discussão
- **Conclusão**: Síntese e perspectivas

### Tamanho
- Mínimo: 100 palavras
- Máximo: 2000 palavras
- Padrão: 500 palavras

### Estilo
- **🎩 Formal**: Máxima formalidade acadêmica
- **⚖️ Equilibrado**: Formal mas acessível
- **🎯 Direto**: Objetivo e conciso

### Base de Conhecimento
- **📚 Todos**: 42 artigos (40 base + 2 principais)
- **⭐ Principais**: Apenas 2 artigos principais
- **📖 Base**: Apenas 40 artigos base

### Chunks de Contexto
- 3-15 trechos relevantes
- Padrão: 5 chunks
- Mais chunks = mais contexto, mas pode ser redundante

---

## 📊 Análise de Citações

Após gerar um texto, clique em **"🔍 Analisar Citações"** para:

✅ **Ver citações extraídas**:
- Lista de todos os autores citados
- Anos de publicação
- Formato das citações

✅ **Receber sugestões**:
- Densidade de citações (recomendado: 1 a cada 100 palavras)
- Diversidade de fontes
- Validação de formato ABNT
- Detecção de citações diretas sem página

---

## 💾 Salvamento e Export

### Salvar Histórico
- Clique em **"💾 Salvar Histórico"**
- Arquivo salvo em `outputs/historico/`
- Nome: `output_YYYYMMDD_HHMMSS.txt`
- Inclui timestamp e solicitação original

### Export para DOCX
- Clique em **"📥 Export DOCX"**
- Arquivo salvo em `outputs/`
- Formatação: Times New Roman, 12pt, justificado
- Compatível com Word e LibreOffice

---

## 🔧 Gerenciamento da Base

### Reindexar PDFs
Use quando:
- Adicionar novos artigos
- Atualizar artigos existentes
- Após erros na indexação

**Processo**:
1. Adicione PDFs em `referencias/base_40/` ou `referencias/principais_2/`
2. Clique em **"🔄 Reindexar PDFs"**
3. Aguarde o processamento (pode levar minutos)

### Limpar Base Vetorial
⚠️ **CUIDADO**: Remove todos os embeddings

Use quando:
- Quiser recomeçar do zero
- Base corrompida
- Após mudanças significativas nos PDFs

---

## 📚 Citações ABNT - Referência Rápida

### Citação Direta Curta (até 3 linhas)
```
De acordo com Silva (2022, p. 45), "a análise tática é fundamental".
```

### Citação Direta Longa (mais de 3 linhas)
```
[recuo 4cm, fonte menor, sem aspas]
A análise tática representa um dos pilares fundamentais para
compreensão do jogo moderno, permitindo identificar padrões e
tendências que influenciam diretamente os resultados (SILVA, 2022, p. 45).
```

### Citação Indireta (paráfrase)
```
Estudos recentes demonstram a importância da posse de bola (OLIVEIRA, 2023).
```

### Múltiplos Autores
- 1 autor: `Silva (2022)`
- 2 autores: `Silva e Oliveira (2022)`
- 3+ autores: `Silva et al. (2022)`

### Referências
```
AUTOR, A. A. Título do artigo. Nome da Revista, v. X, n. X, p. X-X, ano.

AUTOR, A. A. Título do livro. Edição. Local: Editora, ano.
```

---

## 🧪 Testando Módulos Individualmente

### Testar PDF Processor
```bash
cd /Users/bruno/Projects/TCC_Agent
python -m src.pdf_processor
```

### Testar Vector Store
```bash
python -m src.vector_store
```

### Testar Claude Agent
```bash
python -m src.claude_agent
```

### Testar Citation Manager
```bash
python -m src.citation_manager
```

---

## ❓ Troubleshooting

### Erro: "API key do Claude não encontrada"
**Solução**: Verifique se o arquivo `.env` existe e contém `ANTHROPIC_API_KEY`

### Erro ao baixar PDFs do Google Drive
**Soluções possíveis**:
1. Verifique se as pastas estão compartilhadas publicamente
2. Confirme os IDs das pastas no `.env`
3. Verifique sua conexão de internet
4. Alternativa: Baixe manualmente e coloque em `referencias/`

### Base vetorial vazia
**Solução**:
1. Certifique-se de que há PDFs em `referencias/`
2. Clique em "🔄 Reindexar PDFs"
3. Aguarde conclusão do processo

### Texto gerado sem citações
**Soluções**:
1. Marque "Incluir citações" na sidebar
2. Aumente número de "Chunks de contexto"
3. Seja mais específico na solicitação
4. Verifique se a base foi indexada corretamente

### Aplicação lenta
**Otimizações**:
1. Reduza número de chunks de contexto
2. Use filtro de categoria (apenas principais ou apenas base)
3. Reduza tamanho do texto solicitado
4. Verifique uso de RAM (ChromaDB carrega em memória)

---

## 📈 Boas Práticas

### ✅ Para Melhores Resultados:

1. **Seja específico**: Quanto mais detalhada a solicitação, melhor o resultado
2. **Use tipo de seção apropriado**: Cada tipo tem prompt otimizado
3. **Ajuste tamanho gradualmente**: Comece com 300-500 palavras
4. **Revise e refine**: Use o texto gerado como base, não como produto final
5. **Combine gerações**: Gere múltiplos parágrafos e combine manualmente
6. **Verifique citações**: Sempre confira se as citações existem nos artigos

### ❌ Evite:

1. Prompts muito vagos ("escreva sobre futebol")
2. Solicitar textos muito longos (>1500 palavras) de uma vez
3. Copiar texto gerado sem revisão
4. Confiar 100% nas citações sem verificar
5. Usar categoria errada de seção

---

## 🔐 Segurança e Privacidade

- ✅ Todos os dados ficam locais (exceto requisições à API)
- ✅ PDFs não são enviados para Claude (apenas trechos relevantes)
- ✅ API key armazenada apenas localmente em `.env`
- ✅ Histórico salvo apenas no seu computador
- ⚠️ Não versione o arquivo `.env` no Git

---

## 📝 Limitações

- O sistema gera texto baseado nos 42 artigos fornecidos
- Citações podem precisar de revisão e ajuste manual
- Não substitui leitura completa dos artigos
- Requer conexão com internet (Claude API)
- Limite de tokens por requisição (4096)

---

## 🚀 Melhorias Futuras

- [ ] Suporte a mais formatos de citação (APA, Chicago)
- [ ] Export para LaTeX
- [ ] Modo de chat interativo
- [ ] Refinamento iterativo de texto
- [ ] Análise de plágio
- [ ] Geração de gráficos e tabelas
- [ ] Integração com Mendeley/Zotero
- [ ] Suporte a voz (ditado)
- [ ] Modo offline com modelos locais

---

## 🤝 Contribuindo

Este é um projeto pessoal para auxílio em TCC. Sugestões e melhorias são bem-vindas!

---

## 📄 Licença

Projeto acadêmico - Uso educacional

---

## 👨‍💻 Autor

**Bruno**
📧 Contato: [seu-email]
🎓 TCC sobre Futebol

---

## 🙏 Agradecimentos

- **Anthropic** - Claude AI
- **LangChain** - Framework LLM
- **Streamlit** - Interface
- **ChromaDB** - Vector store
- **Comunidade Python** - Bibliotecas open source

---

**⚽ Boa sorte com seu TCC! 🎓**

---

*Última atualização: Novembro 2024*
