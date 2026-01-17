"""
TCC Agent - Assistente de Escrita Academica com IA
Interface de Chat com memoria de longo prazo e inicializacao automatica
"""
import streamlit as st
import os
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

from src.vector_store import VectorStore
from src.claude_agent import ClaudeAgent
from src.citation_manager import CitationManager
from src.pdf_processor import PDFProcessor

# Configuracao da pagina
st.set_page_config(
    page_title="TCC Agent - Assistente Academico",
    page_icon="T",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Carrega variaveis de ambiente
load_dotenv()

# Arquivo de memoria de longo prazo
MEMORY_FILE = Path("outputs/user_preferences.json")

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
    .stTextArea textarea {
        font-size: 1.1rem;
    }
    .feedback-box {
        background-color: #e3f2fd;
        border-left: 4px solid #1E88E5;
        padding: 0.5rem 1rem;
        margin: 0.5rem 0;
        border-radius: 0 0.5rem 0.5rem 0;
    }
    .init-status {
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    </style>
""", unsafe_allow_html=True)


def get_env_var(key: str) -> str:
    """Obtem variavel de ambiente do Streamlit secrets ou .env."""
    try:
        return st.secrets.get(key) or os.getenv(key, "")
    except (AttributeError, FileNotFoundError):
        return os.getenv(key, "")


@st.cache_resource(show_spinner=False)
def initialize_vector_store():
    """
    Inicializa e popula a base vetorial automaticamente.
    Verifica se ja existe dados, senao faz download e indexacao.
    """
    vector_store = VectorStore()
    stats = vector_store.get_stats()

    # Se ja tem documentos indexados, retorna
    if stats['total_chunks'] > 0:
        return vector_store, stats, None

    # Base vazia - precisa indexar
    # Obtem IDs das pastas do Google Drive
    folder_40 = get_env_var("GOOGLE_DRIVE_FOLDER_40")
    folder_2 = get_env_var("GOOGLE_DRIVE_FOLDER_2")
    folder_metodologia = get_env_var("GOOGLE_DRIVE_FOLDER_METODOLOGIA")

    if not folder_40 or not folder_2:
        return vector_store, stats, "IDs das pastas do Google Drive nao configurados"

    try:
        # Inicializa processador de PDFs
        pdf_processor = PDFProcessor(folder_40, folder_2, folder_metodologia)

        # Verifica se PDFs ja existem localmente
        pdf_status = pdf_processor.check_pdfs_exist()

        if not pdf_status['all_ready']:
            # Faz download dos PDFs
            success = pdf_processor.download_all_pdfs()
            if not success:
                return vector_store, stats, "Erro ao baixar PDFs do Google Drive"

        # Processa e indexa os PDFs
        pdfs_data = pdf_processor.process_all_pdfs()

        if pdfs_data:
            vector_store.add_documents(pdfs_data, force_reindex=True)
            stats = vector_store.get_stats()
            return vector_store, stats, None
        else:
            return vector_store, stats, "Nenhum PDF encontrado para indexar"

    except Exception as e:
        return vector_store, stats, f"Erro na inicializacao: {str(e)}"


@st.cache_resource(show_spinner=False)
def init_agent():
    """Inicializa o agente Claude."""
    try:
        return ClaudeAgent()
    except Exception as e:
        st.error(f"Erro ao inicializar Claude Agent: {e}")
        return None


@st.cache_resource(show_spinner=False)
def init_citation_manager():
    """Inicializa o gerenciador de citacoes."""
    return CitationManager()


def load_long_term_memory() -> dict:
    """Carrega memoria de longo prazo do usuario."""
    if MEMORY_FILE.exists():
        try:
            with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {
        "feedbacks": [],
        "preferences": {},
        "learned_patterns": []
    }


def save_long_term_memory(memory: dict):
    """Salva memoria de longo prazo."""
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)


def add_feedback_to_memory(feedback: str, context: dict):
    """Adiciona feedback do usuario a memoria de longo prazo."""
    memory = load_long_term_memory()

    feedback_entry = {
        "timestamp": datetime.now().isoformat(),
        "feedback": feedback,
        "request": context.get("request", ""),
        "section_type": context.get("section_type", ""),
        "tone": context.get("tone", "")
    }

    memory["feedbacks"].append(feedback_entry)

    # Extrai padroes do feedback para aprendizado
    feedback_lower = feedback.lower()

    # Detecta preferencias de estilo
    if "mais formal" in feedback_lower or "muito informal" in feedback_lower:
        memory["preferences"]["tone_preference"] = "mais formal"
    elif "menos formal" in feedback_lower or "mais acessivel" in feedback_lower:
        memory["preferences"]["tone_preference"] = "menos formal"

    # Detecta preferencias de tamanho
    if "mais curto" in feedback_lower or "resumir" in feedback_lower:
        memory["preferences"]["length_preference"] = "mais curto"
    elif "mais longo" in feedback_lower or "expandir" in feedback_lower or "mais detalhes" in feedback_lower:
        memory["preferences"]["length_preference"] = "mais longo"

    # Detecta preferencias de citacoes
    if "mais citacoes" in feedback_lower:
        memory["preferences"]["citation_preference"] = "mais citacoes"
    elif "menos citacoes" in feedback_lower:
        memory["preferences"]["citation_preference"] = "menos citacoes"

    # Armazena padroes aprendidos
    if len(feedback) > 20:
        memory["learned_patterns"].append({
            "pattern": feedback,
            "context": context.get("section_type", "generico")
        })
        # Limita a 50 padroes
        memory["learned_patterns"] = memory["learned_patterns"][-50:]

    save_long_term_memory(memory)
    return memory


def get_memory_context() -> str:
    """Gera contexto baseado na memoria de longo prazo."""
    memory = load_long_term_memory()
    context_parts = []

    # Adiciona preferencias
    prefs = memory.get("preferences", {})
    if prefs:
        pref_text = []
        if prefs.get("tone_preference"):
            pref_text.append(f"- Tom: {prefs['tone_preference']}")
        if prefs.get("length_preference"):
            pref_text.append(f"- Tamanho: {prefs['length_preference']}")
        if prefs.get("citation_preference"):
            pref_text.append(f"- Citacoes: {prefs['citation_preference']}")

        if pref_text:
            context_parts.append("PREFERENCIAS DO USUARIO:\n" + "\n".join(pref_text))

    # Adiciona feedbacks recentes (ultimos 5)
    recent_feedbacks = memory.get("feedbacks", [])[-5:]
    if recent_feedbacks:
        fb_text = ["FEEDBACKS ANTERIORES:"]
        for fb in recent_feedbacks:
            fb_text.append(f"- {fb['feedback']}")
        context_parts.append("\n".join(fb_text))

    return "\n\n".join(context_parts) if context_parts else ""


def save_to_history(text: str, user_request: str):
    """Salva texto gerado no historico."""
    history_dir = Path("outputs/historico")
    history_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"output_{timestamp}.txt"
    filepath = history_dir / filename

    content = f"""TCC AGENT - HISTORICO DE GERACAO
Data: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}
Solicitacao: {user_request}

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
        from docx.shared import Pt
        from docx.enum.text import WD_ALIGN_PARAGRAPH

        doc = Document()

        style = doc.styles['Normal']
        font = style.font
        font.name = 'Times New Roman'
        font.size = Pt(12)

        paragraphs = text.split('\n\n')
        for para_text in paragraphs:
            if para_text.strip():
                p = doc.add_paragraph(para_text.strip())
                p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

        output_path = Path("outputs") / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(output_path)

        return output_path
    except ImportError:
        return None


def main():
    """Funcao principal da aplicacao."""

    # Header
    st.markdown('<div class="main-header">TCC Agent - Assistente de Escrita Academica</div>', unsafe_allow_html=True)

    # ===========================================
    # INICIALIZACAO AUTOMATICA DA BASE VETORIAL
    # ===========================================

    # Placeholder para status de inicializacao
    init_placeholder = st.empty()

    # Verifica se ja inicializou nesta sessao
    if 'initialized' not in st.session_state:
        st.session_state.initialized = False
        st.session_state.init_error = None

    # Inicializa componentes
    if not st.session_state.initialized:
        with init_placeholder.container():
            st.info("Inicializando base de conhecimento...")

            # Progress bar
            progress_bar = st.progress(0)
            status_text = st.empty()

            # Etapa 1: Inicializar Vector Store
            status_text.text("Carregando base vetorial...")
            progress_bar.progress(20)

            vector_store, stats, init_error = initialize_vector_store()

            if init_error:
                st.session_state.init_error = init_error
                st.warning(f"Aviso: {init_error}")
            else:
                progress_bar.progress(60)

            # Etapa 2: Inicializar Agent
            status_text.text("Inicializando agente Claude...")
            progress_bar.progress(80)

            agent = init_agent()
            citation_manager = init_citation_manager()

            # Etapa 3: Finalizar
            progress_bar.progress(100)
            status_text.text("Inicializacao concluida!")

            st.session_state.initialized = True
            st.session_state.vector_store = vector_store
            st.session_state.agent = agent
            st.session_state.citation_manager = citation_manager

            # Limpa o placeholder apos inicializacao
            import time
            time.sleep(1)
            init_placeholder.empty()
    else:
        vector_store = st.session_state.vector_store
        agent = st.session_state.agent
        citation_manager = st.session_state.citation_manager

    # Verifica se componentes estao prontos
    if not agent:
        st.error("Erro ao inicializar o agente Claude. Verifique a API key.")
        return

    # Sidebar
    with st.sidebar:
        st.header("Configuracoes")

        # Status da base
        stats = vector_store.get_stats()
        if stats['ready']:
            st.success(f"{stats['total_chunks']} chunks indexados")

            # Mostra detalhes por categoria
            with st.expander("Detalhes da base"):
                by_cat = stats.get('by_category', {})
                if by_cat.get('metodologia', 0) > 0:
                    st.write(f"Metodologia: {by_cat.get('metodologia', 0)}")
                if by_cat.get('principais_2', 0) > 0:
                    st.write(f"Principais: {by_cat.get('principais_2', 0)}")
                if by_cat.get('base_40', 0) > 0:
                    st.write(f"Base: {by_cat.get('base_40', 0)}")
        else:
            st.warning("Base vetorial vazia")
            st.caption("Configure os IDs do Google Drive nos secrets")

        st.markdown("---")

        # Parametros
        st.subheader("Parametros")

        section_type = st.selectbox(
            "Tipo de secao:",
            ["generico", "introducao", "revisao", "metodologia", "resultados", "conclusao"],
            format_func=lambda x: {
                "generico": "Generico",
                "introducao": "Introducao",
                "revisao": "Revisao de Literatura",
                "metodologia": "Metodologia",
                "resultados": "Resultados e Discussao",
                "conclusao": "Conclusao"
            }[x]
        )

        word_count = st.slider("Tamanho (palavras):", 100, 2000, 500, 50)

        tone = st.radio(
            "Estilo:",
            ["formal", "equilibrado", "direto"],
            format_func=lambda x: {
                "formal": "Formal",
                "equilibrado": "Equilibrado",
                "direto": "Direto"
            }[x]
        )

        include_citations = st.checkbox("Incluir citacoes", value=True)

        st.markdown("---")

        # Memoria de longo prazo
        st.subheader("Memoria")
        memory = load_long_term_memory()

        prefs = memory.get("preferences", {})
        if prefs:
            st.caption("Preferencias aprendidas:")
            for key, value in prefs.items():
                st.write(f"- {key}: {value}")

        fb_count = len(memory.get("feedbacks", []))
        st.caption(f"{fb_count} feedbacks armazenados")

        if st.button("Limpar Memoria"):
            save_long_term_memory({"feedbacks": [], "preferences": {}, "learned_patterns": []})
            st.success("Memoria limpa!")
            st.rerun()

    # Inicializa estado do chat
    if 'messages' not in st.session_state:
        st.session_state.messages = []

    if 'awaiting_feedback' not in st.session_state:
        st.session_state.awaiting_feedback = False

    if 'last_context' not in st.session_state:
        st.session_state.last_context = {}

    # Container do chat
    chat_container = st.container()

    # Exibe historico de mensagens
    with chat_container:
        for i, message in enumerate(st.session_state.messages):
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

                # Acoes para mensagens do assistente
                if message["role"] == "assistant" and message.get("show_actions"):
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        if st.button("Salvar", key=f"save_{i}"):
                            filepath = save_to_history(message["content"], message.get("request", ""))
                            st.success(f"Salvo: {filepath.name}")

                    with col2:
                        if st.button("DOCX", key=f"docx_{i}"):
                            docx_path = export_to_docx(message["content"])
                            if docx_path:
                                st.success(f"Exportado: {docx_path.name}")

                    with col3:
                        if st.button("Citacoes", key=f"cite_{i}"):
                            citations = citation_manager.extract_citations(message["content"])
                            st.write(f"**{len(citations)} citacoes**")
                            for c in citations:
                                st.write(f"- {c['author']} ({c['year']})")

                # Feedback para mensagens do assistente
                if message["role"] == "assistant" and message.get("show_actions"):
                    with st.expander("Dar feedback", expanded=False):
                        feedback_key = f"feedback_{i}"
                        feedback = st.text_input(
                            "Como posso melhorar?",
                            key=feedback_key,
                            placeholder="Ex: mais formal, menos citacoes, mais detalhes..."
                        )
                        if st.button("Enviar Feedback", key=f"fb_btn_{i}"):
                            if feedback:
                                context = {
                                    "request": message.get("request", ""),
                                    "section_type": section_type,
                                    "tone": tone
                                }
                                add_feedback_to_memory(feedback, context)
                                st.success("Feedback salvo! Vou lembrar para proximas geracoes.")

    # Input do chat
    if prompt := st.chat_input("Digite sua solicitacao..."):
        # Adiciona mensagem do usuario
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("user"):
            st.markdown(prompt)

        # Gera resposta
        with st.chat_message("assistant"):
            with st.spinner("Gerando texto academico..."):
                try:
                    # Obtem contexto da memoria de longo prazo
                    memory_context = get_memory_context()

                    # Ajusta prompt com contexto da memoria
                    enhanced_prompt = prompt
                    if memory_context:
                        enhanced_prompt = f"{memory_context}\n\nSOLICITACAO ATUAL:\n{prompt}"

                    generated_text, context_used = agent.generate_text_with_sources(
                        user_request=enhanced_prompt,
                        section_type=section_type,
                        word_count=word_count,
                        tone=tone,
                        include_citations=include_citations,
                        use_hierarchy=True
                    )

                    st.markdown(generated_text)

                    # Salva contexto para feedback
                    st.session_state.last_context = {
                        "request": prompt,
                        "section_type": section_type,
                        "tone": tone
                    }

                    # Adiciona ao historico
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": generated_text,
                        "show_actions": True,
                        "request": prompt
                    })

                except Exception as e:
                    error_msg = f"Erro ao gerar texto: {e}"
                    st.error(error_msg)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_msg,
                        "show_actions": False
                    })

    # Botao para limpar chat
    if st.session_state.messages:
        if st.button("Limpar Conversa", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

    # Footer
    st.markdown("---")
    st.markdown("""
        <div style='text-align: center; color: #666;'>
            <p>TCC Agent - Assistente Academico com IA</p>
            <p style='font-size: 0.9rem;'>Powered by Claude Sonnet 4.5 | ChromaDB</p>
        </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
