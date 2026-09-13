# CryoGuard

## Predictive Medical Cold-Chain Intelligence
Predicting cold-chain risks before they become medical cargo failures.
CryoGuard is a monitoring dashboard designed for temperature-sensitive medical cargo such as blood, organs, and vaccines during transportation.

## Features

* Fail-safe multi-sensor voting
* Temperature monitoring
* Humidity monitoring
* Shock and jolt detection
* Battery monitoring
* SAFE / WARNING / CRITICAL status
* Predictive risk analysis
* Estimated remaining safe hours
* Route viability prediction
* Critical condition lock
* Event logs and trends
* PDF compliance report

## Tech Stack
* Python
* Streamlit
* Pandas
* ReportLab
* Wokwi

## Project Structure
CryoGuard/
* app.py
* requirements.txt
* logic/
  * thresholds.py
  * voting.py
  * state_engine.py
  * prediction.py
  * report.py

## Run Locally
pip install -r requirements.txt
streamlit run app.py

## How It Works
Sensor Data - Sensor Validation - Trusted Readings - Safety Evaluation - Risk Prediction - Route Viability - Dashboard & Reports

CryoGuard is a hackathon prototype exploring predictive monitoring for medical cold-chain transportation.
