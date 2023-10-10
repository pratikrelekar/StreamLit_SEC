import streamlit as st
from sec_edgar_downloader import Downloader
from fuzzywuzzy import process
import os
from edgar import Edgar
from functools import lru_cache
import concurrent.futures
from minio import Minio
import shutil
from bs4 import BeautifulSoup

# MinIO configurations
MINIO_ENDPOINT = 's3.dsrs.illinois.edu'
MINIO_ACCESS_KEY = 'ENTER ACCESS KEY'
MINIO_SECRET_KEY = 'ENTER SECRET KEY'
MINIO_BUCKET_NAME = '10-k'
MINIO_SECURE = True

# Initialize Minio client
minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=MINIO_SECURE
)

# Initialize Edgar objects
edgar_obj = Edgar()
edgar_download = Downloader("DummyCompany", "dummy@email.com")

# Preprocess all companies for faster search
company_index = {}
all_companies = list(edgar_obj.all_companies_dict.keys())
for company in all_companies:
    prefix = company[:3].upper()
    if prefix in company_index:
        company_index[prefix].append(company)
    else:
        company_index[prefix] = [company]

@lru_cache(maxsize=1000)
def get_matching_companies(name):
    prefix = name[:3].upper()
    potential_matches = company_index.get(prefix, [])
    return [match[0] for match in process.extract(name, potential_matches, limit=5)]

def is_cik(input_str):
    """Check if the given input is a CIK (all numeric and typically 10 digits)."""
    return input_str.isdigit() and len(input_str) == 10

def move_and_merge(src, dest):
    if not os.path.exists(dest):
        os.rename(src, dest)
    else:
        for root, dirs, files in os.walk(src):
            for file in files:
                src_file_path = os.path.join(root, file)
                dest_file_path = os.path.join(dest, file)
                if os.path.exists(dest_file_path):
                    os.remove(dest_file_path)
                os.rename(src_file_path, dest_file_path)
            for d in dirs:
                shutil.rmtree(os.path.join(root, d))
        os.rmdir(src)

def clean_file_with_soup(filepath):
    with open(filepath, 'r', encoding='utf-8') as ff:
        content = ff.read()
        soup = BeautifulSoup(content, 'lxml')

        # Remove SEC specific metadata tags
        for tag in soup(["sec-document", "sec-header"]):
            tag.decompose()

        # Extract the main content of the 10-K document
        main_content = soup.find('text')
        if main_content:
            # Convert the HTML content to plain text
            plain_text = main_content.get_text(separator="\n")
            return plain_text

    # If the <text> tag isn't found, return the original content
    return content

def download_and_upload_10k_files(company_name, year):
    try:
        cik = edgar_obj.get_cik_by_company_name(company_name)

        edgar_download.get("10-K", cik, after=f"{year}-01-01", before=f"{year}-12-31")

        src_folder = os.path.join("sec-edgar-filings", cik)
        dest_folder = os.path.join("sec-edgar-filings", company_name.replace(" ", "_"))

        if not os.path.exists(src_folder):
            return f"No 10-K filings were downloaded for {company_name} in {year}.", None

        move_and_merge(src_folder, dest_folder)
        
        # Clean and upload files to Minio
        for root, _, files in os.walk(dest_folder):
            for file in files:
                file_path = os.path.join(root, file)
                cleaned_content = clean_file_with_soup(file_path)

                with open(file_path, 'w', encoding='utf-8') as cleaned_file:
                    cleaned_file.write(cleaned_content)

                minio_path = os.path.join("10-k", company_name.replace(" ", "_"), str(year), f"{cik}_{year}_{file}")
                minio_client.fput_object(MINIO_BUCKET_NAME, minio_path, file_path)
                
                # Generate a presigned URL for the uploaded file
                url = minio_client.presigned_get_object(MINIO_BUCKET_NAME, minio_path)

        return f"Downloaded and uploaded 10-K filings for {company_name} in {year}.", url
    except Exception as e:
        return f"Error: {str(e)}", None

# Streamlit App
st.title('SEC 10-K Filings Downloader & Uploader to MinIO')

input_data = st.text_input("Enter the company name or CIK:")

if input_data:
    if is_cik(input_data):
        # If input is CIK, then use it directly
        cik = input_data
        company_name = edgar_obj.get_company_name_by_cik(cik)
        if not company_name:
            st.write("Invalid CIK provided.")
    else:
        matches = get_matching_companies(input_data)
        if matches:
            matches_with_cik = [f"{match} ({edgar_obj.get_cik_by_company_name(match)})" for match in matches]
            selected = st.selectbox('Select the correct company:', matches_with_cik)
            company_name = selected.split(" (")[0]
            cik = edgar_obj.get_cik_by_company_name(company_name)
        else:
            st.write("No matching companies found.")

    selected_year = st.selectbox('Select the year:', list(range(1993, 2023)))

    if st.button('Download and Upload 10-K filings'):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(download_and_upload_10k_files, company_name, selected_year)
            result, url = future.result()
            st.write(result)

            # If there's a valid URL, display the download link
            if url:
                st.write(f"[Download the cleaned file here.]({url})")
