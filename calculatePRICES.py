# getting price data from: 
# https://pancanal.com/maritime-services/tarifas-maritimas/

import pandas as pd 
import numpy as np 

#######################################################
#######################################################
## PART ONE: defining costs based on vessel size and type (maybe would be easier 
#######################################################
#---- TRANSIT CHARGES --------- #  
# REGULAR VESSEL 
# Other 
regular1 = 15000
# Passengers, General Cargo and Refrigerated with CP/SUAB < 10,000
regular2 = 25000
# Container Ship; Vehicle Carrier/RoRo; Passenger Ship; Tanker; Chemical Tanker; LPG; LNG; Dry Bulk, Category “Other” with CP/SUAB ≥ 7,500; General Cargo and Refrigerated with CP/SUAB ≥ 10,000;
regular3 = 60000
###
# SUPER VESSEL
#Super Container Ship; Passenger Ship; Car Carrier/RoRo Ship; Tanker; LPG; LNG; Chemical Carrier; Dry Bulk Carrier; Refrigerated Carrier; General Cargo and “Other”
super1 = 100000
###
# NEOPANAMAX VESSEL
# Container Ship with TTA <10,000 TEU
npnmx1 = 200000
# Container ship with TTA ≥ 10,000 TEU
# Tanker, Chemical tanker, LPG, LNG; Dry bulk; Passenger; Refrigerated, General cargo and “Other”
npnmx2 = 300000 

#---- CP SUAB CHARGES --------- #  
# TANKERS 
reg_tanker_cp = 6
super_tanker_cp = 5.25
npnmx_tanker_cp = 3.25 
# CHEMICAL 
reg_chemical_cp = 5.5
super_chemical_cp = 5.25
npnmx_chemical_cp = 3.25
# VEHICLE 
reg_vehicle_cp = 6.0
super_vehicle_cp = 4.75
npnmx_vehicle_cp = 2.75
# GEN CARGO 
reg_under10k_cargo_cp = 3.5
reg_over10k_cargo_cp = 3.25
super_cargo_cp = 3
npnmx_cargo_cp = 1.5
# REFRIGERATED
reg_under10k_fridge_cp = 3.5
reg_over10k_fridge_cp = 3.25
super_fridge_cp = 3
npnmx_fridge_cp = 1.5
# OTHER 
reg_under7500_other_cp = 3
reg_over7500_other_cp = 3.25
super_other_cp = 3
npnmx_other_cp = 1.5 

#---- TPM CHARGES --------- #
# DRY BULK (measure by deadweight tonnage)
reg_drybulk_tpm = 1.65
super_drybulk_tpm = 1.5
npmnx_drybulk_tpm = 0.8

#---- TEU CHARGES --------- # 
# CONTAINERS 
reg_teu_capacity = 32
reg_teu_loaded   = 38
reg_teu_empty    = 7

super_teu_capacity = 35
super_teu_loaded   = 40
super_teu_empty    = 8

npnmx_teu_capacity = 42
npnmx_teu_loaded   = 48
npnmx_teu_empty    = 9

#---- M3 CHARGES --------- # 
# LPG 
reg_lpg_m3 = 3.5
super_lpg_m3 = 3.85
npnmx_lpg_m3 = 2.75
# LNG 
reg_lng_m3 = 3.5
super_lng_m3 = 3.85
npnmx_lng_m3 = 2.05


##############################################################
##############################################################
## PART TWO: MAKE IT INTO DICTIONARY SO ITS EASIER TO USE 
##################################################################
# -- DICTIONARIES 
transit_charge_reg = {
    ("regular","other"): regular1,
    ("regular","gencargo"): regular2,
    ("regular","fridge"): regular2,
    ("regular","container"): regular3,
    ("regular","vehicle"): regular3,
    ("regular","tanker"): regular3,
    ("regular","chemical"): regular3,
    ("regular","lng"): regular3,
    ("regular","lpg"): regular3,
    ("regular","drybulk"): regular3}
transit_charge= {
    "super": super1,
    "npnmx": npnmx2}
rates = {
    # containers (tuple = capacity, loaded, empty)
    ("regular","container"): ("teu", (reg_teu_capacity, reg_teu_loaded, reg_teu_empty)),
    ("super","container"):   ("teu", (super_teu_capacity, super_teu_loaded, super_teu_empty)),
    ("npnmx","container"):   ("teu", (npnmx_teu_capacity, npnmx_teu_loaded, npnmx_teu_empty)),
    # dry bulk (TPM)
    ("regular","drybulk"): ("dwt", reg_drybulk_tpm),
    ("super","drybulk"):   ("dwt", super_drybulk_tpm),
    ("npnmx","drybulk"):   ("dwt", npmnx_drybulk_tpm),
    # CP vessels
    ("regular","tanker"):   ("cp", reg_tanker_cp),
    ("super","tanker"):     ("cp", super_tanker_cp),
    ("npnmx","tanker"):     ("cp", npnmx_tanker_cp),
    ("regular","vehicle"):  ("cp", reg_vehicle_cp),
    ("super","vehicle"):    ("cp", super_vehicle_cp),
    ("npnmx","vehicle"):    ("cp", npnmx_vehicle_cp),
    ("regular","chemical"): ("cp", reg_chemical_cp),
    ("super","chemical"):   ("cp", super_chemical_cp),
    ("npnmx","chemical"):   ("cp", npnmx_chemical_cp),
    # cubic meters
    ("regular","lng"): ("m3", reg_lng_m3),
    ("super","lng"):   ("m3", super_lng_m3),
    ("npnmx","lng"):   ("m3", npnmx_lng_m3),
    ("regular","lpg"): ("m3", reg_lpg_m3),
    ("super","lpg"):   ("m3", super_lpg_m3),
    ("npnmx","lpg"):   ("m3", npnmx_lpg_m3),
}

#######################################################################
#######################################################################
#### PART THREE: MAKE FUNCTIONS FOR CALCULATING VESSEL REVENUE 
#############################################################################
def freshwater_surcharge(lake_level):
    exponent = 0.6*(lake_level-79)
    lower = 1 + np.exp(exponent)
    return 0.1/lower

# FUNCTION FOR ANY VESSEL
def vessel_cost(size,content,volume,lake_level):
    # size = "regular" or "super" or "npnmx" 
    # content = "container" or "drybulk" "chemical" or "LPG" "vehicle" "fridge" "tanker" "gencargo" "LNG" or "other" 
    # volume = value that means either totalteu (make a geuss about full or empty) or dwt or m3 or cp 
    percent_full = 0.8 # (geuss average percent full for CONTAINER SHIPS ONLY)
    if size=='regular':
        base = transit_charge_reg[(size,content)]
    else: 
        base = transit_charge[size]
    measure, rate = rates[(size, content)]
    # ---- variable charge ----
    if content == "container":
        cap, full_rate, empty_rate = rate
        full = volume*percent_full
        empty = volume - full 
        variable = cap*volume + full_rate*full + empty_rate*empty
    else:
        variable = rate * volume
    toll = base + variable
    surcharge = toll*freshwater_surcharge(lake_level)
    return toll + surcharge


#############################################################################
#############################################################################
### PART FOUR: READ IN LAKE LEVEL DATA AND TRANSIT DATA 
#############################################################################
# water levels and transits 
os.chdir(r'C:\\Users\\malcor\OneDrive - University of North Carolina at Chapel Hill\Research\Data')
transits = pd.read_csv('canaltransit_DATA.csv',parse_dates=['date'])
# lake gatun data 
url = "https://evtms-rpts.pancanal.com/eng/h2o/Download_Gatun_Lake_Water_Level_History.csv"
response = requests.get(url, timeout=30)
with open('lakegatun.csv', 'wb') as file:
    file.write(response.content)
gatun = pd.read_csv('lakegatun.csv').rename(columns={'DATE_LOG':'date','GATUN_LAKE_LEVEL(FEET)':'lake_level'})
gatun['date'] = pd.to_datetime(gatun['date'])
gatun = gatun[gatun['lake_level']>0]
gatun['month'] = gatun['date'].dt.month
gatun['year'] = gatun['date'].dt.year
gatun_month = gatun.groupby(['month','year'])[['lake_level']].mean().reset_index()

canaldata = transits.merge(gatun_month,how='inner',on=['month','year'])

################################################################################
################################################################################
### PART FIVE: CALCULATE REVENUE WITH LOTS OF ASSUMPTIONS 
################################################################################
# To Test Function: Half container, half dry bulk 
container_pct = 0.35
drybulk_pct = 0.25 
chemical_pct = 0.2 
lpg_pct = 0.2 

# unit for tanker: pc ums 
# Calculate, making volume assumptions as well 
canaldata['regular_rev'] = (
    canaldata['regular_count']*container_pct*vessel_cost("regular","container",2000,canaldata['lake_level'])
    + canaldata['regular_count']*drybulk_pct*vessel_cost("regular","drybulk",50000,canaldata['lake_level'])
    + canaldata['regular_count']*chemical_pct*vessel_cost("regular","chemical",20000,canaldata['lake_level'])
    + canaldata['regular_count']*lpg_pct*vessel_cost("regular","lng",75000,canaldata['lake_level']))

canaldata['super_rev'] = (
    canaldata['super_count']*container_pct*vessel_cost("super","container",4000,canaldata['lake_level'])
    + canaldata['super_count']*drybulk_pct*vessel_cost("super","drybulk",75000,canaldata['lake_level'])
    + canaldata['super_count']*chemical_pct*vessel_cost("super","chemical",30000,canaldata['lake_level'])
    + canaldata['super_count']*lpg_pct*vessel_cost("super","lng",150000,canaldata['lake_level']))

canaldata['npnmx_rev'] = (
    canaldata['neopnmx_count']*container_pct*vessel_cost("npnmx","container",15000,canaldata['lake_level'])
    + canaldata['neopnmx_count']*drybulk_pct*vessel_cost("npnmx","drybulk",100000,canaldata['lake_level'])
    + canaldata['neopnmx_count']*chemical_pct*vessel_cost("npnmx","chemical",40000,canaldata['lake_level'])
    + canaldata['neopnmx_count']*lpg_pct*vessel_cost("npnmx","lng",200000,canaldata['lake_level']))

canaldata['revenue'] = canaldata[['regular_rev','super_rev','npnmx_rev']].sum(axis=1)
canaldata = canaldata[canaldata['revenue']>0]

cols = ['under80beam_count','over80beam_count','regular_count','super_count','neopnmx_count']
canaldata[cols] = canaldata[cols].replace(0, np.nan)







