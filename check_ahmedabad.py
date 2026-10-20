from src import analysis

raw = analysis.load_raw(analysis.find_data_file())
a = raw[raw["City"] == "Ahmedabad"]
print(a.groupby(a["Date"].dt.year)["AQI"].agg(["count", "mean", "max"]).round(1))
