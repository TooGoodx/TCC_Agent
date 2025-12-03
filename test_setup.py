"""
Script de teste para verificar a instalação e configuração do TCC Agent.
"""
import sys
from pathlib import Path

print("🧪 TCC AGENT - TESTE DE CONFIGURAÇÃO\n")
print("="*60)

# 1. Verificar Python
print("\n1️⃣ Verificando versão do Python...")
print(f"   Python {sys.version}")
if sys.version_info >= (3, 11):
    print("   ✅ Versão compatível (3.11+)")
else:
    print("   ⚠️ Recomendado Python 3.11+")

# 2. Verificar estrutura de diretórios
print("\n2️⃣ Verificando estrutura de diretórios...")
required_dirs = [
    "src",
    "referencias",
    "referencias/base_40",
    "referencias/principais_2",
    "vectorstore",
    "vectorstore/chroma_db",
    "outputs",
    "outputs/historico"
]

for dir_path in required_dirs:
    if Path(dir_path).exists():
        print(f"   ✅ {dir_path}")
    else:
        print(f"   ❌ {dir_path} - FALTANDO")

# 3. Verificar arquivos principais
print("\n3️⃣ Verificando arquivos principais...")
required_files = [
    "app.py",
    "requirements.txt",
    ".env",
    ".gitignore",
    "README.md",
    "src/__init__.py",
    "src/pdf_processor.py",
    "src/vector_store.py",
    "src/claude_agent.py",
    "src/prompts.py",
    "src/citation_manager.py"
]

for file_path in required_files:
    if Path(file_path).exists():
        print(f"   ✅ {file_path}")
    else:
        print(f"   ❌ {file_path} - FALTANDO")

# 4. Verificar .env
print("\n4️⃣ Verificando configuração (.env)...")
try:
    from dotenv import load_dotenv
    import os

    load_dotenv()

    api_key = os.getenv("ANTHROPIC_API_KEY")
    folder_40 = os.getenv("GOOGLE_DRIVE_FOLDER_40")
    folder_2 = os.getenv("GOOGLE_DRIVE_FOLDER_2")

    if api_key:
        print(f"   ✅ ANTHROPIC_API_KEY configurada ({api_key[:15]}...)")
    else:
        print("   ❌ ANTHROPIC_API_KEY não encontrada")

    if folder_40:
        print(f"   ✅ GOOGLE_DRIVE_FOLDER_40 configurada")
    else:
        print("   ❌ GOOGLE_DRIVE_FOLDER_40 não encontrada")

    if folder_2:
        print(f"   ✅ GOOGLE_DRIVE_FOLDER_2 configurada")
    else:
        print("   ❌ GOOGLE_DRIVE_FOLDER_2 não encontrada")

except ImportError:
    print("   ⚠️ python-dotenv não instalado (rode: pip install -r requirements.txt)")

# 5. Verificar dependências
print("\n5️⃣ Verificando dependências Python...")
dependencies = [
    "streamlit",
    "anthropic",
    "langchain",
    "chromadb",
    "pdfplumber",
    "PyPDF2",
    "dotenv",
    "gdown",
    "docx",
    "sentence_transformers"
]

installed = []
missing = []

for dep in dependencies:
    try:
        if dep == "dotenv":
            __import__("dotenv")
        elif dep == "docx":
            __import__("docx")
        else:
            __import__(dep)
        installed.append(dep)
        print(f"   ✅ {dep}")
    except ImportError:
        missing.append(dep)
        print(f"   ❌ {dep} - NÃO INSTALADO")

# 6. Verificar importações dos módulos
print("\n6️⃣ Verificando importações dos módulos...")
try:
    from src.pdf_processor import PDFProcessor
    print("   ✅ PDFProcessor")
except Exception as e:
    print(f"   ❌ PDFProcessor - {e}")

try:
    from src.vector_store import VectorStore
    print("   ✅ VectorStore")
except Exception as e:
    print(f"   ❌ VectorStore - {e}")

try:
    from src.claude_agent import ClaudeAgent
    print("   ✅ ClaudeAgent")
except Exception as e:
    print(f"   ❌ ClaudeAgent - {e}")

try:
    from src.citation_manager import CitationManager
    print("   ✅ CitationManager")
except Exception as e:
    print(f"   ❌ CitationManager - {e}")

try:
    from src.prompts import SYSTEM_PROMPT
    print("   ✅ Prompts")
except Exception as e:
    print(f"   ❌ Prompts - {e}")

# 7. Verificar PDFs
print("\n7️⃣ Verificando PDFs baixados...")
base_40_pdfs = list(Path("referencias/base_40").glob("**/*.pdf"))
principais_2_pdfs = list(Path("referencias/principais_2").glob("**/*.pdf"))

print(f"   📚 Base 40: {len(base_40_pdfs)} PDFs")
print(f"   ⭐ Principais 2: {len(principais_2_pdfs)} PDFs")

if len(base_40_pdfs) == 0 and len(principais_2_pdfs) == 0:
    print("   ⚠️ Nenhum PDF encontrado. Use a interface para baixar do Google Drive.")

# 8. Resumo
print("\n" + "="*60)
print("📊 RESUMO DO TESTE\n")

total_checks = len(required_dirs) + len(required_files) + len(dependencies) + 5
passed = 0

if sys.version_info >= (3, 11):
    passed += 1

passed += sum(1 for d in required_dirs if Path(d).exists())
passed += sum(1 for f in required_files if Path(f).exists())
passed += len(installed)

print(f"Verificações passadas: {passed}/{total_checks}")

if missing:
    print(f"\n⚠️ Dependências faltando: {', '.join(missing)}")
    print("   Rode: pip install -r requirements.txt")
else:
    print("\n✅ Todas as dependências instaladas!")

if len(base_40_pdfs) == 0 and len(principais_2_pdfs) == 0:
    print("\n⚠️ PDFs não baixados ainda")
    print("   Use a interface Streamlit para baixar do Google Drive")

print("\n🚀 Para iniciar a aplicação, rode:")
print("   streamlit run app.py")

print("\n" + "="*60)
