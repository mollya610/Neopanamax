# -*- coding: utf-8 -*-
"""
Created on Fri Jan 30 14:25:31 2026

@author: malcor
"""
import requests 
import pandas as pd
import matplotlib.pyplot as plt

# lake gatun data 
url = "https://evtms-rpts.pancanal.com/eng/h2o/Download_Gatun_Lake_Water_Level_History.csv"
response = requests.get(url, timeout=30)
with open('lakegatun.csv', 'wb') as file:
    file.write(response.content)
gatun = pd.read_csv('lakegatun.csv').rename(columns={'DATE_LOG':'date','GATUN_LAKE_LEVEL(FEET)':'lake_level'})
gatun['date'] = pd.to_datetime(gatun['date'])
gatun = gatun[gatun['lake_level']>0]
# NO DATA IN 2002

# el nino data 
url = "https://psl.noaa.gov/data/correlation/oni.csv"
response = requests.get(url, timeout=30)
with open('elnino.csv', 'wb') as file:
    file.write(response.content)
nino = pd.read_csv('elnino.csv',parse_dates=['Date']).rename(columns={'Date':'date','  ONI from CPC  missing value -99.9 https://psl.noaa.gov/data/timeseries/month/':'oni'})
nino = nino[abs(nino['oni'])<=4]

 ## PLOTTING EL NINO AND WATER LEVEL
yr1 = 2018
yr2 = 2025
fig, ax1 = plt.subplots(figsize=(9, 4))
gatunyrs = gatun[(gatun['date'].dt.year >= yr1) &(gatun['date'].dt.year <= yr2)]
ax1.plot(gatunyrs['date'],gatunyrs['lake_level'],label='Lake Gatun Level')
ax1.set_ylabel('Lake Level (ft)')
# this is the level wear panamax vessels have to reduce draft
ax1.axhline(y=78.8,color='red',label='Panamax')
# and where neopanamax has to reduce 
ax1.axhline(y=85,color='red',label='Neopanamax',linestyle='--')
ax1.set_ylim(78, 92)
ax1.set_title(f'Lake Gatun Water Levels and El Nino, {yr1}–{yr2}')
# other axis 
ax2 = ax1.twinx()
ninoyrs = nino[(nino['date'].dt.year >= yr1) &(nino['date'].dt.year <= yr2)]
ax2.plot(ninoyrs['date'],ninoyrs['oni']*-1,label='ONI',color='orange')
ax2.set_ylabel('ONI')
# ---- Optional: horizontal zero line for ENSO ----
ax2.axhline(0, linewidth=1, alpha=0.4)
# ---- Legend (combine both axes) ----
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
plt.show()



