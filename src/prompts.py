"""
Prompts simplificados para o assistente acadêmico.
Reduzido de 402 para 50 linhas - templates unificados.
"""

# System prompt base (usado no core.py)
SYSTEM_PROMPT = """Assistente especializado em TCC sobre futebol.
Hierarquia obrigatória: Metodologia > Principais > Base.
Sempre use formato ABNT para citações."""

# Template genérico (para contexto + solicitação)
GENERIC_TEMPLATE = """{context}

SOLICITAÇÃO DO USUÁRIO:
{request}"""

# Template de refinamento (para feedback iterativo)
REFINEMENT_TEMPLATE = """TEXTO ANTERIOR:
{previous_text}

FEEDBACK DO USUÁRIO:
{feedback}

Por favor, refine o texto considerando o feedback acima."""

# Exemplos de uso (para documentação)
USAGE_EXAMPLES = {
    "introducao": "Escreva uma introdução sobre análise tática no futebol",
    "metodologia": "Descreva o método GPET de Garcia Lopez",
    "resultados": "Apresente resultados sobre posse de bola",
    "conclusao": "Conclua sobre a importância da análise tática",
}

# Instruções por tipo de seção
SECTION_INSTRUCTIONS = {
    "generico": "Escreva um texto acadêmico de alta qualidade.",
    "introducao": """Escreva uma INTRODUÇÃO acadêmica com a seguinte estrutura:
1. Contextualização do tema (panorama geral)
2. Problematização (lacuna ou questão a ser abordada)
3. Justificativa (relevância do estudo)
4. Objetivos (geral e específicos)""",
    "revisao": """Escreva uma REVISÃO DE LITERATURA acadêmica:
1. Organize por temas/conceitos principais
2. Apresente diferentes perspectivas teóricas
3. Relacione os estudos entre si
4. Identifique consensos e divergências na literatura""",
    "metodologia": """Descreva a METODOLOGIA de forma detalhada:
1. Tipo de pesquisa (qualitativa, quantitativa, mista)
2. Procedimentos de coleta de dados
3. Instrumentos utilizados
4. Procedimentos de análise""",
    "resultados": """Apresente os RESULTADOS E DISCUSSÃO:
1. Apresente os dados/achados principais
2. Relacione com a literatura revisada
3. Discuta implicações práticas e teóricas
4. Compare com estudos anteriores""",
    "conclusao": """Escreva uma CONCLUSÃO acadêmica:
1. Retome os objetivos do trabalho
2. Sintetize os principais achados
3. Apresente contribuições do estudo
4. Sugira pesquisas futuras
5. Reconheça limitações (se aplicável)"""
}

# Mapa de tons
TONE_MAP = {
    "formal": "Use linguagem extremamente formal e acadêmica, evitando qualquer coloquialismo.",
    "equilibrado": "Use linguagem formal mas acessível, equilibrando rigor acadêmico com clareza.",
    "direto": "Seja objetivo e conciso, mantendo formalidade mas priorizando clareza e brevidade."
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
        section_type: Tipo de seção ('introducao', 'revisao', 'metodologia', 'resultados', 'conclusao', 'generico')
        context: Contexto da base de conhecimento
        user_request: Solicitação do usuário
        word_count: Número aproximado de palavras
        tone: Tom do texto ('formal', 'equilibrado', 'direto')
        include_citations: Se deve incluir citações ABNT

    Returns:
        Prompt formatado
    """
    section_instruction = SECTION_INSTRUCTIONS.get(section_type, SECTION_INSTRUCTIONS["generico"])
    tone_instruction = TONE_MAP.get(tone, TONE_MAP["formal"])

    citation_instruction = ""
    if include_citations:
        citation_instruction = """
CITAÇÕES (OBRIGATÓRIO):
- Use citações indiretas no formato: (SOBRENOME, ano)
- Use citações diretas curtas entre aspas com página: "texto" (SOBRENOME, ano, p. X)
- Priorize citações dos artigos fornecidos no contexto
- Mantenha densidade de aproximadamente 1 citação a cada 100 palavras
- IMPORTANTE: Só cite autores que aparecem no contexto fornecido"""

    prompt = f"""CONTEXTO DA BASE DE CONHECIMENTO:
{context}

INSTRUÇÕES:
{section_instruction}

{tone_instruction}

Tamanho aproximado: {word_count} palavras.
{citation_instruction}

SOLICITAÇÃO DO USUÁRIO:
{user_request}

Gere o texto acadêmico seguindo todas as instruções acima."""

    return prompt


def get_refinement_prompt(original_text: str, refinement_request: str) -> str:
    """
    Gera prompt para refinamento de texto.

    Args:
        original_text: Texto original a ser refinado
        refinement_request: Solicitação de refinamento do usuário

    Returns:
        Prompt de refinamento
    """
    return f"""TEXTO ORIGINAL:
{original_text}

SOLICITAÇÃO DE REFINAMENTO:
{refinement_request}

Por favor, refine o texto considerando a solicitação acima.
Mantenha o padrão acadêmico, as citações existentes e a coerência geral.
Se necessário, adicione ou ajuste citações no formato ABNT."""


def get_citation_extraction_prompt(text: str) -> str:
    """
    Gera prompt para extração de citações.

    Args:
        text: Texto para extrair citações

    Returns:
        Prompt de extração
    """
    return f"""Analise o seguinte texto acadêmico e extraia todas as citações:

TEXTO:
{text}

TAREFA:
1. Liste todas as citações encontradas (diretas e indiretas)
2. Para cada citação, informe:
   - Autor(es)
   - Ano
   - Tipo (direta ou indireta)
   - Se direta, a página (se disponível)
3. Gere as referências bibliográficas no formato ABNT
4. Identifique possíveis problemas de formatação

Formato da resposta:
## Citações Encontradas
[lista de citações]

## Referências Bibliográficas (ABNT)
[referências formatadas]

## Observações
[problemas ou sugestões]"""


def get_methodology_check_prompt(text: str, methodology_title: str) -> str:
    """
    Gera prompt para verificar se a metodologia foi citada corretamente.

    Args:
        text: Texto a verificar
        methodology_title: Título/nome da metodologia esperada

    Returns:
        Prompt de verificação
    """
    return f"""Analise o seguinte texto e verifique se a metodologia "{methodology_title}" foi mencionada e citada corretamente:

TEXTO:
{text}

VERIFICAR:
1. A metodologia "{methodology_title}" é mencionada?
2. Se sim, está citada corretamente no formato ABNT?
3. A descrição da metodologia está precisa?
4. Há erros ou inconsistências?

Responda em formato estruturado."""


def get_regenerate_prompt(
    original_request: str,
    context: str,
    problems: str,
    recommendations: str
) -> str:
    """
    Gera prompt para regeneração de texto com correções.

    Args:
        original_request: Solicitação original do usuário
        context: Contexto da base de conhecimento
        problems: Problemas identificados no texto anterior
        recommendations: Recomendações de melhoria

    Returns:
        Prompt de regeneração
    """
    return f"""CONTEXTO DA BASE DE CONHECIMENTO:
{context}

SOLICITAÇÃO ORIGINAL:
{original_request}

PROBLEMAS IDENTIFICADOS NO TEXTO ANTERIOR:
{problems}

RECOMENDAÇÕES:
{recommendations}

Por favor, gere um NOVO texto que:
1. Atenda à solicitação original
2. Corrija todos os problemas identificados
3. Siga as recomendações fornecidas
4. Use citações ABNT corretamente
5. Mantenha alta qualidade acadêmica

Gere o texto corrigido:"""
