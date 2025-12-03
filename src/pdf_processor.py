"""
Módulo para download e processamento de PDFs do Google Drive.
"""
import os
import re
from pathlib import Path
from typing import List, Dict
import gdown
import pdfplumber
from PyPDF2 import PdfReader


class PDFProcessor:
    """Processa PDFs: download do Google Drive e extração de texto."""

    def __init__(self, base_folder_40: str, base_folder_2: str):
        """
        Inicializa o processador de PDFs.

        Args:
            base_folder_40: ID da pasta do Google Drive com 40 artigos
            base_folder_2: ID da pasta do Google Drive com 2 artigos principais
        """
        self.base_folder_40 = base_folder_40
        self.base_folder_2 = base_folder_2
        self.referencias_path = Path("referencias")
        self.base_40_path = self.referencias_path / "base_40"
        self.principais_2_path = self.referencias_path / "principais_2"

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

            print(f"✅ Download concluído para {output_path}")
            return True

        except Exception as e:
            print(f"❌ Erro ao fazer download de {folder_id}: {e}")
            return False

    def download_all_pdfs(self) -> bool:
        """
        Faz download de todos os PDFs necessários.

        Returns:
            bool: True se todos os downloads foram bem-sucedidos
        """
        print("\n📥 Iniciando download dos PDFs do Google Drive...")

        # Download dos 40 artigos base
        print("\n1️⃣ Baixando 40 artigos base...")
        success_40 = self.download_from_drive(self.base_folder_40, self.base_40_path)

        # Download dos 2 artigos principais
        print("\n2️⃣ Baixando 2 artigos principais...")
        success_2 = self.download_from_drive(self.base_folder_2, self.principais_2_path)

        if success_40 and success_2:
            print("\n✅ Todos os PDFs foram baixados com sucesso!")
            return True
        else:
            print("\n⚠️ Alguns downloads falharam. Verifique a conexão e permissões.")
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
            print(f"❌ Erro ao extrair texto de {pdf_path.name}: {e}")
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

        # Processa PDFs da base 40
        print("\n📚 Processando 40 artigos base...")
        base_40_pdfs = list(self.base_40_path.glob("**/*.pdf"))
        for pdf_path in base_40_pdfs:
            print(f"  📄 Processando: {pdf_path.name}")
            pdf_data = self.extract_text_from_pdf(pdf_path)
            if pdf_data:
                pdf_data['category'] = 'base_40'
                all_pdfs.append(pdf_data)

        # Processa PDFs principais
        print("\n📖 Processando 2 artigos principais...")
        principais_pdfs = list(self.principais_2_path.glob("**/*.pdf"))
        for pdf_path in principais_pdfs:
            print(f"  📄 Processando: {pdf_path.name}")
            pdf_data = self.extract_text_from_pdf(pdf_path)
            if pdf_data:
                pdf_data['category'] = 'principais_2'
                all_pdfs.append(pdf_data)

        print(f"\n✅ Total de {len(all_pdfs)} PDFs processados!")
        return all_pdfs

    def check_pdfs_exist(self) -> Dict[str, bool]:
        """
        Verifica se os PDFs já foram baixados.

        Returns:
            Dict com status de cada categoria
        """
        base_40_exists = len(list(self.base_40_path.glob("*.pdf"))) > 0
        principais_2_exists = len(list(self.principais_2_path.glob("*.pdf"))) > 0

        return {
            'base_40': base_40_exists,
            'principais_2': principais_2_exists,
            'all_ready': base_40_exists and principais_2_exists
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
    print(f"\n📊 Resumo: {len(pdfs)} PDFs processados")
