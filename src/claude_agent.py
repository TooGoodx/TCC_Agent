"""
Integração com Claude API para geração de texto acadêmico.
"""
import os
from typing import Generator, Dict, Optional
from anthropic import Anthropic
from dotenv import load_dotenv
from src.prompts import (
    SYSTEM_PROMPT,
    get_prompt,
    get_refinement_prompt,
    get_citation_extraction_prompt
)
from src.vector_store import VectorStore


class ClaudeAgent:
    """Agente que integra Claude API com a base de conhecimento."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Inicializa o agente Claude.

        Args:
            api_key: Chave da API Anthropic (se None, carrega do .env)
        """
        load_dotenv()

        # Try Streamlit secrets first (for cloud), then .env (for local)
        try:
            import streamlit as st
            self.api_key = api_key or st.secrets.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        except (ImportError, AttributeError, FileNotFoundError):
            # Fallback to .env if not in Streamlit context
            self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")

        if not self.api_key:
            raise ValueError("API key do Claude não encontrada. Configure ANTHROPIC_API_KEY no .env ou Streamlit secrets")

        self.client = Anthropic(api_key=self.api_key)
        self.vector_store = VectorStore()

        # Configurações padrão
        self.model = "claude-sonnet-4-5-20250929"  # Modelo mais recente
        self.max_tokens = 4096
        self.temperature = 0.7

    def generate_text(
        self,
        user_request: str,
        section_type: str = "generico",
        word_count: int = 500,
        tone: str = "formal",
        include_citations: bool = True,
        category_filter: Optional[str] = None,
        n_context_chunks: int = 5,
        stream: bool = False
    ) -> str | Generator:
        """
        Gera texto acadêmico baseado na solicitação do usuário.

        Args:
            user_request: Solicitação do usuário
            section_type: Tipo de seção ('introducao', 'revisao', etc.)
            word_count: Número aproximado de palavras
            tone: Tom do texto ('formal', 'equilibrado', 'direto')
            include_citations: Se deve incluir citações
            category_filter: Filtrar contexto por categoria ('base_40', 'principais_2')
            n_context_chunks: Número de chunks de contexto a usar
            stream: Se True, retorna generator para streaming

        Returns:
            Texto gerado (ou generator se stream=True)
        """
        # Busca contexto relevante na base vetorial
        print(f"🔍 Buscando contexto relevante para: '{user_request[:50]}...'")

        context = self.vector_store.get_context_for_prompt(
            query=user_request,
            n_results=n_context_chunks,
            category_filter=category_filter
        )

        # Gera o prompt
        user_prompt = get_prompt(
            section_type=section_type,
            context=context,
            user_request=user_request,
            word_count=word_count,
            tone=tone,
            include_citations=include_citations
        )

        # Chama Claude API
        if stream:
            return self._generate_stream(user_prompt)
        else:
            return self._generate_complete(user_prompt)

    def _generate_complete(self, user_prompt: str) -> str:
        """Gera texto completo (não-streaming)."""
        print("🤖 Gerando texto com Claude...")

        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )

        generated_text = response.content[0].text
        print("✅ Texto gerado com sucesso!")

        return generated_text

    def _generate_stream(self, user_prompt: str) -> Generator:
        """Gera texto em streaming."""
        print("🤖 Iniciando geração em streaming...")

        with self.client.messages.stream(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        ) as stream:
            for text in stream.text_stream:
                yield text

    def refine_text(
        self,
        original_text: str,
        refinement_request: str,
        stream: bool = False
    ) -> str | Generator:
        """
        Refina um texto já gerado.

        Args:
            original_text: Texto original
            refinement_request: Solicitação de refinamento
            stream: Se True, retorna generator

        Returns:
            Texto refinado (ou generator se stream=True)
        """
        prompt = get_refinement_prompt(original_text, refinement_request)

        if stream:
            return self._generate_stream(prompt)
        else:
            return self._generate_complete(prompt)

    def extract_citations(self, text: str) -> str:
        """
        Extrai e formata citações de um texto.

        Args:
            text: Texto para extrair citações

        Returns:
            Lista de referências formatadas em ABNT
        """
        prompt = get_citation_extraction_prompt(text)

        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            temperature=0.3,  # Mais determinístico para extração
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        return response.content[0].text

    def continue_text(
        self,
        existing_text: str,
        continuation_request: str,
        stream: bool = False
    ) -> str | Generator:
        """
        Continua um texto existente.

        Args:
            existing_text: Texto existente
            continuation_request: Como continuar
            stream: Se True, retorna generator

        Returns:
            Continuação do texto (ou generator se stream=True)
        """
        prompt = f"""TEXTO EXISTENTE:
{existing_text}

SOLICITAÇÃO DE CONTINUAÇÃO:
{continuation_request}

Continue o texto mantendo coerência, estilo e padrão acadêmico."""

        if stream:
            return self._generate_stream(prompt)
        else:
            return self._generate_complete(prompt)

    def summarize_articles(
        self,
        category: Optional[str] = None,
        max_articles: int = 5
    ) -> str:
        """
        Gera resumo dos artigos da base de conhecimento.

        Args:
            category: Categoria dos artigos ('base_40' ou 'principais_2')
            max_articles: Número máximo de artigos a resumir

        Returns:
            Resumo dos artigos
        """
        # Busca documentos da categoria
        results = self.vector_store.search(
            query="resumo principais conceitos metodologia",
            n_results=max_articles * 3,  # Pega mais chunks
            category_filter=category
        )

        # Agrupa por arquivo
        articles = {}
        for result in results:
            filename = result['metadata']['filename']
            if filename not in articles:
                articles[filename] = []
            articles[filename].append(result['document'])

        # Limita número de artigos
        articles = dict(list(articles.items())[:max_articles])

        # Monta contexto
        context_parts = []
        for filename, chunks in articles.items():
            context_parts.append(f"--- {filename} ---")
            context_parts.append(" ".join(chunks[:2]))  # Primeiros 2 chunks
            context_parts.append("")

        context = "\n".join(context_parts)

        # Gera resumo
        prompt = f"""Analise os seguintes trechos de artigos acadêmicos e forneça um resumo estruturado:

{context}

Forneça um resumo que inclua:
1. Principais temas abordados
2. Metodologias utilizadas
3. Conceitos-chave
4. Autores e referências

Formato: lista organizada por tópicos."""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            temperature=0.5,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        return response.content[0].text

    def get_usage_suggestions(self) -> str:
        """
        Retorna sugestões de uso baseadas nos artigos indexados.

        Returns:
            String com sugestões
        """
        # Busca tópicos diversos
        topics = [
            "análise tática",
            "metodologia",
            "desempenho",
            "tecnologia",
            "treinamento"
        ]

        found_topics = []
        for topic in topics:
            results = self.vector_store.search(topic, n_results=1)
            if results:
                found_topics.append(topic)

        suggestions = f"""📚 **Sugestões baseadas nos artigos indexados:**

Os artigos em sua base de conhecimento cobrem os seguintes tópicos:
{', '.join(found_topics)}

Você pode pedir coisas como:
- "Escreva uma introdução sobre {found_topics[0] if found_topics else 'análise tática'}"
- "Desenvolva um parágrafo sobre a relação entre {found_topics[0] if found_topics else 'tática'} e {found_topics[1] if len(found_topics) > 1 else 'desempenho'}"
- "Explique as metodologias de {found_topics[0] if found_topics else 'análise'} citando estudos"
- "Faça uma revisão de literatura sobre {found_topics[2] if len(found_topics) > 2 else 'futebol moderno'}"

💡 **Dica**: Seja específico em sua solicitação para resultados mais precisos!
"""
        return suggestions


if __name__ == "__main__":
    # Teste do agente
    agent = ClaudeAgent()

    # Teste básico
    print("\n🧪 Teste do Claude Agent\n")

    # Verifica se vector store está pronto
    stats = agent.vector_store.get_stats()
    if not stats['ready']:
        print("⚠️ Base vetorial não está pronta. Execute o processamento dos PDFs primeiro.")
    else:
        print(f"✅ Base vetorial pronta com {stats['total_chunks']} chunks")

        # Teste de geração
        test_request = "Escreva um parágrafo sobre a importância da análise tática no futebol"
        print(f"\n📝 Testando geração: {test_request}")

        result = agent.generate_text(
            user_request=test_request,
            section_type="generico",
            word_count=150,
            n_context_chunks=3
        )

        print(f"\n📄 Resultado:\n{result}")
