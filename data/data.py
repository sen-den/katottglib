import pandas as pd


def load_xlsx(file_name: str = "data/kodifikator.xlsx") -> pd.DataFrame:
    df = pd.read_excel(file_name, skiprows=2, skipfooter=3)
    return df


def load_data() -> pd.DataFrame:
    df = load_xlsx()
    df["id"] = df["Додатковий рівень"].fillna(
        df["Четвертий рівень"].fillna(
            df["Третій рівень"].fillna(
                df["Другий рівень"].fillna(df["Перший рівень"])
            )
        )
    )
    category_mapping = {
        "O": "Області та АРК",
        "K": "Міста зі спеціальним статусом (Київ та Севастополь)",
        "P": "Райони в областях та в АРК",
        "H": "Територіальні громади",
        "M": "Міста",
        "T": "Селища міського типу",
        "C": "Села",
        "X": "Селища",
        "B": "Райони в містах",
    }

    df["Назва категорії об’єкта"] = df["Категорія об’єкта"].map(
        category_mapping
    )
    return df
