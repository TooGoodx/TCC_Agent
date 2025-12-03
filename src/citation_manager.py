"""
Gerenciador de citações e referências no padrão ABNT.
"""
import re
from typing import List, Dict, Set, Tuple
from collections import defaultdict


class CitationManager:
    """Gerencia citações e referências bibliográficas no formato ABNT."""

    def __init__(self):
        """Inicializa o gerenciador de citações."""
        # Padrões regex para detectar citações
        self.citation_patterns = [
            # (AUTOR, ano)
            r'\(([A-ZÀÁÂÃÇÉÊÍÓÔÕÚ][A-Za-zàáâãçéêíóôõú]+(?:\s+et\s+al\.)?),\s*(\d{4})\)',
            # (AUTOR; AUTOR, ano)
            r'\(([A-ZÀÁÂÃÇÉÊÍÓÔÕÚ][A-Za-zàáâãçéêíóôõú]+(?:\s*;\s*[A-ZÀÁÂÃÇÉÊÍÓÔÕÚ][A-Za-zàáâãçéêíóôõú]+)*),\s*(\d{4})\)',
            # Autor (ano)
            r'([A-ZÀÁÂÃÇÉÊÍÓÔÕÚ][A-Za-zàáâãçéêíóôõú]+(?:\s+et\s+al\.)?)\s*\((\d{4})\)',
            # (AUTOR, ano, p. X)
            r'\(([A-ZÀÁÂÃÇÉÊÍÓÔÕÚ][A-Za-zàáâãçéêíóôõú]+),\s*(\d{4}),\s*p\.\s*\d+(?:-\d+)?\)',
        ]

    def extract_citations(self, text: str) -> List[Dict[str, str]]:
        """
        Extrai todas as citações de um texto.

        Args:
            text: Texto contendo citações

        Returns:
            Lista de dicionários com informações das citações
        """
        citations = []
        seen = set()

        for pattern in self.citation_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                author = match.group(1).strip()
                year = match.group(2).strip()

                # Cria identificador único
                citation_id = f"{author}_{year}"

                if citation_id not in seen:
                    citations.append({
                        'author': author,
                        'year': year,
                        'full_citation': match.group(0),
                        'position': match.start()
                    })
                    seen.add(citation_id)

        # Ordena por posição no texto
        citations.sort(key=lambda x: x['position'])

        return citations

    def format_reference_abnt(
        self,
        author: str,
        year: str,
        title: str,
        publication_type: str = "artigo",
        **kwargs
    ) -> str:
        """
        Formata uma referência completa no padrão ABNT.

        Args:
            author: Nome do autor (SOBRENOME, Nome)
            year: Ano de publicação
            title: Título da obra
            publication_type: Tipo ('artigo', 'livro', 'tese', etc.)
            **kwargs: Campos adicionais (journal, volume, pages, publisher, etc.)

        Returns:
            Referência formatada em ABNT
        """
        if publication_type == "artigo":
            # Formato: AUTOR. Título do artigo. Título da Revista, v. X, n. X, p. X-X, ano.
            journal = kwargs.get('journal', 'Nome da Revista')
            volume = kwargs.get('volume', 'X')
            number = kwargs.get('number', 'X')
            pages = kwargs.get('pages', 'X-X')

            return (f"{author.upper()}. {title}. {journal}, "
                   f"v. {volume}, n. {number}, p. {pages}, {year}.")

        elif publication_type == "livro":
            # Formato: AUTOR. Título. Edição. Local: Editora, ano.
            edition = kwargs.get('edition', '')
            location = kwargs.get('location', 'Local')
            publisher = kwargs.get('publisher', 'Editora')

            edition_str = f"{edition}. " if edition else ""
            return f"{author.upper()}. {title}. {edition_str}{location}: {publisher}, {year}."

        elif publication_type == "tese":
            # Formato: AUTOR. Título. Ano. Tipo (Grau) - Instituição, Local, ano.
            degree = kwargs.get('degree', 'Doutorado')
            institution = kwargs.get('institution', 'Universidade')
            location = kwargs.get('location', 'Local')

            return (f"{author.upper()}. {title}. {year}. Tese ({degree}) - "
                   f"{institution}, {location}, {year}.")

        else:
            # Formato genérico
            return f"{author.upper()}. {title}. {year}."

    def generate_references_section(self, citations: List[Dict]) -> str:
        """
        Gera seção de referências a partir das citações extraídas.

        Args:
            citations: Lista de citações extraídas

        Returns:
            Seção de referências formatada
        """
        references = []
        seen = set()

        # Agrupa por autor e ano
        for citation in citations:
            key = f"{citation['author']}_{citation['year']}"
            if key not in seen:
                # Formato básico (usuário pode completar manualmente)
                ref = self.format_reference_abnt(
                    author=citation['author'],
                    year=citation['year'],
                    title="[Título a ser preenchido]",
                    publication_type="artigo",
                    journal="[Nome da revista]",
                    volume="[v]",
                    number="[n]",
                    pages="[p-p]"
                )
                references.append(ref)
                seen.add(key)

        # Ordena alfabeticamente
        references.sort()

        # Monta seção
        section = "REFERÊNCIAS\n\n"
        section += "\n\n".join(references)

        return section

    def validate_citation_format(self, text: str) -> List[Dict]:
        """
        Valida formato das citações no texto.

        Args:
            text: Texto a validar

        Returns:
            Lista de problemas encontrados
        """
        issues = []

        # Verifica citações mal formatadas comuns
        problematic_patterns = [
            (r'\([a-z][A-Za-z]+,\s*\d{4}\)', "Autor deve começar com maiúscula"),
            (r'\([A-Za-z]+\s+\d{4}\)', "Falta vírgula entre autor e ano"),
            (r'\([A-Za-z]+,\d{4}\)', "Falta espaço após vírgula"),
            (r'"[^"]+"\s*\([A-Za-z]+,\s*\d{4}\)', "Citação direta sem página"),
        ]

        for pattern, message in problematic_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                issues.append({
                    'position': match.start(),
                    'text': match.group(0),
                    'issue': message
                })

        return issues

    def extract_direct_quotes(self, text: str) -> List[Dict]:
        """
        Extrai citações diretas (entre aspas) do texto.

        Args:
            text: Texto contendo citações diretas

        Returns:
            Lista de citações diretas encontradas
        """
        quotes = []

        # Padrão para citações diretas: "texto" (AUTOR, ano, p. X)
        pattern = r'"([^"]+)"\s*\(([A-Z][A-Za-z]+),\s*(\d{4}),\s*p\.\s*(\d+(?:-\d+)?)\)'

        matches = re.finditer(pattern, text)
        for match in matches:
            quotes.append({
                'quote_text': match.group(1),
                'author': match.group(2),
                'year': match.group(3),
                'pages': match.group(4),
                'full_match': match.group(0),
                'position': match.start()
            })

        return quotes

    def format_author_name(self, full_name: str) -> str:
        """
        Formata nome de autor para ABNT (SOBRENOME, Nome).

        Args:
            full_name: Nome completo (ex: "João Silva")

        Returns:
            Nome formatado (ex: "SILVA, João")
        """
        parts = full_name.strip().split()
        if len(parts) == 0:
            return ""
        elif len(parts) == 1:
            return parts[0].upper()
        else:
            # Último elemento é o sobrenome
            last_name = parts[-1].upper()
            first_names = " ".join(parts[:-1])
            return f"{last_name}, {first_names}"

    def check_citation_consistency(self, text: str, references: List[str]) -> Dict:
        """
        Verifica consistência entre citações no texto e referências.

        Args:
            text: Texto com citações
            references: Lista de referências

        Returns:
            Dicionário com resultados da verificação
        """
        # Extrai citações do texto
        text_citations = self.extract_citations(text)
        text_authors = {c['author'].lower() for c in text_citations}

        # Extrai autores das referências
        ref_authors = set()
        for ref in references:
            # Pega primeiro autor da referência (antes da vírgula)
            match = re.match(r'([A-ZÀÁÂÃÇÉÊÍÓÔÕÚ]+)', ref)
            if match:
                ref_authors.add(match.group(1).lower())

        # Verifica inconsistências
        cited_not_referenced = text_authors - ref_authors
        referenced_not_cited = ref_authors - text_authors

        return {
            'total_citations': len(text_citations),
            'total_references': len(references),
            'cited_not_referenced': list(cited_not_referenced),
            'referenced_not_cited': list(referenced_not_cited),
            'consistent': len(cited_not_referenced) == 0 and len(referenced_not_cited) == 0
        }

    def suggest_citation_improvements(self, text: str) -> List[str]:
        """
        Sugere melhorias nas citações do texto.

        Args:
            text: Texto a analisar

        Returns:
            Lista de sugestões
        """
        suggestions = []

        # Extrai citações
        citations = self.extract_citations(text)
        quotes = self.extract_direct_quotes(text)

        # Verifica densidade de citações
        words = len(text.split())
        citations_per_100_words = (len(citations) / words) * 100 if words > 0 else 0

        if citations_per_100_words < 1:
            suggestions.append(
                "⚠️ Poucas citações no texto. Recomenda-se pelo menos 1 citação a cada 100 palavras "
                "em textos acadêmicos."
            )

        # Verifica citações diretas sem página
        direct_quotes_without_page = [q for q in quotes if not q.get('pages')]
        if direct_quotes_without_page:
            suggestions.append(
                "⚠️ Citações diretas devem incluir número da página. "
                f"Encontradas {len(direct_quotes_without_page)} sem página."
            )

        # Verifica uso de "et al."
        if any('et al' in c['author'] for c in citations):
            suggestions.append(
                "✅ Uso correto de 'et al.' detectado para obras com mais de 3 autores."
            )

        # Verifica diversidade de fontes
        unique_authors = len(set(c['author'] for c in citations))
        if unique_authors < 3 and len(citations) > 5:
            suggestions.append(
                "⚠️ Pouca diversidade de fontes. Procure citar diferentes autores para "
                "fundamentar melhor o texto."
            )

        if not suggestions:
            suggestions.append("✅ Citações aparentam estar bem formatadas!")

        return suggestions


if __name__ == "__main__":
    # Teste do citation manager
    manager = CitationManager()

    # Texto de exemplo
    test_text = """
    A análise tática no futebol moderno tem ganhado destaque (SILVA, 2022).
    De acordo com Oliveira (2023, p. 45), "a posse de bola é um indicador fundamental".
    Estudos recentes confirmam essa tendência (SANTOS; COSTA, 2021).
    """

    print("🧪 Teste do Citation Manager\n")

    # Extrai citações
    citations = manager.extract_citations(test_text)
    print(f"📚 Citações encontradas: {len(citations)}")
    for c in citations:
        print(f"  - {c['author']} ({c['year']})")

    # Gera seção de referências
    print("\n📖 Seção de Referências:")
    print(manager.generate_references_section(citations))

    # Sugestões
    print("\n💡 Sugestões:")
    suggestions = manager.suggest_citation_improvements(test_text)
    for s in suggestions:
        print(f"  {s}")
