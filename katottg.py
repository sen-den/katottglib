from difflib import SequenceMatcher, get_close_matches

import pandas as pd

from data import load_data
from data.entity import KatottgEntity


def find_by_name(
    name: str, parent: str = None, category: str = None, limit: int = 5
) -> list[KatottgEntity]:
    """
    Finl CATOTTG entity
    :param name: name to search
    :param parent: Filter by higher level entity
    :param category: filter by category ('O', 'K', 'P', 'H', 'M', 'T', 'C', 'X', 'B')
    :param limit: limit return
    :return: KatottgEntity list
    """
    df = load_data()
    return _search_matches(df, name, parent, category, limit)


def _search_matches(
    df, query, parent: str = None, category: str = None, limit: int = 5
):
    # Apply filters for parent and category
    if parent is not None:
        parent_filter = df.apply(lambda row: parent in row.values[:5], axis=1)
        df = df[parent_filter]
    if category is not None:
        category_filter = (df["Категорія об’єкта"] == category) | (
            df["Назва категорії об’єкта"] == category
        )
        df = df[category_filter]

    # Compute similarity scores for the search query against the 'Назва об’єкта' column
    similarity_scores = df["Назва об’єкта"].apply(
        lambda x: SequenceMatcher(None, query, x).ratio()
    )

    # Add similarity scores as a temporary column in the DataFrame
    df["Similarity"] = similarity_scores
    df["Similarity"].fillna(-1)

    category_order = ["O", "K", "P", "H", "M", "T", "C", "X", "B"][::-1]
    df["Порядок категорій"] = df["Категорія об’єкта"].map(
        {v: k for k, v in enumerate(category_order)}
    )

    # Sort the DataFrame by 'Категорія об’єкта' column in the desired order
    df_sorted = (
        df[df["Категорія об’єкта"].isin(category_order)]
        .sort_values(
            by=["Similarity", "Категорія об’єкта", "Назва об’єкта"],
            ascending=False,
        )
        .head(limit)
    )

    return df_sorted


def _serialize_entities(df, search_results):
    serialized_results = []

    for _, row in search_results.iterrows():
        entity = KatottgEntity(
            row["id"], row["Назва об’єкта"], row["Назва категорії об’єкта"]
        )
        parents = [
            parent_id
            for parent_id in row.iloc[:5]
            if isinstance(parent_id, str)
        ][:-1]

        for parent_id in parents[::-1]:
            parent_row = df[df["id"] == parent_id]
            parent_entity = KatottgEntity(
                parent_row["id"].values[0],
                parent_row["Назва об’єкта"].values[0],
                parent_row["Назва категорії об’єкта"].values[0],
            )
            entity.add_parent(parent_entity)

        serialized_results.append(entity)

    return serialized_results
