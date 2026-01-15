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
