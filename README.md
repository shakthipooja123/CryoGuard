#CryoGuard 
Predictive Medical Cold-Chain Intelligence
Predicting cold-chain risks before they become medical cargo failures.
CryoGuard is a Streamlit-based monitoring dashboard for temperature-sensitive medical cargo such as blood, organs, and vaccines.
It monitors simulated:
-  Temperature
-  Humidity
-  Shock / jolts
-  Battery
-  Transit time
The system uses multiple sensor readings, voting logic, stress tracking, and predictive analysis to determine whether the cargo is SAFE, WARNING, or CRITICAL.

##Features:
- Fail-safe multi-sensor voting mechanism
- Sensor outlier detection
- SAFE / WARNING / CRITICAL status
- Predictive confidence
- Estimated safe hours
- Route viability prediction
- Critical condition lock
- Event logs and trends
- PDF compliance report

##Tech Stack
- Python
- Streamlit
- Pandas
- ReportLab
- Wokwi

Run Locally
pip install -r requirements.txt
streamlit run app.py


##Project Structure
CryoGuard/
├── app.py
├── requirements.txt
└── logic/
    ├── thresholds.py
    ├── voting.py
    ├── state_engine.py
    ├── prediction.py
    └── report.py

##Note
CryoGuard is a hackathon prototype exploring predictive monitoring for medical cold-chain transportation.

Monitor. Predict. Protect.

