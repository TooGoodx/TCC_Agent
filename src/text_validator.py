"""
Módulo de validação de textos gerados.
Verifica uso de metodologia e contradições com artigos principais.
"""
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ValidationAlert:
    """Representa um alerta de validação."""
    level: str  # 'warning', 'error', 'info'
    category: str  # 'methodology', 'contradiction', 'citation'
    message: str
    suggestion: Optional[str] = None


class TextValidator:
    """Valida textos gerados contra a base de conhecimento."""

    def __init__(self):
        """Inicializa o validador."""
        # Padrões para identificar menções metodológicas
        self.methodology_patterns = [
            r'GPET',
            r'Garcia\s*Lopez',
            r'García\s*López',
            r'modelo\s+(de\s+)?análise',
            r'metodologia\s+(proposta|utilizada)',
            r'instrumento\s+(de\s+)?observação',
            r'categorias\s+(de\s+)?análise',
            r'variáveis\s+táticas',
        ]

        # Termos que podem indicar contradição
        self.contradiction_indicators = [
            'no entanto',
            'contudo',
            'porém',
            'entretanto',
            'diferentemente',
            'ao contrário',
            'em oposição',
            'diverge de',
            'contradiz',
        ]

    def check_methodology_usage(
        self,
        generated_text: str,
        methodology_context: Optional[str] = None,
        methodology_title: str = "Garcia Lopez GPET"
    ) -> Tuple[bool, List[ValidationAlert]]:
        """
        Verifica se o texto gerado utiliza a metodologia especificada.

        Args:
            generated_text: Texto gerado pelo Claude
            methodology_context: Contexto do artigo metodológico (opcional)
            methodology_title: Título/nome da metodologia esperada

        Returns:
            Tuple com (usa_metodologia: bool, alertas: List[ValidationAlert])
        """
        alerts = []
        uses_methodology = False

        # Normaliza texto para busca
        text_lower = generated_text.lower()

        # Verifica menções à metodologia
        methodology_mentions = []
        for pattern in self.methodology_patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            if matches:
                methodology_mentions.extend(matches)
                uses_methodology = True

        # Verifica menção específica ao título da metodologia
        if methodology_title.lower() in text_lower:
            uses_methodology = True
            methodology_mentions.append(methodology_title)

        # Gera alertas baseados na análise
        if not uses_methodology:
            alerts.append(ValidationAlert(
                level='warning',
                category='methodology',
                message=f"O texto não menciona explicitamente a metodologia '{methodology_title}'",
                suggestion="Considere adicionar referências ao modelo metodológico base"
            ))
        else:
            alerts.append(ValidationAlert(
                level='info',
                category='methodology',
                message=f"Metodologia identificada: {', '.join(set(methodology_mentions))}",
                suggestion=None
            ))

        # Se temos contexto metodológico, verifica aderência
        if methodology_context:
            adherence_score = self._check_methodology_adherence(
                generated_text, methodology_context
            )
            if adherence_score < 0.3:
                alerts.append(ValidationAlert(
                    level='warning',
                    category='methodology',
                    message="Baixa aderência ao modelo metodológico de referência",
                    suggestion="Revise o texto para incorporar mais elementos da metodologia base"
                ))

        return uses_methodology, alerts

    def check_contradictions(
        self,
        generated_text: str,
        principais_context: str
    ) -> Tuple[bool, List[ValidationAlert]]:
        """
        Verifica se o texto gerado contradiz os artigos principais.

        Args:
            generated_text: Texto gerado pelo Claude
            principais_context: Contexto dos artigos principais

        Returns:
            Tuple com (tem_contradicoes: bool, alertas: List[ValidationAlert])
        """
        alerts = []
        has_contradictions = False
        text_lower = generated_text.lower()

        # Verifica indicadores de contradição
        found_indicators = []
        for indicator in self.contradiction_indicators:
            if indicator in text_lower:
                found_indicators.append(indicator)

        if found_indicators:
            # Pode haver contradição - precisa análise mais profunda
            alerts.append(ValidationAlert(
                level='info',
                category='contradiction',
                message=f"Expressões de contraste encontradas: {', '.join(found_indicators)}",
                suggestion="Verifique se as afirmações contraditórias estão bem fundamentadas"
            ))

        # Extrai afirmações-chave do texto principal para comparar
        # (simplificado - uma implementação completa usaria NLP mais sofisticado)
        key_assertions = self._extract_key_assertions(principais_context)

        for assertion in key_assertions:
            negation = self._check_negation(generated_text, assertion)
            if negation:
                has_contradictions = True
                alerts.append(ValidationAlert(
                    level='warning',
                    category='contradiction',
                    message=f"Possível contradição com artigo principal",
                    suggestion=f"Verifique afirmação sobre: {assertion[:100]}..."
                ))

        if not has_contradictions and not found_indicators:
            alerts.append(ValidationAlert(
                level='info',
                category='contradiction',
                message="Nenhuma contradição evidente com artigos principais",
                suggestion=None
            ))

        return has_contradictions, alerts

    def generate_validation_report(
        self,
        generated_text: str,
        methodology_context: Optional[str] = None,
        principais_context: Optional[str] = None,
        methodology_title: str = "Garcia Lopez GPET",
        sources_used: Optional[Dict] = None
    ) -> Dict:
        """
        Gera relatório completo de validação do texto.

        Args:
            generated_text: Texto gerado
            methodology_context: Contexto da metodologia
            principais_context: Contexto dos artigos principais
            methodology_title: Nome da metodologia
            sources_used: Dict com fontes utilizadas por categoria

        Returns:
            Dict com relatório de validação
        """
        all_alerts = []
        report = {
            'valid': True,
            'uses_methodology': False,
            'has_contradictions': False,
            'alerts': [],
            'summary': '',
            'recommendations': [],
            'sources_used': sources_used or {}
        }

        # Verifica uso de metodologia
        uses_methodology, method_alerts = self.check_methodology_usage(
            generated_text, methodology_context, methodology_title
        )
        report['uses_methodology'] = uses_methodology
        all_alerts.extend(method_alerts)

        # Verifica contradições
        if principais_context:
            has_contradictions, contr_alerts = self.check_contradictions(
                generated_text, principais_context
            )
            report['has_contradictions'] = has_contradictions
            all_alerts.extend(contr_alerts)

        # Verifica citações
        citation_alerts = self._check_citations(generated_text)
        all_alerts.extend(citation_alerts)

        # Compila alertas
        report['alerts'] = all_alerts

        # Determina validade geral
        warnings = [a for a in all_alerts if a.level == 'warning']
        errors = [a for a in all_alerts if a.level == 'error']

        if errors:
            report['valid'] = False
        elif len(warnings) > 2:
            report['valid'] = False

        # Gera sumário
        report['summary'] = self._generate_summary(report)

        # Gera recomendações
        report['recommendations'] = self._generate_recommendations(all_alerts)

        return report

    def _check_methodology_adherence(
        self,
        generated_text: str,
        methodology_context: str
    ) -> float:
        """Calcula score de aderência à metodologia (0-1)."""
        # Extrai termos-chave do contexto metodológico
        method_terms = set(re.findall(r'\b\w{5,}\b', methodology_context.lower()))

        # Conta quantos aparecem no texto gerado
        text_lower = generated_text.lower()
        matches = sum(1 for term in method_terms if term in text_lower)

        if not method_terms:
            return 1.0

        return min(1.0, matches / (len(method_terms) * 0.1))

    def _extract_key_assertions(self, text: str) -> List[str]:
        """Extrai afirmações-chave de um texto."""
        # Divide em sentenças
        sentences = re.split(r'[.!?]', text)

        # Filtra sentenças assertivas (heurística simples)
        assertions = []
        assertive_patterns = [
            r'\bé\b',
            r'\bsão\b',
            r'\bdemonstram?\b',
            r'\bmostra[mn]?\b',
            r'\bindica[mn]?\b',
            r'\bconfirma[mn]?\b',
        ]

        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 30:  # Ignora sentenças muito curtas
                for pattern in assertive_patterns:
                    if re.search(pattern, sentence, re.IGNORECASE):
                        assertions.append(sentence)
                        break

        return assertions[:10]  # Limita a 10 afirmações

    def _check_negation(self, text: str, assertion: str) -> bool:
        """Verifica se o texto contém negação de uma afirmação."""
        # Extrai palavras-chave da afirmação
        keywords = set(re.findall(r'\b\w{5,}\b', assertion.lower()))

        if not keywords:
            return False

        text_lower = text.lower()

        # Procura negações próximas às palavras-chave
        negation_patterns = [r'não\s+\w+', r'nunca\s+\w+', r'jamais\s+\w+']

        for pattern in negation_patterns:
            matches = re.finditer(pattern, text_lower)
            for match in matches:
                # Verifica se alguma palavra-chave está próxima
                context = text_lower[max(0, match.start()-50):match.end()+50]
                if any(kw in context for kw in keywords):
                    return True

        return False

    def _check_citations(self, text: str) -> List[ValidationAlert]:
        """Verifica qualidade das citações no texto."""
        alerts = []

        # Padrão de citação ABNT
        citation_pattern = r'\([A-Z][A-Za-z]+(?:\s+et\s+al\.?)?,?\s*\d{4}(?:,\s*p\.\s*\d+)?\)'
        citations = re.findall(citation_pattern, text)

        # Contagem de palavras
        word_count = len(text.split())

        # Verifica densidade de citações
        if word_count > 100:
            expected_citations = word_count // 100  # 1 citação a cada 100 palavras
            if len(citations) < expected_citations * 0.5:
                alerts.append(ValidationAlert(
                    level='warning',
                    category='citation',
                    message=f"Densidade de citações baixa ({len(citations)} citações para {word_count} palavras)",
                    suggestion="Considere adicionar mais citações para fundamentar o texto"
                ))

        # Verifica citações diretas sem página
        direct_quotes = re.findall(r'"[^"]{50,}"', text)
        for quote in direct_quotes:
            # Procura citação próxima
            idx = text.find(quote)
            context = text[idx:idx+len(quote)+50]
            if not re.search(r'p\.\s*\d+', context):
                alerts.append(ValidationAlert(
                    level='warning',
                    category='citation',
                    message="Citação direta sem número de página",
                    suggestion="Adicione o número da página nas citações diretas"
                ))
                break  # Só alerta uma vez

        return alerts

    def _generate_summary(self, report: Dict) -> str:
        """Gera resumo textual do relatório."""
        parts = []

        if report['valid']:
            parts.append("Texto validado com sucesso.")
        else:
            parts.append("Texto requer revisão.")

        if report['uses_methodology']:
            parts.append("Metodologia base identificada.")
        else:
            parts.append("Metodologia base NÃO identificada.")

        if report['has_contradictions']:
            parts.append("Possíveis contradições detectadas.")

        warnings = [a for a in report['alerts'] if a.level == 'warning']
        if warnings:
            parts.append(f"{len(warnings)} alertas de atenção.")

        return " ".join(parts)

    def _generate_recommendations(
        self,
        alerts: List[ValidationAlert]
    ) -> List[str]:
        """Gera lista de recomendações baseada nos alertas."""
        recommendations = []

        for alert in alerts:
            if alert.suggestion and alert.level in ['warning', 'error']:
                recommendations.append(alert.suggestion)

        return list(set(recommendations))  # Remove duplicatas


# Função utilitária para uso direto
def validate_generated_text(
    text: str,
    methodology_context: Optional[str] = None,
    principais_context: Optional[str] = None,
    methodology_title: str = "Garcia Lopez GPET",
    sources_used: Optional[Dict] = None
) -> Dict:
    """
    Função utilitária para validar texto gerado.

    Args:
        text: Texto a validar
        methodology_context: Contexto da metodologia
        principais_context: Contexto dos artigos principais
        methodology_title: Nome da metodologia
        sources_used: Dict com fontes utilizadas por categoria

    Returns:
        Relatório de validação
    """
    validator = TextValidator()
    return validator.generate_validation_report(
        text, methodology_context, principais_context, methodology_title, sources_used
    )


def extract_sources_from_context(context: str) -> Dict[str, List[str]]:
    """
    Extrai as fontes (nomes de arquivos) do contexto formatado.

    Args:
        context: String de contexto formatado

    Returns:
        Dict com listas de fontes por categoria
    """
    sources = {
        'metodologia': [],
        'principais_2': [],
        'base_40': []
    }

    # Padrão para extrair fonte e categoria
    import re
    fonte_pattern = r'Fonte:\s*([^\n]+)'
    categoria_pattern = r'Categoria:\s*([^\n]+)'

    fontes = re.findall(fonte_pattern, context)
    categorias = re.findall(categoria_pattern, context)

    for fonte, categoria in zip(fontes, categorias):
        fonte = fonte.strip()
        categoria = categoria.strip()
        if categoria in sources and fonte not in sources[categoria]:
            sources[categoria].append(fonte)

    return sources


if __name__ == "__main__":
    # Teste do validador
    test_text = """
    A análise tática no futebol moderno utiliza diversos instrumentos de observação.
    Segundo Garcia Lopez (2021), o modelo GPET permite categorizar as ações táticas
    de forma sistemática. Estudos demonstram que a posse de bola é fundamental
    (SILVA, 2020). No entanto, outros autores questionam essa afirmação.
    "A análise tática deve considerar múltiplas variáveis para ser efetiva"
    (OLIVEIRA, 2022, p. 45).
    """

    validator = TextValidator()
    report = validator.generate_validation_report(test_text)

    print("=== Relatório de Validação ===")
    print(f"Válido: {report['valid']}")
    print(f"Usa metodologia: {report['uses_methodology']}")
    print(f"Tem contradições: {report['has_contradictions']}")
    print(f"\nSumário: {report['summary']}")
    print("\nAlertas:")
    for alert in report['alerts']:
        print(f"  [{alert.level}] {alert.category}: {alert.message}")
    print("\nRecomendações:")
    for rec in report['recommendations']:
        print(f"  - {rec}")
