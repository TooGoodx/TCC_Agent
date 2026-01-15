"""
Módulo central unificado - Integração Claude + VectorStore
Simplificado: remove validações redundantes e gerenciamento de citações
"""
import os
from typing import List, Dict, Optional
from anthropic import Anthropic
from dotenv import load_dotenv
from src.vector_store import VectorStore


class SimpleAgent:
    """Agente simplificado para geração de texto acadêmico."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Inicializa o agente.

        Args:
            api_key: Chave API Anthropic (opcional, carrega do .env)
        """
        load_dotenv()

        # Tenta Streamlit secrets, depois .env
        try:
            import streamlit as st
            self.api_key = api_key or st.secrets.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        except (ImportError, AttributeError, FileNotFoundError):
            self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")

        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY não encontrada no .env ou Streamlit secrets")

        self.client = Anthropic(api_key=self.api_key)
        self.vector_store = VectorStore()
        self.model = "claude-sonnet-4-5-20250929"
        self.max_tokens = 4096

    def generate_text(
        self,
        prompt: str,
        section_type: str = "generico",
        context_history: Optional[List[Dict]] = None,
        stream: bool = False
    ) -> str:
        """
        Gera texto acadêmico com busca hierárquica.

        Args:
            prompt: Solicitação do usuário
            section_type: Tipo de seção do TCC
            context_history: Histórico de mensagens do chat
            stream: Se True, faz streaming da resposta

        Returns:
            Texto gerado
        """
        # Busca hierárquica no vector store
        print(f"🔍 Buscando contexto para: {prompt[:50]}...")

        metodologia = self.vector_store.search(
            query=prompt,
            n_results=2,
            category_filter="metodologia"
        )

        principais = self.vector_store.search(
            query=prompt,
            n_results=3,
            category_filter="principais_2"
        )

        base = self.vector_store.search(
            query=prompt,
            n_results=5,
            category_filter="base_40"
        )

        # Monta contexto hierárquico
        context = self._build_hierarchical_context(metodologia, principais, base)

        # Adiciona histórico do chat se existir
        if context_history and len(context_history) > 0:
            context += "\n\n" + self._format_history(context_history[-5:])

        # System prompt simplificado
        system_prompt = self._build_system_prompt(section_type, context)

        # Gera com Claude
        print(f"🤖 Gerando texto com Claude ({self.model})...")

        if stream:
            return self._generate_stream(system_prompt, prompt)
        else:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=0.7,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}]
            )

            return response.content[0].text

    def _build_hierarchical_context(
        self,
        metodologia: List[Dict],
        principais: List[Dict],
        base: List[Dict]
    ) -> str:
        """Constrói contexto respeitando hierarquia de documentos."""
        context_parts = []

        if metodologia:
            context_parts.append("📚 METODOLOGIA BASE (Prioridade Máxima):")
            for i, doc in enumerate(metodologia[:2], 1):
                context_parts.append(f"\n[Met-{i}] {doc['document'][:800]}")

        if principais:
            context_parts.append("\n\n📖 ARTIGOS PRINCIPAIS (Alta Prioridade):")
            for i, doc in enumerate(principais[:3], 1):
                context_parts.append(f"\n[Princ-{i}] {doc['document'][:600]}")

        if base:
            context_parts.append("\n\n📑 CONTEXTO ADICIONAL:")
            for i, doc in enumerate(base[:3], 1):
                context_parts.append(f"\n[Base-{i}] {doc['document'][:400]}")

        return "\n".join(context_parts)

    def _format_history(self, messages: List[Dict]) -> str:
        """Formata histórico de conversa para contexto."""
        history_lines = ["💬 HISTÓRICO DA CONVERSA (últimas mensagens):"]

        for msg in messages:
            role = "Usuário" if msg['role'] == 'user' else "Assistente"
            content = msg['content'][:200] + "..." if len(msg['content']) > 200 else msg['content']
            history_lines.append(f"\n{role}: {content}")

        return "\n".join(history_lines)

    def _build_system_prompt(self, section_type: str, context: str) -> str:
        """Constrói system prompt com hierarquia e contexto."""

        section_guidance = {
            "introducao": "Escreva uma INTRODUÇÃO clara: contexto → problema → objetivos.",
            "metodologia": "Descreva a METODOLOGIA: use o artigo metodológico como base estrutural.",
            "resultados": "Apresente RESULTADOS objetivamente, com dados e citações.",
            "conclusao": "Escreva CONCLUSÃO: síntese → contribuições → limitações → perspectivas.",
            "generico": "Escreva texto acadêmico bem fundamentado."
        }

        return f"""Você é um assistente especializado em redação de TCC sobre futebol.

🎯 HIERARQUIA DE DOCUMENTOS (OBRIGATÓRIA):
1. METODOLOGIA: Use SEMPRE como base estrutural principal
2. PRINCIPAIS: NUNCA contradiga estes artigos fundamentais
3. BASE: Use para citações adicionais e enriquecimento

Em conflitos, priorize: Metodologia > Principais > Base

📝 SEÇÃO ATUAL: {section_type.upper()}
{section_guidance.get(section_type, section_guidance["generico"])}

📚 PADRÃO ABNT (obrigatório):
- Citação direta curta: Autor (2023, p. 10) afirma que "texto".
- Citação indireta: A literatura aponta que... (SILVA; SANTOS, 2023).
- Múltiplos autores: Silva et al. (2023)

✅ SEMPRE:
- Base suas afirmações nos artigos do contexto
- Cite fontes em formato ABNT
- Use linguagem formal e acadêmica
- Seja objetivo e preciso

❌ NUNCA:
- Invente citações ou autores
- Use linguagem coloquial
- Faça afirmações sem fundamentação
- Copie trechos sem indicar citação

📖 CONTEXTO DISPONÍVEL:
{context}"""

    def _generate_stream(self, system_prompt: str, user_message: str):
        """Gera resposta com streaming."""
        with self.client.messages.stream(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=0.7,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}]
        ) as stream:
            for text in stream.text_stream:
                yield text
