# getting price data from: 
# https://pancanal.com/maritime-services/tarifas-maritimas/

# FUNCTIONS TO CALC PRICES ARE AT END: 
#   reg_container(totalteu, full, empty)
#   super_container(totalteu, full, empty)
#   npnmx_container(totalteu, full, empty)
#   reg_drybulk(dwt)
#   super_drybulk(dwt)
#   npnmx_drybulk(dwt)
#   reg_lng(volume_m3)
#   super_lng(volume_m3)
#   npnmx_lng(volume_m3)
#   reg_lpg(volume_m3)
#   super_lpg(volume_m3)
#   npnmx_lpg(volume_m3)
#   reg_vehicle(cp)
#   super_vehicle(cp)
#   npnmx_vehicle(cp)
#   reg_tanker(cp)
#   super_tanker(cp)
#   npnmx_tanker(cp)


import pandas as pd 
import numpy as np 

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


#------CALCULATING VESSEL PRICES
## CONTAINER EQUATIONS 
def reg_container(totalteu,full,empty): 
    transit_charge = regular3 
    teucap_charge = (reg_teu_capacity*totalteu)
    teufull_charge = (reg_teu_loaded*full)
    teuempty_charge = (reg_teu_empty*empty)
    return transit_charge + teucap_charge + teufull_charge + teuempty_charge
def super_container(totalteu,full,empty): 
    transit_charge = super1
    teucap_charge = (super_teu_capacity*totalteu)
    teufull_charge = (super_teu_loaded*full)
    teuempty_charge = (super_teu_empty*empty)
    return transit_charge + teucap_charge + teufull_charge + teuempty_charge
def npnmx_container(totalteu,full,empty): 
    if totalteu < 10000: 
        transit_charge = npnmx1
    else: 
        transit_charge = npnmx2
    teucap_charge = (npnmx_teu_capacity*totalteu)
    teufull_charge = (npnmx_teu_loaded*full)
    teuempty_charge = (npnmx_teu_empty*empty)
    return transit_charge + teucap_charge + teufull_charge + teuempty_charge

## DRY BULK EQUATIONS 
def reg_drybulk(dwt):
    transit_charge = regular3
    tpm_charge = reg_drybulk_tpm * dwt
    return transit_charge + tpm_charge
def super_drybulk(dwt):
    transit_charge = super1
    tpm_charge = super_drybulk_tpm * dwt
    return transit_charge + tpm_charge
def npnmx_drybulk(dwt):
    transit_charge = npnmx2
    tpm_charge = npmnx_drybulk_tpm * dwt
    return transit_charge + tpm_charge

## LNG
def reg_lng(volume_m3):
    transit_charge = regular3
    m3_charge = reg_lng_m3 * volume_m3
    return transit_charge + m3_charge
def super_lng(volume_m3):
    transit_charge = super1
    m3_charge = super_lng_m3 * volume_m3
    return transit_charge + m3_charge
def npnmx_lng(volume_m3):
    transit_charge = npnmx2
    m3_charge = npnmx_lng_m3 * volume_m3
    return transit_charge + m3_charge

# LPG 
def reg_lpg(volume_m3):
    return regular3 + reg_lpg_m3 * volume_m3
def super_lpg(volume_m3):
    return super1 + super_lpg_m3 * volume_m3
def npnmx_lpg(volume_m3):
    return npnmx2 + npnmx_lpg_m3 * volume_m3

# VEHICLES 
def reg_vehicle(cp):
    transit_charge = regular3
    cp_charge = reg_vehicle_cp * cp
    return transit_charge + cp_charge
def super_vehicle(cp):
    transit_charge = super1
    cp_charge = super_vehicle_cp * cp
    return transit_charge + cp_charge
def npnmx_vehicle(cp):
    transit_charge = npnmx2
    cp_charge = npnmx_vehicle_cp * cp
    return transit_charge + cp_charge

# TANKERS 
def reg_tanker(cp):
    return regular3 + reg_tanker_cp * cp
def super_tanker(cp):
    return super1 + super_tanker_cp * cp
def npnmx_tanker(cp):
    return npnmx2 + npnmx_tanker_cp * cp



