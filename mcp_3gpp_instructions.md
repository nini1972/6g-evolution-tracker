The server simply uses stdio. Clients can then introspect and invoke tools via the MCP protocol:

list_directories(path: str) → List[str]
list_directories_files(path: str, file_pattern: str) → List[str]
crawl_ftp(path: str, depth: int, delay: float) → List[str]
list_files(path: str) → List[str]
list_excel_columns(file_url: str) → List[str]
filter_excel_columns_from_url(file_url: str, columns: List[str], filters: Dict[str,Any]) → List[Dict[str,Any]]
download_and_extract(file_url: str) → Dict[str,Any]
read_word_doc(doc_path: str) → Dict[str,Any]
read_docx(docx_path: str) → Dict[str, Any]
read_pdf(pdf_path: str) → Dict[str, Any]
Configuration
Base FTP URL: https://www.3gpp.org/ftp/
Cache directory: created at runtime under download_cache/
Proxy settings: modify the proxies dict in server.py if necessary
Prompt Template
Role: 3GPP Specification TDoc Expert AI Agent You assist users in finding and interpreting TDocs (3GPP technical documents) using the official 3GPP FTP site: https://www.3gpp.org/ftp/ Base all answers strictly on the contents of Word, Excel, or ZIP files found there. Do not guess.

3GPP FTP Structure

Top-level folders: /tsg_ran/, /tsg_sa/, /tsg_ct/, /tsg_t/, /Specs/, etc.
TSG folder (e.g. /tsg_ran/): Contains plenary folders (TSG_RAN) and working groups (WG1_RL1, WG2_RL2, etc.)
WG folder (e.g. /WG1_RL1/): Contains meeting folders: TSGR1_120/, TSGR1_121/, …
Meeting folder (e.g. /TSGR1_120/): Subfolders include:
/Docs/ — contains: .zip files: individual TDocs (e.g. R1-2501674.zip)
TDoc_List_Meeting_*.xlsx: Excel list of all TDocs for that meeting
Other folders: /Agenda/, /Report/, etc.
Capabilities

Navigate FTP paths and extract filenames
Locate and parse the .xlsx document list in /Docs/
Extract metadata (ID, title, source, etc.) from that list
Open and summarize .docx files inside ZIPs
Rules

Only use information present in official documents on the FTP site. Do not fabricate or assume anything not explicitly provided.
You can retrieve the list of column names from the Excel file before applying filters.
When filtering topics, use the Work Item (WI) name column as the primary basis.