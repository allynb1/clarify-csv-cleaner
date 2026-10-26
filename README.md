# Clarify — Simple CSV Cleaner

Clarify is a lightweight, locally run Streamlit application for uploading, viewing, cleaning, visualizing, and exporting CSV datasets. It provides a simple workflow for basic data preparation and exploration.

## Requirements

- Python 3.10 or newer
- Windows, macOS, or Linux

## Installation and Setup

### Windows

Open PowerShell in the project folder and run:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

If PowerShell blocks virtual environment activation, you can run the app without activating it:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

### macOS and Linux

Open a terminal in the project folder and run:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Features

- Upload CSV files and preview rows and detected column types.
- Review missing values and duplicate-row counts.
- Trim whitespace from text values.
- Remove duplicate rows.
- Fill missing values using supported strategies.
- Drop rows containing missing values.
- Rename columns.
- Undo cleaning actions and restore the original uploaded data.
- Create bar charts, histograms, scatter plots, line charts, and box plots.
- Export the cleaned dataset as a CSV file.
- Download a log of cleaning operations.

## Sample Data

The `sample_csv/` folder contains example CSV files for exploring Clarify's features and testing the data-cleaning workflow.

Use these files to try the application before uploading your own datasets.

## Limitations

- **In-memory processing:** CSV files are loaded into memory using Pandas. Large datasets may require substantial RAM and can cause slowdowns or failures on computers with limited resources.
- **File size:** There is no guaranteed maximum supported file size. Performance depends on the dataset's size, number of columns, data types, and available system memory.
- **Local application:** Clarify runs locally and is intended for individual use. This version does not include user authentication, cloud storage, or a shared database.
- **CSV only:** The application is designed for CSV files and does not currently provide direct import support for Excel workbooks or database connections.
- **Basic data preparation:** Cleaning operations are intended for common data-quality tasks. The app is not a replacement for a full-scale ETL pipeline or specialized data-cleaning platform.
- **Visualization constraints:** Charts may become slow or impractical when working with very large datasets.

## Technical Notes

- Built with Python, Streamlit, Pandas, and Plotly.
- The original dataset is kept separately from the working copy during the current session.
- Data processing occurs locally within the running application; this code does not intentionally upload datasets to a hosted service.
- Uploaded data and cleaning history are managed within the application session. This version does not provide persistent project storage.

## Future Improvements

Potential enhancements include more efficient processing of large CSV files, additional data-quality checks, and expanded data exploration features.
