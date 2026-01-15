"""
TCC Agent - Assistente Acadêmico Simplificado
Interface de chat com hierarquia de documentos
Reduzido de 674 para ~300 linhas
"""
import streamlit as st
import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

from src.pdf_processor import PDFProcessor
from src.vector_store import VectorStore
from src.core import SimpleAgent

# Configuração da página
st.set_page_config(
    page_title="🎓 TCC Agent",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Carrega variáveis de ambiente
load_dotenv()

# CSS mínimo
st.markdown("""
    <style>
    .stChatMessage {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    </style>
""", unsafe_allow_html=True)


# Inicialização de componentes
@st.cache_resource
def init_components():
    """Inicializa componentes da aplicação."""
    try:
        vector_store = VectorStore()
        agent = SimpleAgent()

        # Carrega configurações do Google Drive
        try:
            folder_40 = st.secrets.get("GOOGLE_DRIVE_FOLDER_40") or os.getenv("GOOGLE_DRIVE_FOLDER_40")
            folder_2 = st.secrets.get("GOOGLE_DRIVE_FOLDER_2") or os.getenv("GOOGLE_DRIVE_FOLDER_2")
            folder_metodologia = st.secrets.get("GOOGLE_DRIVE_FOLDER_METODOLOGIA") or os.getenv("GOOGLE_DRIVE_FOLDER_METODOLOGIA")
        except (AttributeError, FileNotFoundError):
            folder_40 = os.getenv("GOOGLE_DRIVE_FOLDER_40")
            folder_2 = os.getenv("GOOGLE_DRIVE_FOLDER_2")
            folder_metodologia = os.getenv("GOOGLE_DRIVE_FOLDER_METODOLOGIA")

        pdf_processor = PDFProcessor(folder_40, folder_2, folder_metodologia)

        return vector_store, agent, pdf_processor
    except Exception as e:
        st.error(f"❌ Erro ao inicializar: {e}")
        return None, None, None


def get_vectorstore_stats(vector_store):
    """Obtém estatísticas da base vetorial."""
    try:
        stats = vector_store.get_statistics()
        return {
            'ready': stats['total_chunks'] > 0,
            'total_chunks': stats['total_chunks'],
            'metodologia': stats.get('metodologia', 0),
            'principais': stats.get('principais_2', 0),
            'base': stats.get('base_40', 0)
        }
    except:
        return {'ready': False, 'total_chunks': 0}


def save_to_file(text: str, user_request: str):
    """Salva texto em arquivo TXT."""
    history_dir = Path("outputs/historico")
    history_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"output_{timestamp}.txt"
    filepath = history_dir / filename

    content = f"""TCC AGENT - GERAÇÃO
Data: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}
Solicitação: {user_request}

{'='*80}

{text}
"""

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    return filepath


def auto_initialize(pdf_processor, vector_store):
    """
    Inicializa automaticamente PDFs e base vetorial.
    Executa apenas uma vez por sessão.
    """
    # Verifica se já foi inicializado nesta sessão
    if st.session_state.get('auto_initialized', False):
        return True

    try:
        # PASSO 1: Verificar e baixar PDFs se necessário
        pdf_status = pdf_processor.check_pdfs_exist()

        if not pdf_status['all_ready']:
            st.info("🔄 Primeira execução detectada - baixando PDFs do Google Drive...")
            with st.spinner("📥 Baixando PDFs... Isso pode levar alguns minutos."):
                success = pdf_processor.download_all_pdfs()
                if not success:
                    st.error("❌ Erro ao baixar PDFs do Google Drive")
                    return False
                st.success("✅ PDFs baixados com sucesso!")

        # PASSO 2: Verificar e processar/indexar se necessário
        stats = get_vectorstore_stats(vector_store)

        if not stats['ready'] or stats['total_chunks'] == 0:
            st.info("📊 Base vetorial vazia - processando e indexando PDFs...")
            with st.spinner("⚙️ Processando PDFs e criando índice vetorial... Pode levar vários minutos."):
                pdfs_data = pdf_processor.process_all_pdfs()

                if pdfs_data:
                    vector_store.add_documents(pdfs_data)
                    st.success(f"✅ {len(pdfs_data)} documentos processados e indexados!")
                    st.balloons()
                else:
                    st.warning("⚠️ Nenhum PDF encontrado para processar")
                    return False

        # Marcar como inicializado
        st.session_state.auto_initialized = True
        return True

    except Exception as e:
        st.error(f"❌ Erro na inicialização automática: {e}")
        import traceback
        st.error(traceback.format_exc())
        return False


# Inicializa componentes
vector_store, agent, pdf_processor = init_components()

if not all([vector_store, agent, pdf_processor]):
    st.error("⚠️ Falha ao inicializar componentes. Verifique as configurações.")
    st.stop()

# Inicializa histórico de mensagens
if 'messages' not in st.session_state:
    st.session_state.messages = []

if 'last_save_path' not in st.session_state:
    st.session_state.last_save_path = None

# ========== INICIALIZAÇÃO AUTOMÁTICA ==========
with st.spinner("🚀 Preparando sistema..."):
    if not auto_initialize(pdf_processor, vector_store):
        st.error("⚠️ Falha na inicialização automática. Verifique os logs acima.")
        st.stop()

# Atualiza estatísticas após inicialização
stats = get_vectorstore_stats(vector_store)


# ========== SIDEBAR ==========
with st.sidebar:
    st.header("📊 Status do Sistema")

    # Status da base vetorial (apenas leitura)
    if stats['ready']:
        st.success(f"✅ Sistema pronto!")

        st.metric("Total de Chunks", stats['total_chunks'])

        with st.expander("📚 Detalhes da Base"):
            st.info(f"📖 Base (40 artigos): {stats['base']} chunks")
            st.info(f"⭐ Principais (2 artigos): {stats['principais']} chunks")
            st.info(f"🎯 Metodologia: {stats['metodologia']} chunks")
    else:
        st.warning("⚠️ Sistema inicializando...")

    st.markdown("---")

    # Upload de metodologia adicional (opcional)
    st.subheader("📎 Upload Adicional")
    st.caption("Adicione PDFs extras de metodologia (opcional)")

    uploaded_file = st.file_uploader(
        "Selecione PDF",
        type=['pdf'],
        key="metodologia_upload"
    )

    if uploaded_file:
        if st.button("➕ Processar PDF", use_container_width=True):
            with st.spinner("Processando PDF..."):
                try:
                    # Upload e processa o PDF
                    pdf_data = pdf_processor.upload_single_pdf(
                        uploaded_file,
                        uploaded_file.name,
                        category='metodologia'
                    )

                    if pdf_data:
                        # Adiciona ao vector store
                        vector_store.add_documents([pdf_data])
                        st.success(f"✅ '{uploaded_file.name}' adicionado!")
                        st.rerun()
                    else:
                        st.error("❌ Erro ao extrair conteúdo")

                except Exception as e:
                    st.error(f"❌ Erro: {e}")

    st.markdown("---")

    # Opções avançadas (escondidas)
    with st.expander("⚙️ Opções Avançadas"):
        if st.button("🔄 Reindexar Base", use_container_width=True):
            with st.spinner("Reindexando..."):
                try:
                    st.session_state.auto_initialized = False
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Erro: {e}")

    st.markdown("---")

    # Tipo de seção
    section_type = st.selectbox(
        "📝 Tipo de Seção",
        ["generico", "introducao", "metodologia", "resultados", "conclusao"],
        index=0,
        help="Escolha o tipo de seção do TCC"
    )

    st.markdown("---")

    # Botão limpar conversa
    if st.button("🗑️ Limpar Conversa", use_container_width=True):
        st.session_state.messages = []
        st.session_state.last_save_path = None
        st.rerun()

    # Info
    st.caption("💡 **Dica:** Converse naturalmente sobre seu TCC. O assistente respeitará a hierarquia dos documentos.")


# ========== MAIN INTERFACE ==========
st.title("🎓 TCC Agent - Assistente Acadêmico")
st.caption("Chat inteligente com hierarquia de documentos: Metodologia > Principais > Base")

# Mostra histórico de mensagens
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Input do usuário
if prompt := st.chat_input("Digite sua solicitação ou feedback sobre o texto..."):
    # Adiciona mensagem do usuário
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.write(prompt)

    # Gera resposta
    with st.chat_message("assistant"):
        with st.spinner("🤔 Analisando documentos e gerando resposta..."):
            try:
                response = agent.generate_text(
                    prompt=prompt,
                    section_type=section_type,
                    context_history=st.session_state.messages
                )

                st.write(response)

                # Adiciona resposta ao histórico
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response
                })

                # Salva automaticamente
                save_path = save_to_file(response, prompt)
                st.session_state.last_save_path = save_path

            except Exception as e:
                st.error(f"❌ Erro ao gerar texto: {e}")

# Botão de download (se houver histórico)
if len(st.session_state.messages) > 0:
    # Junta toda a conversa
    full_conversation = "\n\n".join([
        f"**{'Usuário' if msg['role'] == 'user' else 'Assistente'}:** {msg['content']}"
        for msg in st.session_state.messages
    ])

    st.download_button(
        label="📥 Baixar Conversa Completa",
        data=full_conversation,
        file_name=f"tcc_conversa_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        mime="text/plain",
        use_container_width=True
    )

# Footer
st.markdown("---")
st.caption("""
🎓 **TCC Agent Simplificado**
Hierarquia automática: Metodologia (prioridade máxima) → Principais → Base
Citações ABNT geradas automaticamente pelo Claude
""")
