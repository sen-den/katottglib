import pandas as pd
import os

DATA_FILE_PATH = "kodifikator_data.pkl"


def load_xlsx() -> pd.DataFrame:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, "kodifikator.xlsx")
    df = pd.read_excel(file_path, skiprows=2, skipfooter=3)
    return df


def load_data() -> pd.DataFrame:
    if os.path.exists(DATA_FILE_PATH):
        df = pd.read_pickle(DATA_FILE_PATH)
    else:
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
        df.to_pickle(DATA_FILE_PATH)  # Persist the DataFrame to disk

    return df
