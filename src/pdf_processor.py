"""
Módulo para download e processamento de PDFs do Google Drive.
Suporta 3 níveis de documentos com hierarquia de importância:
- metodologia: máxima prioridade
- principais_2: alta prioridade
- base_40: contexto adicional
"""
import os
import re
import shutil
from pathlib import Path
from typing import List, Dict, Optional, BinaryIO
import gdown
import pdfplumber
from PyPDF2 import PdfReader


class PDFProcessor:
    """Processa PDFs: download do Google Drive, upload local e extração de texto."""

    # Pesos de prioridade para cada categoria
    CATEGORY_WEIGHTS = {
        'metodologia': 3.0,
        'principais_2': 2.0,
        'base_40': 1.0
    }

    def __init__(
        self,
        base_folder_40: str,
        base_folder_2: str,
        base_folder_metodologia: Optional[str] = None
    ):
        """
        Inicializa o processador de PDFs.

        Args:
            base_folder_40: ID da pasta do Google Drive com 40 artigos
            base_folder_2: ID da pasta do Google Drive com 2 artigos principais
            base_folder_metodologia: ID da pasta do Google Drive com artigos de metodologia (opcional)
        """
        self.base_folder_40 = base_folder_40
        self.base_folder_2 = base_folder_2
        self.base_folder_metodologia = base_folder_metodologia
        self.referencias_path = Path("referencias")
        self.base_40_path = self.referencias_path / "base_40"
        self.principais_2_path = self.referencias_path / "principais_2"
        self.metodologia_path = self.referencias_path / "metodologia_upload"

        # Garante que as pastas existem
        self.metodologia_path.mkdir(parents=True, exist_ok=True)

    def download_from_drive(self, folder_id: str, output_path: Path) -> bool:
        """
        Faz download de todos os PDFs de uma pasta do Google Drive.

        Args:
            folder_id: ID da pasta no Google Drive
            output_path: Caminho local para salvar os arquivos

        Returns:
            bool: True se bem-sucedido
        """
        try:
            # URL da pasta do Google Drive
            folder_url = f"https://drive.google.com/drive/folders/{folder_id}"

            # Garante que o diretório existe
            output_path.mkdir(parents=True, exist_ok=True)

            # Download da pasta inteira
            gdown.download_folder(
                url=folder_url,
                output=str(output_path),
                quiet=False,
                use_cookies=False
            )

            print(f"Download concluido para {output_path}")
            return True

        except Exception as e:
            print(f"Erro ao fazer download de {folder_id}: {e}")
            return False

    def download_all_pdfs(self) -> bool:
        """
        Faz download de todos os PDFs necessários.

        Returns:
            bool: True se todos os downloads foram bem-sucedidos
        """
        print("\nIniciando download dos PDFs do Google Drive...")

        # Download dos 40 artigos base
        print("\n1. Baixando 40 artigos base...")
        success_40 = self.download_from_drive(self.base_folder_40, self.base_40_path)

        # Download dos 2 artigos principais
        print("\n2. Baixando 2 artigos principais...")
        success_2 = self.download_from_drive(self.base_folder_2, self.principais_2_path)

        # Download dos artigos de metodologia (se configurado)
        success_metodologia = True
        if self.base_folder_metodologia:
            print("\n3. Baixando artigos de metodologia...")
            success_metodologia = self.download_from_drive(
                self.base_folder_metodologia,
                self.metodologia_path
            )

        if success_40 and success_2 and success_metodologia:
            print("\nTodos os PDFs foram baixados com sucesso!")
            return True
        else:
            print("\nAlguns downloads falharam. Verifique a conexao e permissoes.")
            return False

    def upload_single_pdf(
        self,
        uploaded_file: BinaryIO,
        filename: str,
        category: str = 'metodologia'
    ) -> Dict:
        """
        Recebe um PDF via upload (Streamlit) e salva localmente.

        Args:
            uploaded_file: Arquivo uploadado (st.file_uploader)
            filename: Nome do arquivo
            category: Categoria do documento ('metodologia', 'principais_2', 'base_40')

        Returns:
            Dict com informações do PDF processado
        """
        # Define o diretório de destino baseado na categoria
        if category == 'metodologia':
            dest_path = self.metodologia_path
        elif category == 'principais_2':
            dest_path = self.principais_2_path
        else:
            dest_path = self.base_40_path

        dest_path.mkdir(parents=True, exist_ok=True)

        # Salva o arquivo
        file_path = dest_path / filename
        with open(file_path, 'wb') as f:
            f.write(uploaded_file.read())

        print(f"PDF salvo em: {file_path}")

        # Extrai texto do PDF
        pdf_data = self.extract_text_from_pdf(file_path)
        if pdf_data:
            pdf_data['category'] = category
            pdf_data['weight'] = self.CATEGORY_WEIGHTS.get(category, 1.0)

        return pdf_data

    def remove_pdf(self, filename: str, category: str) -> bool:
        """
        Remove um PDF da categoria especificada.

        Args:
            filename: Nome do arquivo
            category: Categoria do documento

        Returns:
            bool: True se removido com sucesso
        """
        if category == 'metodologia':
            file_path = self.metodologia_path / filename
        elif category == 'principais_2':
            file_path = self.principais_2_path / filename
        else:
            file_path = self.base_40_path / filename

        try:
            if file_path.exists():
                file_path.unlink()
                print(f"PDF removido: {file_path}")
                return True
            return False
        except Exception as e:
            print(f"Erro ao remover PDF: {e}")
            return False

    def extract_text_from_pdf(self, pdf_path: Path) -> Dict[str, any]:
        """
        Extrai texto de um PDF usando pdfplumber (melhor para PDFs acadêmicos).

        Args:
            pdf_path: Caminho para o arquivo PDF

        Returns:
            Dict com informações do PDF (nome, texto, páginas)
        """
        try:
            text_content = []

            with pdfplumber.open(pdf_path) as pdf:
                num_pages = len(pdf.pages)

                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text()
                    if text:
                        # Limpa o texto
                        text = self._clean_text(text)
                        text_content.append({
                            'page': page_num,
                            'text': text
                        })

            # Extrai metadados usando PyPDF2
            metadata = self._extract_metadata(pdf_path)

            return {
                'filename': pdf_path.name,
                'path': str(pdf_path),
                'num_pages': num_pages,
                'pages': text_content,
                'full_text': ' '.join([p['text'] for p in text_content]),
                'metadata': metadata
            }

        except Exception as e:
            print(f"Erro ao extrair texto de {pdf_path.name}: {e}")
            return None

    def _extract_metadata(self, pdf_path: Path) -> Dict:
        """Extrai metadados do PDF (autor, título, etc.)."""
        try:
            reader = PdfReader(pdf_path)
            metadata = reader.metadata

            return {
                'title': metadata.get('/Title', ''),
                'author': metadata.get('/Author', ''),
                'subject': metadata.get('/Subject', ''),
                'creator': metadata.get('/Creator', ''),
                'producer': metadata.get('/Producer', ''),
                'creation_date': metadata.get('/CreationDate', '')
            }
        except:
            return {}

    def _clean_text(self, text: str) -> str:
        """
        Limpa e normaliza o texto extraído do PDF.

        Args:
            text: Texto bruto

        Returns:
            str: Texto limpo
        """
        # Remove quebras de linha múltiplas
        text = re.sub(r'\n{3,}', '\n\n', text)

        # Remove espaços múltiplos
        text = re.sub(r' {2,}', ' ', text)

        # Remove hífens de quebra de linha
        text = re.sub(r'-\n', '', text)

        # Normaliza espaços ao redor de pontuação
        text = re.sub(r'\s+([.,;:!?])', r'\1', text)

        return text.strip()

    def process_all_pdfs(self) -> List[Dict]:
        """
        Processa todos os PDFs baixados e retorna lista com conteúdo.

        Returns:
            List[Dict]: Lista de dicionários com informações dos PDFs
        """
        all_pdfs = []

        # Processa PDFs de METODOLOGIA (máxima prioridade)
        print("\nProcessando artigos de METODOLOGIA (prioridade maxima)...")
        metodologia_pdfs = list(self.metodologia_path.glob("**/*.pdf"))
        for pdf_path in metodologia_pdfs:
            print(f"  Processando: {pdf_path.name}")
            pdf_data = self.extract_text_from_pdf(pdf_path)
            if pdf_data:
                pdf_data['category'] = 'metodologia'
                pdf_data['weight'] = self.CATEGORY_WEIGHTS['metodologia']
                all_pdfs.append(pdf_data)

        # Processa PDFs principais (alta prioridade)
        print("\nProcessando 2 artigos principais (alta prioridade)...")
        principais_pdfs = list(self.principais_2_path.glob("**/*.pdf"))
        for pdf_path in principais_pdfs:
            print(f"  Processando: {pdf_path.name}")
            pdf_data = self.extract_text_from_pdf(pdf_path)
            if pdf_data:
                pdf_data['category'] = 'principais_2'
                pdf_data['weight'] = self.CATEGORY_WEIGHTS['principais_2']
                all_pdfs.append(pdf_data)

        # Processa PDFs da base 40 (contexto)
        print("\nProcessando 40 artigos base (contexto)...")
        base_40_pdfs = list(self.base_40_path.glob("**/*.pdf"))
        for pdf_path in base_40_pdfs:
            print(f"  Processando: {pdf_path.name}")
            pdf_data = self.extract_text_from_pdf(pdf_path)
            if pdf_data:
                pdf_data['category'] = 'base_40'
                pdf_data['weight'] = self.CATEGORY_WEIGHTS['base_40']
                all_pdfs.append(pdf_data)

        print(f"\nTotal de {len(all_pdfs)} PDFs processados!")
        print(f"   - Metodologia: {len(metodologia_pdfs)}")
        print(f"   - Principais: {len(principais_pdfs)}")
        print(f"   - Base: {len(base_40_pdfs)}")
        return all_pdfs

    def get_pdfs_by_category(self) -> Dict[str, List[str]]:
        """
        Retorna lista de PDFs organizados por categoria.

        Returns:
            Dict com listas de nomes de arquivos por categoria
        """
        return {
            'metodologia': [p.name for p in self.metodologia_path.glob("*.pdf")],
            'principais_2': [p.name for p in self.principais_2_path.glob("*.pdf")],
            'base_40': [p.name for p in self.base_40_path.glob("*.pdf")]
        }

    def check_pdfs_exist(self) -> Dict[str, bool]:
        """
        Verifica se os PDFs já foram baixados.

        Returns:
            Dict com status de cada categoria
        """
        base_40_exists = len(list(self.base_40_path.glob("*.pdf"))) > 0
        principais_2_exists = len(list(self.principais_2_path.glob("*.pdf"))) > 0
        metodologia_exists = len(list(self.metodologia_path.glob("*.pdf"))) > 0

        return {
            'base_40': base_40_exists,
            'principais_2': principais_2_exists,
            'metodologia': metodologia_exists,
            'all_ready': base_40_exists and principais_2_exists,
            'counts': {
                'metodologia': len(list(self.metodologia_path.glob("*.pdf"))),
                'principais_2': len(list(self.principais_2_path.glob("*.pdf"))),
                'base_40': len(list(self.base_40_path.glob("*.pdf")))
            }
        }


if __name__ == "__main__":
    # Teste do processador
    from dotenv import load_dotenv
    load_dotenv()

    folder_40 = os.getenv("GOOGLE_DRIVE_FOLDER_40")
    folder_2 = os.getenv("GOOGLE_DRIVE_FOLDER_2")

    processor = PDFProcessor(folder_40, folder_2)

    # Verifica se PDFs já existem
    status = processor.check_pdfs_exist()
    print(f"Status dos PDFs: {status}")

    # Se não existirem, faz download
    if not status['all_ready']:
        processor.download_all_pdfs()

    # Processa todos os PDFs
    pdfs = processor.process_all_pdfs()
    print(f"\nResumo: {len(pdfs)} PDFs processados")
