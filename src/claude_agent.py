"""
Integração com Claude API para geração de texto acadêmico.
Suporta hierarquia de documentos e validação pós-geração.
"""
import os
from typing import Generator, Dict, Optional, Tuple, List
from anthropic import Anthropic
from dotenv import load_dotenv
from src.prompts import (
    SYSTEM_PROMPT,
    get_prompt,
    get_refinement_prompt,
    get_citation_extraction_prompt,
    get_methodology_check_prompt,
    get_regenerate_prompt
)
from src.vector_store import VectorStore
from src.text_validator import TextValidator, validate_generated_text, extract_sources_from_context


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
        self.text_validator = TextValidator()

        # Configurações padrão
        self.model = "claude-sonnet-4-5-20250929"  # Modelo mais recente
        self.max_tokens = 4096
        self.temperature = 0.7

        # Configurações de hierarquia
        self.n_metodologia_chunks = 2
        self.n_principais_chunks = 3
        self.n_base_chunks = 5
        self.methodology_title = "Garcia Lopez GPET"

    def generate_text(
        self,
        user_request: str,
        section_type: str = "generico",
        word_count: int = 500,
        tone: str = "formal",
        include_citations: bool = True,
        category_filter: Optional[str] = None,
        n_context_chunks: int = 5,
        stream: bool = False,
        use_hierarchy: bool = True,
        n_metodologia: Optional[int] = None,
        n_principais: Optional[int] = None,
        n_base: Optional[int] = None
    ) -> str | Generator:
        """
        Gera texto acadêmico baseado na solicitação do usuário.

        Args:
            user_request: Solicitação do usuário
            section_type: Tipo de seção ('introducao', 'revisao', etc.)
            word_count: Número aproximado de palavras
            tone: Tom do texto ('formal', 'equilibrado', 'direto')
            include_citations: Se deve incluir citações
            category_filter: Filtrar contexto por categoria ('base_40', 'principais_2', 'metodologia')
            n_context_chunks: Número de chunks de contexto (se não usar hierarquia)
            stream: Se True, retorna generator para streaming
            use_hierarchy: Se True, busca respeitando hierarquia de categorias
            n_metodologia: Número de chunks de metodologia (default: 2)
            n_principais: Número de chunks dos principais (default: 3)
            n_base: Número de chunks da base (default: 5)

        Returns:
            Texto gerado (ou generator se stream=True)
        """
        # Define valores de hierarquia
        n_met = n_metodologia if n_metodologia is not None else self.n_metodologia_chunks
        n_pri = n_principais if n_principais is not None else self.n_principais_chunks
        n_bas = n_base if n_base is not None else self.n_base_chunks

        # Busca contexto relevante na base vetorial
        print(f"Buscando contexto relevante para: '{user_request[:50]}...'")

        if use_hierarchy and not category_filter:
            # Busca hierárquica: metodologia > principais > base
            print("  Usando busca hierarquica...")
            context = self.vector_store.get_context_for_prompt(
                query=user_request,
                use_hierarchy=True,
                n_metodologia=n_met,
                n_principais=n_pri,
                n_base=n_bas
            )
        else:
            # Busca tradicional
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

    def generate_text_with_sources(
        self,
        user_request: str,
        section_type: str = "generico",
        word_count: int = 500,
        tone: str = "formal",
        include_citations: bool = True,
        use_hierarchy: bool = True,
        n_metodologia: Optional[int] = None,
        n_principais: Optional[int] = None,
        n_base: Optional[int] = None,
        category_filter: Optional[str] = None,
        n_context_chunks: int = 5
    ) -> Tuple[str, str]:
        """
        Gera texto e retorna também o contexto usado.

        Returns:
            Tuple com (texto_gerado, contexto_usado)
        """
        # Define valores de hierarquia
        n_met = n_metodologia if n_metodologia is not None else self.n_metodologia_chunks
        n_pri = n_principais if n_principais is not None else self.n_principais_chunks
        n_bas = n_base if n_base is not None else self.n_base_chunks

        # Busca contexto
        if use_hierarchy and not category_filter:
            context = self.vector_store.get_context_for_prompt(
                query=user_request,
                use_hierarchy=True,
                n_metodologia=n_met,
                n_principais=n_pri,
                n_base=n_bas
            )
        else:
            context = self.vector_store.get_context_for_prompt(
                query=user_request,
                n_results=n_context_chunks,
                category_filter=category_filter
            )

        # Gera o prompt
        from src.prompts import get_prompt
        user_prompt = get_prompt(
            section_type=section_type,
            context=context,
            user_request=user_request,
            word_count=word_count,
            tone=tone,
            include_citations=include_citations
        )

        # Gera texto
        generated_text = self._generate_complete(user_prompt)

        return generated_text, context

    def generate_text_with_validation(
        self,
        user_request: str,
        section_type: str = "generico",
        word_count: int = 500,
        tone: str = "formal",
        include_citations: bool = True,
        methodology_title: Optional[str] = None
    ) -> Tuple[str, Dict]:
        """
        Gera texto e valida automaticamente.

        Args:
            user_request: Solicitação do usuário
            section_type: Tipo de seção
            word_count: Número de palavras
            tone: Tom do texto
            include_citations: Incluir citações
            methodology_title: Título da metodologia para validação

        Returns:
            Tuple com (texto_gerado, relatório_validação)
        """
        # Gera texto com hierarquia e captura o contexto
        generated_text, context_used = self.generate_text_with_sources(
            user_request=user_request,
            section_type=section_type,
            word_count=word_count,
            tone=tone,
            include_citations=include_citations,
            use_hierarchy=True
        )

        # Valida o texto gerado com as fontes
        validation_report = self.validate_generated_text(
            generated_text,
            methodology_title or self.methodology_title,
            context_used=context_used
        )

        return generated_text, validation_report

    def validate_generated_text(
        self,
        text: str,
        methodology_title: Optional[str] = None,
        context_used: Optional[str] = None
    ) -> Dict:
        """
        Valida um texto gerado contra a base de conhecimento.

        Args:
            text: Texto a validar
            methodology_title: Título da metodologia esperada
            context_used: Contexto que foi usado na geração (para extrair fontes)

        Returns:
            Relatório de validação
        """
        title = methodology_title or self.methodology_title

        # Busca contexto para validação
        methodology_context = self.vector_store.get_context_for_prompt(
            query=title,
            n_results=3,
            category_filter='metodologia'
        )

        principais_context = self.vector_store.get_context_for_prompt(
            query="conceitos principais fundamentos",
            n_results=3,
            category_filter='principais_2'
        )

        # Extrai fontes do contexto usado
        sources_used = None
        if context_used:
            sources_used = extract_sources_from_context(context_used)

        # Gera relatório de validação
        report = validate_generated_text(
            text=text,
            methodology_context=methodology_context,
            principais_context=principais_context,
            methodology_title=title,
            sources_used=sources_used
        )

        return report

    def get_sources_info(self) -> Dict[str, List[str]]:
        """
        Retorna informações sobre as fontes disponíveis na base.

        Returns:
            Dict com listas de fontes por categoria
        """
        stats = self.vector_store.get_stats()

        # Busca os nomes dos documentos de cada categoria
        sources = {
            'metodologia': [],
            'principais_2': [],
            'base_40': []
        }

        try:
            collection = self.vector_store._get_or_create_collection()
            results = collection.get()

            for metadata in results['metadatas']:
                cat = metadata.get('category', '')
                filename = metadata.get('filename', '')
                if cat in sources and filename and filename not in sources[cat]:
                    sources[cat].append(filename)
        except:
            pass

        return sources

    def regenerate_with_fixes(
        self,
        original_request: str,
        validation_report: Dict,
        previous_text: str
    ) -> str:
        """
        Regenera texto corrigindo problemas identificados.

        Args:
            original_request: Solicitação original
            validation_report: Relatório de validação com problemas
            previous_text: Texto anterior que teve problemas

        Returns:
            Texto regenerado
        """
        # Extrai problemas e recomendações do relatório
        problems = []
        for alert in validation_report.get('alerts', []):
            if alert.level in ['warning', 'error']:
                problems.append(f"- {alert.message}")

        recommendations = validation_report.get('recommendations', [])

        problems_str = "\n".join(problems) if problems else "Nenhum problema específico"
        recommendations_str = "\n".join(f"- {r}" for r in recommendations) if recommendations else "Seguir boas práticas"

        # Busca contexto hierárquico
        context = self.vector_store.get_context_for_prompt(
            query=original_request,
            use_hierarchy=True,
            n_metodologia=3,  # Mais contexto de metodologia para correção
            n_principais=3,
            n_base=4
        )

        # Gera prompt de regeneração
        prompt = get_regenerate_prompt(
            original_request=original_request,
            context=context,
            problems=problems_str,
            recommendations=recommendations_str
        )

        return self._generate_complete(prompt)

    def _generate_complete(self, user_prompt: str) -> str:
        """Gera texto completo (não-streaming)."""
        print("Gerando texto com Claude...")

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
        print("Texto gerado com sucesso!")

        return generated_text

    def _generate_stream(self, user_prompt: str) -> Generator:
        """Gera texto em streaming."""
        print("Iniciando geracao em streaming...")

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

        suggestions = f"""**Sugestoes baseadas nos artigos indexados:**

Os artigos em sua base de conhecimento cobrem os seguintes topicos:
{', '.join(found_topics)}

Voce pode pedir coisas como:
- "Escreva uma introducao sobre {found_topics[0] if found_topics else 'analise tatica'}"
- "Desenvolva um paragrafo sobre a relacao entre {found_topics[0] if found_topics else 'tatica'} e {found_topics[1] if len(found_topics) > 1 else 'desempenho'}"
- "Explique as metodologias de {found_topics[0] if found_topics else 'analise'} citando estudos"
- "Faca uma revisao de literatura sobre {found_topics[2] if len(found_topics) > 2 else 'futebol moderno'}"

**Dica**: Seja especifico em sua solicitacao para resultados mais precisos!
"""
        return suggestions


if __name__ == "__main__":
    # Teste do agente
    agent = ClaudeAgent()

    # Teste básico
    print("\nTeste do Claude Agent\n")

    # Verifica se vector store está pronto
    stats = agent.vector_store.get_stats()
    if not stats['ready']:
        print("Base vetorial nao esta pronta. Execute o processamento dos PDFs primeiro.")
    else:
        print(f"Base vetorial pronta com {stats['total_chunks']} chunks")

        # Teste de geração
        test_request = "Escreva um paragrafo sobre a importancia da analise tatica no futebol"
        print(f"\nTestando geracao: {test_request}")

        result = agent.generate_text(
            user_request=test_request,
            section_type="generico",
            word_count=150,
            n_context_chunks=3
        )

        print(f"\nResultado:\n{result}")
