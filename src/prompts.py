"""
Templates de prompts para o assistente acadêmico.
"""

# System prompt base para o Claude
SYSTEM_PROMPT = """Você é um assistente acadêmico especializado em redação de TCC (Trabalho de Conclusão de Curso) na área de futebol.

Sua função é auxiliar na escrita de textos acadêmicos de alta qualidade, seguindo rigorosamente:

1. **Padrão ABNT**: Use normas brasileiras para citações e referências
2. **Linguagem formal e acadêmica**: Tom objetivo, impessoal, técnico
3. **Embasamento teórico**: Sempre cite os artigos fornecidos no contexto
4. **Coerência**: Mantenha conexão lógica entre ideias
5. **Precisão**: Use terminologia técnica correta da área

## Formato de Citações:

**Citação direta curta (até 3 linhas):**
De acordo com Silva (2022, p. 45), "a análise tática é fundamental para compreender o jogo moderno".

**Citação direta longa (mais de 3 linhas):**
[recuo de 4cm, fonte 10, sem aspas]

**Citação indireta (paráfrase):**
A literatura aponta que a posse de bola influencia diretamente o resultado das partidas (OLIVEIRA; SANTOS, 2023).

**Múltiplos autores:**
- 1 autor: Silva (2022)
- 2 autores: Silva e Oliveira (2022)
- 3+ autores: Silva et al. (2022)

## Estrutura do Texto:

- **Introdução**: Contextualização → Problema → Objetivos
- **Desenvolvimento**: Fundamentação teórica → Análise → Discussão
- **Conclusão**: Síntese → Contribuições → Limitações → Perspectivas

## Diretrizes Importantes:

✅ **SEMPRE**:
- Base suas respostas nos artigos fornecidos no contexto
- Inclua citações para fundamentar afirmações
- Use linguagem formal (evite: "você", "a gente", gírias)
- Seja objetivo e direto
- Mantenha coerência temporal e conceitual
- Cite múltiplas fontes quando relevante

❌ **NUNCA**:
- Invente citações ou autores
- Use linguagem coloquial
- Faça afirmações sem fundamentação
- Copie trechos integralmente sem indicar citação direta
- Use opiniões pessoais sem embasamento teórico

Quando não tiver certeza sobre uma informação específica nos artigos, indique isso claramente e sugira pesquisa adicional."""


# Templates para diferentes tipos de seção do TCC

INTRO_TEMPLATE = """Você está escrevendo a INTRODUÇÃO do TCC.

A introdução deve conter:
1. Contextualização do tema (panorama geral)
2. Delimitação do problema de pesquisa
3. Justificativa (relevância do estudo)
4. Objetivos (geral e específicos)

Contexto dos artigos:
{context}

Solicitação do usuário:
{user_request}

Escreva uma introdução acadêmica bem estruturada, com aproximadamente {word_count} palavras."""


REVISAO_LITERATURA_TEMPLATE = """Você está escrevendo a REVISÃO DE LITERATURA / FUNDAMENTAÇÃO TEÓRICA do TCC.

Esta seção deve:
1. Apresentar conceitos fundamentais
2. Discutir teorias e modelos relevantes
3. Sintetizar achados de estudos anteriores
4. Identificar lacunas na literatura
5. Estabelecer base teórica para o trabalho

Contexto dos artigos:
{context}

Solicitação do usuário:
{user_request}

Escreva um texto acadêmico bem fundamentado, com aproximadamente {word_count} palavras, citando múltiplas fontes."""


METODOLOGIA_TEMPLATE = """Você está escrevendo a METODOLOGIA do TCC.

Esta seção deve descrever:
1. Tipo de pesquisa (qualitativa/quantitativa/mista)
2. Procedimentos de coleta de dados
3. Instrumentos utilizados
4. Critérios de seleção (amostra/corpus)
5. Técnicas de análise

Contexto dos artigos:
{context}

Solicitação do usuário:
{user_request}

Escreva uma metodologia clara e replicável, com aproximadamente {word_count} palavras."""


RESULTADOS_TEMPLATE = """Você está escrevendo a seção de RESULTADOS E DISCUSSÃO do TCC.

Esta seção deve:
1. Apresentar os achados de forma clara
2. Discutir à luz da teoria (artigos de referência)
3. Comparar com estudos anteriores
4. Interpretar significados e implicações
5. Reconhecer limitações quando relevante

Contexto dos artigos:
{context}

Solicitação do usuário:
{user_request}

Escreva uma análise acadêmica rigorosa, com aproximadamente {word_count} palavras."""


CONCLUSAO_TEMPLATE = """Você está escrevendo a CONCLUSÃO do TCC.

A conclusão deve:
1. Retomar os objetivos do trabalho
2. Sintetizar os principais achados
3. Destacar contribuições do estudo
4. Reconhecer limitações
5. Sugerir perspectivas para pesquisas futuras

Contexto dos artigos:
{context}

Solicitação do usuário:
{user_request}

Escreva uma conclusão concisa e impactante, com aproximadamente {word_count} palavras."""


GENERIC_TEMPLATE = """Contexto dos artigos acadêmicos:
{context}

Solicitação do usuário:
{user_request}

Instruções de estilo:
- Tom: {tone}
- Comprimento aproximado: {word_count} palavras
- Incluir citações: {include_citations}

Escreva um texto acadêmico de qualidade, fundamentado nos artigos fornecidos."""


# Mapeamento de tipos de seção
SECTION_TEMPLATES = {
    'introducao': INTRO_TEMPLATE,
    'revisao': REVISAO_LITERATURA_TEMPLATE,
    'metodologia': METODOLOGIA_TEMPLATE,
    'resultados': RESULTADOS_TEMPLATE,
    'conclusao': CONCLUSAO_TEMPLATE,
    'generico': GENERIC_TEMPLATE
}


def get_prompt(
    section_type: str,
    context: str,
    user_request: str,
    word_count: int = 500,
    tone: str = "formal",
    include_citations: bool = True
) -> str:
    """
    Gera o prompt completo para o Claude.

    Args:
        section_type: Tipo de seção ('introducao', 'revisao', 'metodologia', etc.)
        context: Contexto recuperado da base vetorial
        user_request: Solicitação do usuário
        word_count: Número aproximado de palavras
        tone: Tom do texto ('formal', 'equilibrado', 'direto')
        include_citations: Se deve incluir citações

    Returns:
        Prompt formatado
    """
    template = SECTION_TEMPLATES.get(section_type, GENERIC_TEMPLATE)

    prompt = template.format(
        context=context,
        user_request=user_request,
        word_count=word_count,
        tone=tone,
        include_citations="Sim" if include_citations else "Não"
    )

    return prompt


def get_refinement_prompt(original_text: str, refinement_request: str) -> str:
    """
    Gera prompt para refinamento de texto já gerado.

    Args:
        original_text: Texto original a ser refinado
        refinement_request: Solicitação de refinamento

    Returns:
        Prompt de refinamento
    """
    return f"""Você está refinando um texto acadêmico já escrito.

TEXTO ORIGINAL:
{original_text}

SOLICITAÇÃO DE REFINAMENTO:
{refinement_request}

Por favor, refine o texto mantendo o padrão acadêmico e a qualidade das citações."""


def get_citation_extraction_prompt(text: str) -> str:
    """
    Gera prompt para extrair e formatar citações de um texto.

    Args:
        text: Texto para extrair citações

    Returns:
        Prompt de extração
    """
    return f"""Analise o texto abaixo e extraia todas as citações no formato ABNT.

TEXTO:
{text}

Liste todas as referências citadas no formato:
AUTOR, A. A. Título da obra. Local: Editora, Ano.

Organize em ordem alfabética."""


# Exemplos de uso para o usuário
USAGE_EXAMPLES = """
## 📚 Exemplos de Prompts:

**Para Introdução:**
"Escreva uma introdução sobre a importância da análise tática no futebol moderno, contextualizando com o avanço da tecnologia."

**Para Revisão de Literatura:**
"Explique os principais modelos de análise de desempenho no futebol, citando estudos relevantes."

**Para Metodologia:**
"Descreva uma metodologia para análise quantitativa de indicadores táticos em partidas de futebol."

**Para Resultados:**
"Discuta como a posse de bola se relaciona com o sucesso das equipes, fundamentando com os artigos."

**Para Conclusão:**
"Escreva uma conclusão sintetizando a importância da análise de dados no futebol contemporâneo."

**Geral:**
"Desenvolva um parágrafo sobre [tema específico], incluindo citações de pelo menos 3 autores diferentes."
"""
