from hashlib import md5
from langchain_community.graphs.graph_document import GraphDocument
from langchain_community.graphs.neo4j_graph import BASE_ENTITY_LABEL, Neo4jGraph, _get_rel_import_query
from langchain_core.embeddings import Embeddings

include_docs_query = (
    "MERGE (d:Document {id:$document.metadata.id}) "
    "SET d.text = $document.page_content "
    "SET d.embedding = $document.metadata.embedding "
    "WITH d "
)


def _get_node_import_query(baseEntityLabel: bool, include_source: bool) -> str:
    if baseEntityLabel:
        return (
            f"{include_docs_query if include_source else ''}"
            "UNWIND $data AS row "
            f"MERGE (source:`{BASE_ENTITY_LABEL}` {{id: row.id}}) "
            "SET source += row.properties "
            f"{'MERGE (d)-[:MENTIONS]->(source) ' if include_source else ''}"
            "WITH source, row "
            "CALL apoc.create.addLabels( source, [row.type] ) YIELD node "
            "RETURN distinct 'done' AS result"
        )
    else:
        return (
            f"{include_docs_query if include_source else ''}"
            "UNWIND $data AS row "
            "CALL apoc.merge.node([row.type], {id: row.id}, "
            "row.properties, {}) YIELD node "
            f"{'MERGE (d)-[:MENTIONS]->(node) ' if include_source else ''}"
            "RETURN distinct 'done' AS result"
        )


class ModifiedNeo4JGraph(Neo4jGraph):
    def add_graph_documents_with_embeddings(self, graph_documents: list[GraphDocument], embedding: Embeddings, include_source: bool = False,
                            baseEntityLabel: bool = False) -> None:
        """
        This method constructs nodes and relationships in the graph based on the
        provided GraphDocument objects.

        Parameters:
        - graph_documents (List[GraphDocument]): A list of GraphDocument objects
        that contain the nodes and relationships to be added to the graph. Each
        GraphDocument should encapsulate the structure of part of the graph,
        including nodes, relationships, and the source document information.
        - embedding (Embeddings): An embedding function to embed the chunked documents.
        - include_source (bool, optional): If True, stores the source document
        and links it to nodes in the graph using the MENTIONS relationship.
        This is useful for tracing back the origin of data. Merges source
        documents based on the `id` property from the source document metadata
        if available; otherwise it calculates the MD5 hash of `page_content`
        for merging process. Defaults to False.
        - baseEntityLabel (bool, optional): If True, each newly created node
        gets a secondary __Entity__ label, which is indexed and improves import
        speed and performance. Defaults to False.
        """

        if baseEntityLabel:  # Check if constraint already exists
            constraint_exists = any(
                [
                    el["labelsOrTypes"] == [BASE_ENTITY_LABEL]
                    and el["properties"] == ["id"]
                    for el in self.structured_schema.get("metadata", {}).get(
                    "constraint"
                )
                ]
            )
            if not constraint_exists:
                # Create constraint
                self.query(
                    f"CREATE CONSTRAINT IF NOT EXISTS FOR (b:{BASE_ENTITY_LABEL}) "
                    "REQUIRE b.id IS UNIQUE;"
                )
                self.refresh_schema()  # Refresh constraint information

        node_import_query = _get_node_import_query(baseEntityLabel, include_source)
        rel_import_query = _get_rel_import_query(baseEntityLabel)
        for document in graph_documents:
            if not document.source.metadata.get("id"):
                document.source.metadata["id"] = md5(
                    document.source.page_content.encode("utf-8")
                ).hexdigest()
                document.source.metadata["embedding"] = embedding.embed_query(text=document.source.page_content)

            # Import nodes
            self.query(
                node_import_query,
                {
                    "data": [el.__dict__ for el in document.nodes],
                    "document": document.source.__dict__,
                },
            )
            # Import relationships
            self.query(
                rel_import_query,
                {
                    "data": [
                        {
                            "source": el.source.id,
                            "source_label": el.source.type,
                            "target": el.target.id,
                            "target_label": el.target.type,
                            "type": el.type.replace(" ", "_").upper(),
                            "properties": el.properties,
                        }
                        for el in document.relationships
                    ]
                },
            )
