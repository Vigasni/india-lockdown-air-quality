# Did India's 2020 lockdown clean the air, or just pause the pollution?
Live app: https://india-lockdown-air-quality.streamlit.app/ (upload `city_day.csv` from Kaggle to use it)

An interactive Python dashboard (Streamlit + Plotly) plus static figures (Matplotlib/Seaborn)
comparing air quality in Indian cities during the 2020 lockdown (25 Mar - 31 May)
with the **same calendar dates in 2017-2019**, then checking how much of the
improvement was still there in June.

## Run it
1. Download `city_day.csv` from Kaggle ("Air Quality Data in India (2015-2020)") into `data/`.
2. Install and run:
```
pip install -r requirements.txt
python run_pipeline.py          # cleaning, analysis, static figures -> figures/, outputs/
streamlit run app/app.py        # interactive dashboard
```
(The dashboard also lets you upload the CSV if it isn't in `data/`.)

## Method
- Negative readings -> missing. Gaps of up to 3 days are interpolated; longer gaps stay empty.
- Per city: mean over the lockdown window vs mean over the same dates in 2017-2019.
- A city is included only if >= 60% of window days have data in 2020 and in >= 2 baseline years.
- "Pause or fix?": % change vs baseline in lockdown and in June; the share retained gives the verdict.

## Project layout
```
data/          city_coords.csv (+ your city_day.csv, not committed)
src/           common.py (settings) · analysis.py · charts.py (Plotly) · static_figures.py
app/app.py     Streamlit dashboard (5 tabs)
run_pipeline.py
```
Change dates, thresholds and colours in `src/common.py`.

## Limitations
Weather also affects air quality, so results are *consistent with* a lockdown effect, not proof.
Monitoring stations differ across years and the data ends in July 2020.

## Findings
1. During the lockdown (25 Mar - 31 May 2020), 14 of 15 cities had lower AQI than on the same dates in 2017-2019, with a median drop of 33%.
2. The largest improvements were in northern cities: Delhi -52%, Lucknow -51%, Gurugram -49%.
3. Particulates fell more than NO2 (PM2.5 median -43%, NO2 median -30%).
4. In June, most cities were still cleaner than normal (7 of 13 kept most of the gain), a partial rebound. Chennai was the exception.
5. Industrial towns such as Jorapokhar saw little or no improvement.

**Data notes:** Ahmedabad was excluded because its AQI readings reached about 2,000, far above the 500-point scale, in every year. 11 cities were dropped for too little data. Weather also affects air quality, so these results are consistent with a lockdown effect, not proof of it.