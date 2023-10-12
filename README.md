# StreamLit SEC 10-k Downloader
This Python script is designed to facilitate the download and upload of SEC 10-K filings for specific companies and years to a MinIO object storage service. It utilizes the SEC Edgar database and the MinIO client library to achieve this functionality.

Table of Contents

## 1. Installation
## 2. Usage
## 3. Dependencies
## 4. License

## 1. Installation

Clone this repository to your local machine using the following command:
```
git clone https://github.com/your-username/SEC-10K-Filings.git
```
Navigate to the project directory:
```
cd SEC-10K-Filings
```

## Install the required Python libraries using pip:
```
pip -r requirements.txt
```

## 2. Usage

To use this script, follow these steps:
### Run the script using Python:
```
python main.py
```

Enter the name of the company for which you want to download and upload 10-K filings.
Select the correct company from the suggestions provided.
Choose the year for which you want to download and upload 10-K filings.
Click the "Download and Upload 10-K filings" button.

The script will download the 10-K filings for the specified company and year from the SEC Edgar database, clean the files, and upload them to a MinIO object storage service. It will display the download link for the cleaned files if the process is successful.
