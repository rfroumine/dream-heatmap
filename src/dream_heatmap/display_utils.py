"""Display utilities for prettifying column/variable names."""

_ACRONYMS = {
    "id", "dna", "rna", "umap", "pca", "tsne", "qc", "umi",
    "snp", "hla", "mhc", "go", "kegg",
}


def prettify_name(name: str) -> str:
    """Convert snake_case names to Title Case with smart acronyms.

    Examples::

        prettify_name("cell_type")  # -> "Cell Type"
        prettify_name("cell_id")    # -> "Cell ID"
        prettify_name("umap_1")     # -> "UMAP 1"
    """
    words = name.replace("_", " ").split()
    return " ".join(
        w.upper() if w.lower() in _ACRONYMS else w.capitalize()
        for w in words
    )
