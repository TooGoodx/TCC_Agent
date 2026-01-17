"""
Gerenciador de citacoes ABNT para textos academicos.
Extrai, valida e sugere melhorias em citacoes.
"""
import re
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class Citation:
    """Representa uma citacao encontrada no texto."""
    author: str
    year: str
    page: Optional[str] = None
    citation_type: str = "indirect"  # "direct" ou "indirect"
    raw_text: str = ""


class CitationManager:
    """Gerencia citacoes em formato ABNT."""

    # Padroes de citacao ABNT
    PATTERNS = {
        # Citacao indireta: (SILVA, 2020) ou (SILVA; OLIVEIRA, 2020)
        'indirect_parenthetical': r'\(([A-ZÀÁÂÃÉÊÍÓÔÕÚÇ][A-ZÀÁÂÃÉÊÍÓÔÕÚÇ\s;]+),\s*(\d{4})\)',

        # Citacao indireta no texto: Silva (2020) ou Silva e Oliveira (2020)
        'indirect_textual': r'([A-ZÀÁÂÃÉÊÍÓÔÕÚÇ][a-zàáâãéêíóôõúç]+(?:\s+(?:e|et\s+al\.?)\s+[A-ZÀÁÂÃÉÊÍÓÔÕÚÇ][a-zàáâãéêíóôõúç]+)?)\s*\((\d{4})\)',

        # Citacao direta com pagina: (SILVA, 2020, p. 45) ou (SILVA, 2020, pp. 45-46)
        'direct_with_page': r'\(([A-ZÀÁÂÃÉÊÍÓÔÕÚÇ][A-ZÀÁÂÃÉÊÍÓÔÕÚÇ\s;]+),\s*(\d{4}),\s*p{1,2}\.\s*([\d\-]+)\)',

        # Citacao direta no texto: Silva (2020, p. 45)
        'direct_textual': r'([A-ZÀÁÂÃÉÊÍÓÔÕÚÇ][a-zàáâãéêíóôõúç]+(?:\s+(?:e|et\s+al\.?)\s+[A-ZÀÁÂÃÉÊÍÓÔÕÚÇ][a-zàáâãéêíóôõúç]+)?)\s*\((\d{4}),\s*p{1,2}\.\s*([\d\-]+)\)',
    }

    def __init__(self):
        """Inicializa o gerenciador de citacoes."""
        self.citations_cache: List[Citation] = []

    def extract_citations(self, text: str) -> List[Dict]:
        """
        Extrai todas as citacoes de um texto.

        Args:
            text: Texto para extrair citacoes

        Returns:
            Lista de dicionarios com informacoes das citacoes
        """
        citations = []
        seen = set()  # Evita duplicatas

        # Citacoes diretas com pagina (parentetica)
        for match in re.finditer(self.PATTERNS['direct_with_page'], text):
            key = (match.group(1), match.group(2), match.group(3))
            if key not in seen:
                seen.add(key)
                citations.append({
                    'author': match.group(1).strip(),
                    'year': match.group(2),
                    'page': match.group(3),
                    'type': 'direct',
                    'format': 'parenthetical',
                    'raw': match.group(0)
                })

        # Citacoes diretas textuais
        for match in re.finditer(self.PATTERNS['direct_textual'], text):
            key = (match.group(1), match.group(2), match.group(3))
            if key not in seen:
                seen.add(key)
                citations.append({
                    'author': match.group(1).strip(),
                    'year': match.group(2),
                    'page': match.group(3),
                    'type': 'direct',
                    'format': 'textual',
                    'raw': match.group(0)
                })

        # Citacoes indiretas parenteticas
        for match in re.finditer(self.PATTERNS['indirect_parenthetical'], text):
            key = (match.group(1), match.group(2), None)
            if key not in seen:
                seen.add(key)
                citations.append({
                    'author': match.group(1).strip(),
                    'year': match.group(2),
                    'page': None,
                    'type': 'indirect',
                    'format': 'parenthetical',
                    'raw': match.group(0)
                })

        # Citacoes indiretas textuais
        for match in re.finditer(self.PATTERNS['indirect_textual'], text):
            # Evita pegar autores ja capturados nas diretas
            author = match.group(1).strip()
            year = match.group(2)

            # Verifica se nao e parte de uma citacao direta
            full_match_pos = match.start()
            context = text[max(0, full_match_pos-5):min(len(text), match.end()+20)]
            if ', p.' in context or ', pp.' in context:
                continue

            key = (author, year, None)
            if key not in seen:
                seen.add(key)
                citations.append({
                    'author': author,
                    'year': year,
                    'page': None,
                    'type': 'indirect',
                    'format': 'textual',
                    'raw': match.group(0)
                })

        # Ordena por ordem de aparicao no texto
        citations.sort(key=lambda c: text.find(c['raw']))

        return citations

    def validate_citations(self, text: str) -> Dict:
        """
        Valida as citacoes de um texto.

        Args:
            text: Texto para validar

        Returns:
            Relatorio de validacao
        """
        citations = self.extract_citations(text)
        issues = []
        warnings = []

        # Verifica citacoes diretas sem pagina
        direct_quotes = re.findall(r'"[^"]{50,}"', text)  # Citacoes longas entre aspas
        if direct_quotes:
            # Verifica se ha citacao com pagina proximo
            for quote in direct_quotes:
                quote_pos = text.find(quote)
                nearby_text = text[quote_pos:min(len(text), quote_pos + len(quote) + 50)]
                if not re.search(r'p{1,2}\.\s*\d+', nearby_text):
                    issues.append("Citacao direta longa sem indicacao de pagina")

        # Verifica densidade de citacoes
        word_count = len(text.split())
        citation_count = len(citations)

        if word_count > 100:
            density = word_count / max(citation_count, 1)
            if density > 150:
                warnings.append(f"Baixa densidade de citacoes: 1 a cada {int(density)} palavras (recomendado: 1 a cada 100)")
            elif density < 50:
                warnings.append(f"Alta densidade de citacoes: 1 a cada {int(density)} palavras (pode dificultar leitura)")

        # Verifica variedade de autores
        unique_authors = set(c['author'] for c in citations)
        if len(citations) > 3 and len(unique_authors) < len(citations) / 2:
            warnings.append("Pouca variedade de autores citados")

        # Verifica anos das citacoes
        current_year = 2024
        old_citations = [c for c in citations if int(c['year']) < current_year - 10]
        if len(old_citations) > len(citations) / 2:
            warnings.append("Maioria das citacoes tem mais de 10 anos")

        return {
            'valid': len(issues) == 0,
            'citation_count': citation_count,
            'unique_authors': len(unique_authors),
            'issues': issues,
            'warnings': warnings,
            'citations': citations
        }

    def suggest_citation_improvements(self, text: str) -> List[str]:
        """
        Sugere melhorias para as citacoes do texto.

        Args:
            text: Texto para analisar

        Returns:
            Lista de sugestoes
        """
        suggestions = []
        validation = self.validate_citations(text)

        # Adiciona issues como sugestoes
        for issue in validation['issues']:
            suggestions.append(f"Corrigir: {issue}")

        # Adiciona warnings como sugestoes
        for warning in validation['warnings']:
            suggestions.append(f"Considerar: {warning}")

        # Sugestoes adicionais baseadas na analise
        citations = validation['citations']

        if not citations:
            suggestions.append("Adicionar citacoes para fundamentar o texto")
        else:
            # Verifica tipos de citacao
            direct_count = sum(1 for c in citations if c['type'] == 'direct')
            indirect_count = sum(1 for c in citations if c['type'] == 'indirect')

            if direct_count == 0 and len(citations) > 3:
                suggestions.append("Considerar incluir algumas citacoes diretas para enfatizar pontos importantes")

            if indirect_count == 0:
                suggestions.append("Considerar parafrasear algumas fontes (citacoes indiretas)")

            # Verifica formato
            parenthetical = sum(1 for c in citations if c['format'] == 'parenthetical')
            textual = sum(1 for c in citations if c['format'] == 'textual')

            if parenthetical > 0 and textual == 0:
                suggestions.append("Variar o formato das citacoes (usar algumas no corpo do texto)")
            elif textual > 0 and parenthetical == 0:
                suggestions.append("Variar o formato das citacoes (usar algumas entre parenteses)")

        if not suggestions:
            suggestions.append("Citacoes estao adequadas!")

        return suggestions

    def format_reference(
        self,
        author: str,
        year: str,
        title: str,
        source: str = "",
        volume: str = "",
        number: str = "",
        pages: str = "",
        publisher: str = "",
        city: str = ""
    ) -> str:
        """
        Formata uma referencia bibliografica em ABNT.

        Args:
            author: Nome do autor (SOBRENOME, Nome)
            year: Ano de publicacao
            title: Titulo do trabalho
            source: Nome do periodico/livro
            volume: Volume
            number: Numero
            pages: Paginas
            publisher: Editora
            city: Cidade

        Returns:
            Referencia formatada em ABNT
        """
        reference = f"{author}. **{title}**."

        if source:
            reference += f" *{source}*"
            if volume:
                reference += f", v. {volume}"
            if number:
                reference += f", n. {number}"
            if pages:
                reference += f", p. {pages}"
        elif publisher:
            if city:
                reference += f" {city}:"
            reference += f" {publisher}"

        reference += f", {year}."

        return reference

    def get_citation_stats(self, text: str) -> Dict:
        """
        Retorna estatisticas sobre as citacoes do texto.

        Args:
            text: Texto para analisar

        Returns:
            Dicionario com estatisticas
        """
        citations = self.extract_citations(text)
        word_count = len(text.split())

        return {
            'total_citations': len(citations),
            'direct_citations': sum(1 for c in citations if c['type'] == 'direct'),
            'indirect_citations': sum(1 for c in citations if c['type'] == 'indirect'),
            'unique_authors': len(set(c['author'] for c in citations)),
            'word_count': word_count,
            'citation_density': word_count / max(len(citations), 1),
            'years': sorted(set(c['year'] for c in citations))
        }


if __name__ == "__main__":
    # Teste do gerenciador de citacoes
    manager = CitationManager()

    test_text = """
    A analise tatica no futebol tem evoluido significativamente nos ultimos anos
    (SILVA, 2020). Segundo Oliveira (2019), as metricas de desempenho sao
    fundamentais para a compreensao do jogo. Conforme destacam Silva e Santos (2021, p. 45),
    "a posse de bola e um indicador importante, mas nao determinante do sucesso".

    Estudos recentes (FERREIRA; COSTA, 2022) demonstram que a intensidade de
    pressao e mais relevante que a posse de bola isoladamente. Garcia Lopez (2018)
    propoe uma metodologia inovadora para analise tatica.
    """

    print("=== Teste do CitationManager ===\n")

    # Extrai citacoes
    citations = manager.extract_citations(test_text)
    print(f"Citacoes encontradas: {len(citations)}")
    for c in citations:
        print(f"  - {c['author']} ({c['year']}) - {c['type']}/{c['format']}")

    print("\n")

    # Valida
    validation = manager.validate_citations(test_text)
    print(f"Valido: {validation['valid']}")
    print(f"Issues: {validation['issues']}")
    print(f"Warnings: {validation['warnings']}")

    print("\n")

    # Sugestoes
    suggestions = manager.suggest_citation_improvements(test_text)
    print("Sugestoes:")
    for s in suggestions:
        print(f"  - {s}")

    print("\n")

    # Estatisticas
    stats = manager.get_citation_stats(test_text)
    print(f"Estatisticas: {stats}")
