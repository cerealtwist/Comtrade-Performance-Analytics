import pandas as pd

raw = pd.read_csv("data/raw/comtrade_hs85_all_20260508.csv", dtype={"period": str})

print("=== netWgt distribution ===")
print(raw["netWgt"].describe())
print(f"Zero count: {(raw['netWgt'] == 0).sum()}")
print(f"Null count: {raw['netWgt'].isnull().sum()}")
print(
    f"Non-zero non-null count: {((raw['netWgt'] != 0) & (raw['netWgt'].notnull())).sum()}"
)

print()
print("=== primaryValue distribution ===")
print(raw["primaryValue"].describe())
print(f"Null count: {raw['primaryValue'].isnull().sum()}")
print(f"Zero count: {(raw['primaryValue'] == 0).sum()}")

print()
print("=== Sample of non-zero weight rows ===")
nonzero = raw.loc[(raw["netWgt"] > 0) & (raw["netWgt"].notnull())]
print(f"Count: {len(nonzero)}")
print(
    nonzero[
        [
            "partnerISO",
            "partnerDesc",
            "refYear",
            "refMonth",
            "flowCode",
            "netWgt",
            "primaryValue",
        ]
    ]
    .head(10)
    .to_string()
)
