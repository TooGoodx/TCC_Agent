"""
Módulo para gerenciamento da base vetorial usando ChromaDB.
"""
import os
import re
from pathlib import Path
from typing import List, Dict, Optional
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer


class SimpleTextSplitter:
    """Text splitter simples para dividir documentos em chunks."""

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200, separators: List[str] = None):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", ". ", " ", ""]

    def split_text(self, text: str) -> List[str]:
        """Divide texto em chunks."""
        chunks = []

        # Tenta dividir pelos separadores na ordem
        for separator in self.separators:
            if separator in text:
                parts = text.split(separator)
                current_chunk = ""

                for part in parts:
                    if len(current_chunk) + len(part) + len(separator) <= self.chunk_size:
                        current_chunk += part + separator
                    else:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                        current_chunk = part + separator

                if current_chunk:
                    chunks.append(current_chunk.strip())
                break

        # Se não conseguiu dividir, divide por tamanho fixo
        if not chunks:
            for i in range(0, len(text), self.chunk_size - self.chunk_overlap):
                chunks.append(text[i:i + self.chunk_size])

        return [c for c in chunks if c.strip()]


class VectorStore:
    """Gerencia a base vetorial para busca semântica nos artigos."""

    def __init__(self, persist_directory: str = "vectorstore/chroma_db"):
        """
        Inicializa o vector store.

        Args:
            persist_directory: Diretório para persistir o ChromaDB
        """
        self.persist_directory = persist_directory
        self.collection_name = "tcc_articles"

        # Inicializa ChromaDB
        self.client = chromadb.PersistentClient(path=persist_directory)

        # Carrega modelo de embeddings (multilingual para português)
        print("🔄 Carregando modelo de embeddings...")
        self.embedding_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        print("✅ Modelo de embeddings carregado!")

        # Text splitter para dividir documentos grandes
        self.text_splitter = SimpleTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", ". ", " ", ""]
        )

    def _get_or_create_collection(self):
        """Obtém ou cria a coleção no ChromaDB."""
        try:
            # Tenta obter coleção existente
            collection = self.client.get_collection(name=self.collection_name)
            print(f"📚 Coleção '{self.collection_name}' carregada ({collection.count()} documentos)")
        except:
            # Cria nova coleção
            collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "Artigos acadêmicos para TCC sobre futebol"}
            )
            print(f"✨ Nova coleção '{self.collection_name}' criada")

        return collection

    def _create_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Cria embeddings para uma lista de textos.

        Args:
            texts: Lista de textos

        Returns:
            Lista de embeddings
        """
        embeddings = self.embedding_model.encode(
            texts,
            show_progress_bar=True,
            convert_to_numpy=True
        )
        return embeddings.tolist()

    def add_documents(self, pdfs_data: List[Dict], force_reindex: bool = False):
        """
        Adiciona documentos PDF à base vetorial.

        Args:
            pdfs_data: Lista de dicionários com dados dos PDFs
            force_reindex: Se True, recria o índice do zero
        """
        collection = self._get_or_create_collection()

        # Se force_reindex, limpa a coleção
        if force_reindex and collection.count() > 0:
            print("🗑️ Limpando coleção existente...")
            self.client.delete_collection(name=self.collection_name)
            collection = self._get_or_create_collection()

        # Se a coleção já tem documentos e não forçou reindex, pula
        if collection.count() > 0 and not force_reindex:
            print(f"✅ Base vetorial já contém {collection.count()} documentos")
            return

        print(f"\n📝 Processando {len(pdfs_data)} PDFs para indexação...")

        all_chunks = []
        all_metadatas = []
        all_ids = []
        chunk_counter = 0

        for pdf in pdfs_data:
            print(f"  📄 Dividindo '{pdf['filename']}' em chunks...")

            # Divide o texto em chunks
            chunks = self.text_splitter.split_text(pdf['full_text'])

            for i, chunk in enumerate(chunks):
                # Cria ID único para o chunk
                chunk_id = f"{pdf['filename']}_chunk_{i}"

                # Metadados do chunk
                metadata = {
                    'filename': pdf['filename'],
                    'category': pdf['category'],
                    'chunk_index': i,
                    'total_chunks': len(chunks),
                    'author': pdf.get('metadata', {}).get('author', 'Desconhecido'),
                    'title': pdf.get('metadata', {}).get('title', pdf['filename'])
                }

                all_chunks.append(chunk)
                all_metadatas.append(metadata)
                all_ids.append(chunk_id)
                chunk_counter += 1

        print(f"\n🔢 Total de chunks criados: {chunk_counter}")
        print("🧮 Criando embeddings...")

        # Cria embeddings
        embeddings = self._create_embeddings(all_chunks)

        print("💾 Salvando no ChromaDB...")

        # Adiciona à coleção em batches (ChromaDB tem limite)
        batch_size = 100
        for i in range(0, len(all_chunks), batch_size):
            end_idx = min(i + batch_size, len(all_chunks))

            collection.add(
                embeddings=embeddings[i:end_idx],
                documents=all_chunks[i:end_idx],
                metadatas=all_metadatas[i:end_idx],
                ids=all_ids[i:end_idx]
            )

            print(f"  ✅ Batch {i//batch_size + 1}/{(len(all_chunks)-1)//batch_size + 1} adicionado")

        print(f"\n✅ Base vetorial criada com sucesso! Total: {collection.count()} chunks")

    def search(
        self,
        query: str,
        n_results: int = 10,
        category_filter: Optional[str] = None
    ) -> List[Dict]:
        """
        Realiza busca semântica na base vetorial.

        Args:
            query: Texto da busca
            n_results: Número de resultados a retornar
            category_filter: Filtrar por categoria ('base_40', 'principais_2', ou None para todos)

        Returns:
            Lista de dicionários com resultados
        """
        collection = self._get_or_create_collection()

        # Verifica se a coleção está vazia
        if collection.count() == 0:
            print("⚠️ Base vetorial vazia. Execute a indexação primeiro.")
            return []

        # Cria embedding da query
        query_embedding = self._create_embeddings([query])[0]

        # Prepara filtro
        where_filter = None
        if category_filter:
            where_filter = {"category": category_filter}

        # Realiza busca
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_filter
        )

        # Formata resultados
        formatted_results = []
        for i in range(len(results['ids'][0])):
            formatted_results.append({
                'id': results['ids'][0][i],
                'document': results['documents'][0][i],
                'metadata': results['metadatas'][0][i],
                'distance': results['distances'][0][i] if 'distances' in results else None
            })

        return formatted_results

    def get_context_for_prompt(
        self,
        query: str,
        n_results: int = 5,
        category_filter: Optional[str] = None
    ) -> str:
        """
        Obtém contexto formatado para incluir no prompt do Claude.

        Args:
            query: Texto da busca
            n_results: Número de resultados
            category_filter: Filtrar por categoria

        Returns:
            String formatada com o contexto
        """
        results = self.search(query, n_results, category_filter)

        if not results:
            return "Nenhum contexto relevante encontrado."

        context_parts = ["CONTEXTO DOS ARTIGOS ACADÊMICOS:\n"]

        for i, result in enumerate(results, 1):
            metadata = result['metadata']
            document = result['document']

            context_parts.append(f"\n--- TRECHO {i} ---")
            context_parts.append(f"Fonte: {metadata.get('filename', 'Desconhecido')}")
            context_parts.append(f"Autor: {metadata.get('author', 'Desconhecido')}")
            context_parts.append(f"Categoria: {metadata.get('category', 'Desconhecido')}")
            context_parts.append(f"\nTexto:\n{document}")
            context_parts.append("---\n")

        return "\n".join(context_parts)

    def get_stats(self) -> Dict:
        """
        Retorna estatísticas da base vetorial.

        Returns:
            Dicionário com estatísticas
        """
        try:
            collection = self._get_or_create_collection()
            total_docs = collection.count()

            # Conta por categoria
            results = collection.get()
            categories = {}
            for metadata in results['metadatas']:
                cat = metadata.get('category', 'unknown')
                categories[cat] = categories.get(cat, 0) + 1

            return {
                'total_chunks': total_docs,
                'by_category': categories,
                'ready': total_docs > 0
            }
        except Exception as e:
            return {
                'total_chunks': 0,
                'by_category': {},
                'ready': False,
                'error': str(e)
            }

    def reset(self):
        """Reseta a base vetorial (apaga tudo)."""
        try:
            self.client.delete_collection(name=self.collection_name)
            print("🗑️ Base vetorial resetada com sucesso")
            return True
        except Exception as e:
            print(f"❌ Erro ao resetar base vetorial: {e}")
            return False


if __name__ == "__main__":
    # Teste do vector store
    vector_store = VectorStore()

    # Obtém estatísticas
    stats = vector_store.get_stats()
    print(f"\n📊 Estatísticas da base vetorial:")
    print(f"  Total de chunks: {stats['total_chunks']}")
    print(f"  Por categoria: {stats['by_category']}")
    print(f"  Pronto para uso: {stats['ready']}")

    # Teste de busca
    if stats['ready']:
        print("\n🔍 Teste de busca:")
        results = vector_store.search("análise tática futebol", n_results=3)
        print(f"Encontrados {len(results)} resultados")
        for r in results:
            print(f"  - {r['metadata']['filename']}: {r['document'][:100]}...")
