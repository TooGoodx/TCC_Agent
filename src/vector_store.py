"""
Módulo para gerenciamento da base vetorial usando ChromaDB.
Suporta hierarquia de documentos com pesos de relevância:
- metodologia: peso 3.0 (máxima prioridade)
- principais_2: peso 2.0 (alta prioridade)
- base_40: peso 1.0 (contexto adicional)
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

    # Pesos de relevância por categoria
    CATEGORY_WEIGHTS = {
        'metodologia': 3.0,
        'principais_2': 2.0,
        'base_40': 1.0
    }

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
        print("Carregando modelo de embeddings...")
        self.embedding_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        print("Modelo de embeddings carregado!")

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
            print(f"Colecao '{self.collection_name}' carregada ({collection.count()} documentos)")
        except:
            # Cria nova coleção
            collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "Artigos acadêmicos para TCC sobre futebol"}
            )
            print(f"Nova colecao '{self.collection_name}' criada")

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
            print("Limpando colecao existente...")
            self.client.delete_collection(name=self.collection_name)
            collection = self._get_or_create_collection()

        # Se a coleção já tem documentos e não forçou reindex, pula
        if collection.count() > 0 and not force_reindex:
            print(f"Base vetorial ja contem {collection.count()} documentos")
            return

        print(f"\nProcessando {len(pdfs_data)} PDFs para indexacao...")

        all_chunks = []
        all_metadatas = []
        all_ids = []
        chunk_counter = 0

        for pdf in pdfs_data:
            print(f"  Dividindo '{pdf['filename']}' em chunks...")

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

        print(f"\nTotal de chunks criados: {chunk_counter}")
        print("Criando embeddings...")

        # Cria embeddings
        embeddings = self._create_embeddings(all_chunks)

        print("Salvando no ChromaDB...")

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

            print(f"  Batch {i//batch_size + 1}/{(len(all_chunks)-1)//batch_size + 1} adicionado")

        print(f"\nBase vetorial criada com sucesso! Total: {collection.count()} chunks")

    def search(
        self,
        query: str,
        n_results: int = 10,
        category_filter: Optional[str] = None,
        apply_weights: bool = True
    ) -> List[Dict]:
        """
        Realiza busca semântica na base vetorial com boost de relevância por categoria.

        Args:
            query: Texto da busca
            n_results: Número de resultados a retornar
            category_filter: Filtrar por categoria ('base_40', 'principais_2', 'metodologia', ou None para todos)
            apply_weights: Se True, aplica boost de relevância por categoria

        Returns:
            Lista de dicionários com resultados ordenados por relevância ponderada
        """
        collection = self._get_or_create_collection()

        # Verifica se a coleção está vazia
        if collection.count() == 0:
            print("Base vetorial vazia. Execute a indexacao primeiro.")
            return []

        # Cria embedding da query
        query_embedding = self._create_embeddings([query])[0]

        # Prepara filtro
        where_filter = None
        if category_filter:
            where_filter = {"category": category_filter}

        # Busca mais resultados para depois filtrar com pesos
        search_n = n_results * 3 if apply_weights and not category_filter else n_results

        # Realiza busca
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=search_n,
            where=where_filter
        )

        # Formata resultados
        formatted_results = []
        for i in range(len(results['ids'][0])):
            category = results['metadatas'][0][i].get('category', 'base_40')
            distance = results['distances'][0][i] if 'distances' in results else 1.0

            # Calcula score com peso da categoria
            weight = self.CATEGORY_WEIGHTS.get(category, 1.0)
            # Score menor = mais relevante, então dividimos a distância pelo peso
            weighted_score = distance / weight if apply_weights else distance

            formatted_results.append({
                'id': results['ids'][0][i],
                'document': results['documents'][0][i],
                'metadata': results['metadatas'][0][i],
                'distance': distance,
                'weighted_score': weighted_score,
                'category_weight': weight
            })

        # Ordena por score ponderado (menor = mais relevante)
        if apply_weights:
            formatted_results.sort(key=lambda x: x['weighted_score'])

        return formatted_results[:n_results]

    def search_by_hierarchy(
        self,
        query: str,
        n_metodologia: int = 2,
        n_principais: int = 3,
        n_base: int = 5
    ) -> Dict[str, List[Dict]]:
        """
        Busca respeitando hierarquia de documentos.

        Args:
            query: Texto da busca
            n_metodologia: Número de chunks da metodologia
            n_principais: Número de chunks dos principais
            n_base: Número de chunks da base

        Returns:
            Dict com resultados por categoria
        """
        results = {
            'metodologia': [],
            'principais_2': [],
            'base_40': []
        }

        # Busca em cada categoria separadamente
        if n_metodologia > 0:
            results['metodologia'] = self.search(
                query, n_metodologia, category_filter='metodologia', apply_weights=False
            )

        if n_principais > 0:
            results['principais_2'] = self.search(
                query, n_principais, category_filter='principais_2', apply_weights=False
            )

        if n_base > 0:
            results['base_40'] = self.search(
                query, n_base, category_filter='base_40', apply_weights=False
            )

        return results

    def add_single_document(self, pdf_data: Dict) -> bool:
        """
        Adiciona um único documento PDF à base vetorial.

        Args:
            pdf_data: Dicionário com dados do PDF

        Returns:
            bool: True se adicionado com sucesso
        """
        try:
            collection = self._get_or_create_collection()

            # Divide o texto em chunks
            chunks = self.text_splitter.split_text(pdf_data['full_text'])

            all_chunks = []
            all_metadatas = []
            all_ids = []

            for i, chunk in enumerate(chunks):
                chunk_id = f"{pdf_data['filename']}_chunk_{i}"

                metadata = {
                    'filename': pdf_data['filename'],
                    'category': pdf_data.get('category', 'metodologia'),
                    'chunk_index': i,
                    'total_chunks': len(chunks),
                    'author': pdf_data.get('metadata', {}).get('author', 'Desconhecido'),
                    'title': pdf_data.get('metadata', {}).get('title', pdf_data['filename']),
                    'weight': pdf_data.get('weight', self.CATEGORY_WEIGHTS.get(pdf_data.get('category', 'base_40'), 1.0))
                }

                all_chunks.append(chunk)
                all_metadatas.append(metadata)
                all_ids.append(chunk_id)

            # Cria embeddings
            embeddings = self._create_embeddings(all_chunks)

            # Adiciona à coleção
            collection.add(
                embeddings=embeddings,
                documents=all_chunks,
                metadatas=all_metadatas,
                ids=all_ids
            )

            print(f"Documento '{pdf_data['filename']}' adicionado com {len(chunks)} chunks")
            return True

        except Exception as e:
            print(f"Erro ao adicionar documento: {e}")
            return False

    def remove_document(self, filename: str) -> bool:
        """
        Remove todos os chunks de um documento específico.

        Args:
            filename: Nome do arquivo a remover

        Returns:
            bool: True se removido com sucesso
        """
        try:
            collection = self._get_or_create_collection()

            # Busca todos os IDs relacionados ao arquivo
            results = collection.get(
                where={"filename": filename}
            )

            if results['ids']:
                collection.delete(ids=results['ids'])
                print(f"Removidos {len(results['ids'])} chunks de '{filename}'")
                return True
            else:
                print(f"Documento '{filename}' nao encontrado na base")
                return False

        except Exception as e:
            print(f"Erro ao remover documento: {e}")
            return False

    def remove_category(self, category: str) -> bool:
        """
        Remove todos os documentos de uma categoria específica.

        Args:
            category: Categoria a remover ('metodologia', 'principais_2', 'base_40')

        Returns:
            bool: True se removido com sucesso
        """
        try:
            collection = self._get_or_create_collection()

            # Busca todos os IDs da categoria
            results = collection.get(
                where={"category": category}
            )

            if results['ids']:
                collection.delete(ids=results['ids'])
                print(f"Removidos {len(results['ids'])} chunks da categoria '{category}'")
                return True
            else:
                print(f"Nenhum documento encontrado na categoria '{category}'")
                return False

        except Exception as e:
            print(f"Erro ao remover categoria: {e}")
            return False

    def get_documents_in_category(self, category: str) -> List[str]:
        """
        Retorna lista de documentos em uma categoria.

        Args:
            category: Categoria a consultar

        Returns:
            Lista de nomes de arquivos únicos
        """
        try:
            collection = self._get_or_create_collection()
            results = collection.get(
                where={"category": category}
            )

            filenames = set()
            for metadata in results['metadatas']:
                filename = metadata.get('filename', '')
                if filename:
                    filenames.add(filename)

            return list(filenames)

        except Exception as e:
            print(f"Erro ao listar documentos: {e}")
            return []

    def get_context_for_prompt(
        self,
        query: str,
        n_results: int = 5,
        category_filter: Optional[str] = None,
        use_hierarchy: bool = False,
        n_metodologia: int = 2,
        n_principais: int = 3,
        n_base: int = 5
    ) -> str:
        """
        Obtém contexto formatado para incluir no prompt do Claude.

        Args:
            query: Texto da busca
            n_results: Número de resultados (usado se use_hierarchy=False)
            category_filter: Filtrar por categoria
            use_hierarchy: Se True, busca respeitando hierarquia de categorias
            n_metodologia: Chunks de metodologia (se use_hierarchy=True)
            n_principais: Chunks dos principais (se use_hierarchy=True)
            n_base: Chunks da base (se use_hierarchy=True)

        Returns:
            String formatada com o contexto
        """
        if use_hierarchy and not category_filter:
            # Busca hierárquica
            hierarchy_results = self.search_by_hierarchy(
                query, n_metodologia, n_principais, n_base
            )

            context_parts = ["CONTEXTO DOS ARTIGOS ACADÊMICOS (HIERARQUIA DE PRIORIDADE):\n"]

            # Metodologia primeiro (máxima prioridade)
            if hierarchy_results['metodologia']:
                context_parts.append("\n=== METODOLOGIA (PRIORIDADE MÁXIMA) ===")
                for i, result in enumerate(hierarchy_results['metodologia'], 1):
                    self._append_result_to_context(context_parts, result, f"M{i}")

            # Principais (alta prioridade)
            if hierarchy_results['principais_2']:
                context_parts.append("\n=== ARTIGOS PRINCIPAIS (ALTA PRIORIDADE) ===")
                for i, result in enumerate(hierarchy_results['principais_2'], 1):
                    self._append_result_to_context(context_parts, result, f"P{i}")

            # Base (contexto)
            if hierarchy_results['base_40']:
                context_parts.append("\n=== BASE DE ARTIGOS (CONTEXTO) ===")
                for i, result in enumerate(hierarchy_results['base_40'], 1):
                    self._append_result_to_context(context_parts, result, f"B{i}")

            return "\n".join(context_parts)

        else:
            # Busca tradicional com pesos
            results = self.search(query, n_results, category_filter)

            if not results:
                return "Nenhum contexto relevante encontrado."

            context_parts = ["CONTEXTO DOS ARTIGOS ACADÊMICOS:\n"]

            for i, result in enumerate(results, 1):
                self._append_result_to_context(context_parts, result, str(i))

            return "\n".join(context_parts)

    def _append_result_to_context(
        self,
        context_parts: List[str],
        result: Dict,
        index: str
    ):
        """Helper para adicionar resultado ao contexto."""
        metadata = result['metadata']
        document = result['document']
        category = metadata.get('category', 'Desconhecido')

        context_parts.append(f"\n--- TRECHO {index} [{category.upper()}] ---")
        context_parts.append(f"Fonte: {metadata.get('filename', 'Desconhecido')}")
        context_parts.append(f"Autor: {metadata.get('author', 'Desconhecido')}")
        context_parts.append(f"Categoria: {category}")
        context_parts.append(f"\nTexto:\n{document}")
        context_parts.append("---\n")

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
            filenames_by_category = {
                'metodologia': set(),
                'principais_2': set(),
                'base_40': set()
            }

            for metadata in results['metadatas']:
                cat = metadata.get('category', 'unknown')
                categories[cat] = categories.get(cat, 0) + 1
                if cat in filenames_by_category:
                    filenames_by_category[cat].add(metadata.get('filename', ''))

            return {
                'total_chunks': total_docs,
                'by_category': categories,
                'documents_by_category': {
                    k: len(v) for k, v in filenames_by_category.items()
                },
                'ready': total_docs > 0,
                'has_metodologia': categories.get('metodologia', 0) > 0
            }
        except Exception as e:
            return {
                'total_chunks': 0,
                'by_category': {},
                'documents_by_category': {},
                'ready': False,
                'has_metodologia': False,
                'error': str(e)
            }

    def reset(self):
        """Reseta a base vetorial (apaga tudo)."""
        try:
            self.client.delete_collection(name=self.collection_name)
            print("Base vetorial resetada com sucesso")
            return True
        except Exception as e:
            print(f"Erro ao resetar base vetorial: {e}")
            return False


if __name__ == "__main__":
    # Teste do vector store
    vector_store = VectorStore()

    # Obtém estatísticas
    stats = vector_store.get_stats()
    print(f"\nEstatisticas da base vetorial:")
    print(f"  Total de chunks: {stats['total_chunks']}")
    print(f"  Por categoria: {stats['by_category']}")
    print(f"  Pronto para uso: {stats['ready']}")

    # Teste de busca
    if stats['ready']:
        print("\nTeste de busca:")
        results = vector_store.search("analise tatica futebol", n_results=3)
        print(f"Encontrados {len(results)} resultados")
        for r in results:
            print(f"  - {r['metadata']['filename']}: {r['document'][:100]}...")
