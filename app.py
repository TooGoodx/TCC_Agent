"""
TCC Agent - Assistente de Escrita Acadêmica com IA
Interface Streamlit
"""
import streamlit as st
import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

from src.pdf_processor import PDFProcessor
from src.vector_store import VectorStore
from src.claude_agent import ClaudeAgent
from src.citation_manager import CitationManager
from src.prompts import USAGE_EXAMPLES

# Configuração da página
st.set_page_config(
    page_title="⚽ TCC Agent - Assistente Acadêmico",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Carrega variáveis de ambiente
load_dotenv()

# CSS customizado
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E88E5;
        text-align: center;
        padding: 1rem 0;
    }
    .status-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #f0f2f6;
        margin: 1rem 0;
    }
    .success-box {
        background-color: #d4edda;
        border-left: 4px solid #28a745;
        padding: 1rem;
        margin: 1rem 0;
    }
    .warning-box {
        background-color: #fff3cd;
        border-left: 4px solid #ffc107;
        padding: 1rem;
        margin: 1rem 0;
    }
    .stTextArea textarea {
        font-size: 1.1rem;
    }
    </style>
""", unsafe_allow_html=True)


# Inicialização de componentes (com cache)
@st.cache_resource
def init_components():
    """Inicializa componentes da aplicação."""
    try:
        vector_store = VectorStore()
        agent = ClaudeAgent()
        citation_manager = CitationManager()

        # Try Streamlit secrets first (for cloud), then .env (for local)
        try:
            folder_40 = st.secrets.get("GOOGLE_DRIVE_FOLDER_40") or os.getenv("GOOGLE_DRIVE_FOLDER_40")
            folder_2 = st.secrets.get("GOOGLE_DRIVE_FOLDER_2") or os.getenv("GOOGLE_DRIVE_FOLDER_2")
        except (AttributeError, FileNotFoundError):
            folder_40 = os.getenv("GOOGLE_DRIVE_FOLDER_40")
            folder_2 = os.getenv("GOOGLE_DRIVE_FOLDER_2")

        pdf_processor = PDFProcessor(folder_40, folder_2)

        return vector_store, agent, citation_manager, pdf_processor
    except Exception as e:
        st.error(f"Erro ao inicializar componentes: {e}")
        return None, None, None, None


def save_to_history(text: str, user_request: str):
    """Salva texto gerado no histórico."""
    history_dir = Path("outputs/historico")
    history_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"output_{timestamp}.txt"
    filepath = history_dir / filename

    content = f"""TCC AGENT - HISTÓRICO DE GERAÇÃO
Data: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}
Solicitação: {user_request}

{'='*80}

{text}
"""

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    return filepath


def export_to_docx(text: str, filename: str = "output.docx"):
    """Exporta texto para formato DOCX."""
    try:
        from docx import Document
        from docx.shared import Pt, Inches
        from docx.enum.text import WD_ALIGN_PARAGRAPH

        doc = Document()

        # Configurações de estilo
        style = doc.styles['Normal']
        font = style.font
        font.name = 'Times New Roman'
        font.size = Pt(12)

        # Adiciona texto
        paragraphs = text.split('\n\n')
        for para_text in paragraphs:
            if para_text.strip():
                p = doc.add_paragraph(para_text.strip())
                p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

        # Salva
        output_path = Path("outputs") / filename
        doc.save(output_path)

        return output_path
    except ImportError:
        st.warning("Biblioteca python-docx não disponível. Instalando...")
        return None


def main():
    """Função principal da aplicação."""

    # Header
    st.markdown('<div class="main-header">⚽ TCC Agent - Assistente de Escrita Acadêmica</div>', unsafe_allow_html=True)
    st.markdown("---")

    # Inicializa componentes
    vector_store, agent, citation_manager, pdf_processor = init_components()

    if not all([vector_store, agent, citation_manager, pdf_processor]):
        st.error("❌ Erro ao inicializar aplicação. Verifique as configurações.")
        return

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configurações")

        # Status da base de conhecimento
        st.subheader("📊 Status da Base")
        stats = vector_store.get_stats()

        if stats['ready']:
            st.success(f"✅ {stats['total_chunks']} chunks indexados")
            for cat, count in stats['by_category'].items():
                st.write(f"  • {cat}: {count}")
        else:
            st.warning("⚠️ Base vetorial vazia")

        st.markdown("---")

        # Configurações de geração
        st.subheader("🎛️ Parâmetros")

        section_type = st.selectbox(
            "Tipo de seção:",
            ["generico", "introducao", "revisao", "metodologia", "resultados", "conclusao"],
            format_func=lambda x: {
                "generico": "Genérico",
                "introducao": "Introdução",
                "revisao": "Revisão de Literatura",
                "metodologia": "Metodologia",
                "resultados": "Resultados e Discussão",
                "conclusao": "Conclusão"
            }[x]
        )

        word_count = st.slider("Tamanho (palavras):", 100, 2000, 500, 50)

        tone = st.radio(
            "Estilo:",
            ["formal", "equilibrado", "direto"],
            format_func=lambda x: {
                "formal": "🎩 Formal",
                "equilibrado": "⚖️ Equilibrado",
                "direto": "🎯 Direto"
            }[x]
        )

        category_filter = st.radio(
            "Base de conhecimento:",
            [None, "principais_2", "base_40"],
            format_func=lambda x: {
                None: "📚 Todos (42 artigos)",
                "principais_2": "⭐ Principais (2)",
                "base_40": "📖 Base (40)"
            }[x]
        )

        n_context_chunks = st.slider("Chunks de contexto:", 3, 15, 5)

        include_citations = st.checkbox("Incluir citações", value=True)

        st.markdown("---")

        # Ações administrativas
        st.subheader("🔧 Gerenciamento")

        if st.button("📥 Baixar PDFs do Drive"):
            with st.spinner("Baixando PDFs..."):
                pdf_status = pdf_processor.check_pdfs_exist()
                if pdf_status['all_ready']:
                    st.info("PDFs já existem localmente")
                else:
                    success = pdf_processor.download_all_pdfs()
                    if success:
                        st.success("PDFs baixados com sucesso!")
                        st.rerun()
                    else:
                        st.error("Erro ao baixar PDFs")

        if st.button("🔄 Reindexar PDFs"):
            with st.spinner("Processando e indexando PDFs..."):
                try:
                    pdfs_data = pdf_processor.process_all_pdfs()
                    vector_store.add_documents(pdfs_data, force_reindex=True)
                    st.success(f"✅ {len(pdfs_data)} PDFs indexados!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro: {e}")

        # Limpar base vetorial com confirmação
        if 'confirm_clear' not in st.session_state:
            st.session_state.confirm_clear = False

        if st.button("🗑️ Limpar Base Vetorial"):
            st.session_state.confirm_clear = True

        if st.session_state.confirm_clear:
            st.warning("⚠️ Tem certeza que deseja limpar a base vetorial?")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Sim, limpar"):
                    vector_store.reset()
                    st.success("Base vetorial limpa!")
                    st.session_state.confirm_clear = False
                    st.rerun()
            with col2:
                if st.button("❌ Cancelar"):
                    st.session_state.confirm_clear = False
                    st.rerun()

    # Área principal
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("✍️ Sua Solicitação")

        user_request = st.text_area(
            "O que você quer escrever?",
            height=200,
            placeholder="Ex: Escreva uma introdução sobre a importância da análise tática no futebol moderno...",
            help="Seja específico para melhores resultados"
        )

        col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])

        with col_btn1:
            generate_btn = st.button("🚀 Gerar Texto", type="primary", use_container_width=True)

        with col_btn2:
            examples_btn = st.button("💡 Ver Exemplos", use_container_width=True)

        with col_btn3:
            summary_btn = st.button("📚 Resumir Artigos", use_container_width=True)

        # Botão de exemplos
        if examples_btn:
            with st.expander("💡 Exemplos de Prompts", expanded=True):
                st.markdown(USAGE_EXAMPLES)

        # Botão de resumo
        if summary_btn:
            with st.spinner("Gerando resumo dos artigos..."):
                try:
                    summary = agent.summarize_articles(category=category_filter, max_articles=5)
                    st.info("📚 **Resumo dos Artigos:**\n\n" + summary)
                except Exception as e:
                    st.error(f"Erro ao gerar resumo: {e}")

    with col2:
        st.subheader("📝 Texto Gerado")

        # Container para o resultado
        result_container = st.container()

        # Sessão para armazenar resultado
        if 'generated_text' not in st.session_state:
            st.session_state.generated_text = ""

        if 'current_request' not in st.session_state:
            st.session_state.current_request = ""

    # Geração de texto
    if generate_btn and user_request:
        with st.spinner("🤖 Gerando texto acadêmico..."):
            try:
                generated_text = agent.generate_text(
                    user_request=user_request,
                    section_type=section_type,
                    word_count=word_count,
                    tone=tone,
                    include_citations=include_citations,
                    category_filter=category_filter,
                    n_context_chunks=n_context_chunks,
                    stream=False
                )

                st.session_state.generated_text = generated_text
                st.session_state.current_request = user_request

            except Exception as e:
                st.error(f"❌ Erro ao gerar texto: {e}")

    # Exibe resultado
    with result_container:
        if st.session_state.generated_text:
            st.text_area(
                "Resultado:",
                value=st.session_state.generated_text,
                height=400,
                label_visibility="collapsed"
            )

            # Ações pós-geração
            st.markdown("---")
            col_action1, col_action2, col_action3, col_action4 = st.columns(4)

            with col_action1:
                if st.button("💾 Salvar Histórico"):
                    filepath = save_to_history(
                        st.session_state.generated_text,
                        st.session_state.current_request
                    )
                    st.success(f"✅ Salvo em: {filepath.name}")

            with col_action2:
                if st.button("📥 Export DOCX"):
                    docx_path = export_to_docx(st.session_state.generated_text)
                    if docx_path:
                        st.success(f"✅ Exportado: {docx_path.name}")

            with col_action3:
                if st.button("🔍 Analisar Citações"):
                    with st.expander("📖 Análise de Citações", expanded=True):
                        citations = citation_manager.extract_citations(st.session_state.generated_text)
                        st.write(f"**Total de citações:** {len(citations)}")

                        if citations:
                            st.write("**Autores citados:**")
                            for c in citations:
                                st.write(f"  • {c['author']} ({c['year']})")

                        suggestions = citation_manager.suggest_citation_improvements(
                            st.session_state.generated_text
                        )
                        st.write("\n**Sugestões:**")
                        for s in suggestions:
                            st.write(s)

            with col_action4:
                if st.button("🗑️ Limpar"):
                    st.session_state.generated_text = ""
                    st.session_state.current_request = ""
                    st.rerun()
        else:
            st.info("👈 Digite sua solicitação e clique em 'Gerar Texto'")

    # Footer
    st.markdown("---")
    st.markdown("""
        <div style='text-align: center; color: #666;'>
            <p>🎓 TCC Agent - Assistente Acadêmico com IA</p>
            <p style='font-size: 0.9rem;'>Powered by Claude Sonnet 4.5 | ChromaDB | LangChain</p>
        </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
