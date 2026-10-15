#!/usr/bin/env python3
"""
SCHEMESATHI AI - Your Guide to Government Schemes
==================================================
A production-minded, full-stack web application designed to help Indian citizens
discover government schemes, check eligibility, explore required documents,
and access official government portals.

All core application logic, API endpoints, dataset, eligibility engine,
AI assistant, multilingual dictionary, and embedded frontend UI reside in this file.
"""

import os
import sys
import json
import re
import time
import logging
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse

from flask import Flask, request, jsonify, render_template_string, make_response
try:
    from flask_cors import CORS
    HAS_CORS = True
except ImportError:
    HAS_CORS = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# -----------------------------------------------------------------------------
# Configuration & Constants
# -----------------------------------------------------------------------------
APP_VERSION = "1.0.0"
APP_NAME = "SchemeSathi AI"
APP_TAGLINE = "Your Guide to Government Schemes"
MAX_CONTENT_LENGTH = 1 * 1024 * 1024  # 1MB limit for request bodies

# Environment settings
PORT = int(os.environ.get("PORT", 5000))
HOST = os.environ.get("HOST", "0.0.0.0")
DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"
SECRET_KEY = os.environ.get("SECRET_KEY", "schemesathi-default-local-secret-key-change-in-prod")

# AI API configuration (Supports Google Gemini or OpenAI-compatible endpoints)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
AI_API_KEY = os.environ.get("AI_API_KEY", "").strip() or GEMINI_API_KEY or OPENAI_API_KEY
AI_PROVIDER = os.environ.get("AI_PROVIDER", "auto").lower()  # "gemini", "openai", "auto"
AI_MODEL = os.environ.get("AI_MODEL", "gemini-1.5-flash" if (GEMINI_API_KEY or not OPENAI_API_KEY) else "gpt-3.5-turbo")

# Optional Supabase database configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "").strip() or os.environ.get("SUPABASE_ANON_KEY", "").strip()

# Initialize Flask app
app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
if HAS_CORS:
    CORS(app, resources={r"/api/*": {"origins": "*"}})

logging.basicConfig(
    level=logging.INFO if not DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("schemesathi")

# -----------------------------------------------------------------------------
# Curated, Verified Indian Government Schemes Dataset
# -----------------------------------------------------------------------------
INDIAN_STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand",
    "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur",
    "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab",
    "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura",
    "Uttar Pradesh", "Uttarakhand", "West Bengal",
    # Union Territories
    "Andaman and Nicobar Islands", "Chandigarh",
    "Dadra and Nagar Haveli and Daman and Diu", "Delhi (NCT)",
    "Jammu and Kashmir", "Ladakh", "Lakshadweep", "Puducherry"
]

CATEGORIES = [
    "Farmers and agriculture",
    "Health and healthcare",
    "Students and education",
    "Scholarships",
    "Women and children",
    "Small businesses",
    "Employment and skill development",
    "Housing",
    "Senior citizens",
    "Disability support",
    "Social welfare"
]

CURATED_SCHEMES: List[Dict[str, Any]] = [
    {
        "id": "pm-kisan",
        "name": "Pradhan Mantri Kisan Samman Nidhi (PM-KISAN)",
        "short_description": "Direct income support of ₹6,000 per year in three equal installments to all landholding farmer families across India.",
        "detailed_description": "PM-KISAN is a Central Sector scheme with 100% funding from Government of India. It became operational on 1st December 2018. Under the scheme, financial assistance of ₹6,000/- per annum is provided to all landholding farmer families, subject to certain exclusion criteria relating to higher income status. The amount is directly transferred into the bank accounts of the beneficiaries through Direct Benefit Transfer (DBT).",
        "category": "Farmers and agriculture",
        "government_level": "Central",
        "state": "All India",
        "benefits": "₹6,000 per year paid in three four-monthly installments of ₹2,000 each via DBT directly into the farmer's bank account.",
        "eligibility_summary": "All landholding farmer families who have cultivable landholding in their names. Subject to standard tax-payer and institutional landholder exclusions.",
        "eligibility_rules": {
            "min_age": 18,
            "max_age": 100,
            "occupations": ["farmer", "agriculture", "any"],
            "max_income": None,
            "gender": "all",
            "student_only": False,
            "farmer_only": True,
            "disability_friendly": True,
            "categories": ["All", "General", "OBC", "SC", "ST", "EWS"],
            "state_specific": "All India"
        },
        "required_documents": [
            "Aadhaar Card (Mandatory)",
            "Land Holding Papers (Khatauni / Land Title Document)",
            "Active Savings Bank Account Passbook",
            "Aadhaar-linked Mobile Number"
        ],
        "application_steps": [
            "Visit the official PM-KISAN portal (pmkisan.gov.in).",
            "Click on 'New Farmer Registration' under the Farmers Corner.",
            "Choose Rural Farmer or Urban Farmer, enter your Aadhaar number and Mobile number, and select your State.",
            "Verify with OTP received on your mobile.",
            "Enter land details (Survey/Khata number, Khasra number, Area) and bank account details.",
            "Submit the application and note the registration reference number."
        ],
        "official_url": "https://pmkisan.gov.in",
        "source_name": "Ministry of Agriculture & Farmers Welfare / myScheme.gov.in",
        "last_verified": "2024-10-01",
        "status": "verified"
    },
    {
        "id": "pmjay-ayushman",
        "name": "Ayushman Bharat PM Jan Arogya Yojana (AB-PMJAY)",
        "short_description": "Cashless health insurance coverage of up to ₹5,00,000 per eligible family per year for secondary and tertiary hospitalization.",
        "detailed_description": "Ayushman Bharat PM-JAY is the world's largest government-funded health assurance scheme. It provides a health cover of ₹5 Lakh per family per year for secondary and tertiary care hospitalization to over 12 crore poor and vulnerable families (approximately 55 crore beneficiaries). In 2024, the Union Cabinet expanded PM-JAY coverage to all senior citizens aged 70 years and above irrespective of income.",
        "category": "Health and healthcare",
        "government_level": "Central",
        "state": "All India",
        "benefits": "Cashless and paperless access to healthcare services up to ₹5,00,000 per family per year at empaneled public and private hospitals across India.",
        "eligibility_summary": "Families listed in SECC 2011 deprivation criteria, active NFSA/Ration card beneficiaries, and all senior citizens aged 70 years and older.",
        "eligibility_rules": {
            "min_age": 0,
            "max_age": 120,
            "occupations": ["any"],
            "max_income": 300000,
            "gender": "all",
            "student_only": False,
            "farmer_only": False,
            "disability_friendly": True,
            "categories": ["All", "General", "OBC", "SC", "ST", "EWS"],
            "state_specific": "All India"
        },
        "required_documents": [
            "Aadhaar Card or Valid Government Photo ID",
            "Ration Card or Family Identification Document",
            "Active Mobile Number for OTP Verification"
        ],
        "application_steps": [
            "Visit the official Ayushman Bharat beneficiary portal (beneficiary.nha.gov.in).",
            "Login with your mobile number and authenticate via OTP.",
            "Search for your family using State, District, Sub-district, Ration Card, or Aadhaar number.",
            "Complete e-KYC using Aadhaar OTP or biometric authentication.",
            "Download your Ayushman Card (Golden Card) upon instant approval."
        ],
        "official_url": "https://pmjay.gov.in",
        "source_name": "National Health Authority (NHA) / myScheme.gov.in",
        "last_verified": "2024-10-01",
        "status": "verified"
    },
    {
        "id": "pmay-urban",
        "name": "Pradhan Mantri Awas Yojana - Urban 2.0 (PMAY-U)",
        "short_description": "Financial subsidy and assistance to build or purchase a pucca house for urban families without an existing permanent house.",
        "detailed_description": "PMAY-U addresses the affordable housing requirement of urban poor, including slum dwellers, EWS, and LIG segments. Under PMAY-U 2.0, the government provides interest subsidies on home loans, beneficiary-led construction support, and affordable housing in partnership. A pucca house constructed under the scheme must include basic civic amenities like water, sanitation, and electricity.",
        "category": "Housing",
        "government_level": "Central",
        "state": "All India",
        "benefits": "Financial assistance up to ₹2.5 Lakh for house construction or interest subsidy of up to 4% on home loans up to ₹25 Lakh for eligible EWS/LIG families.",
        "eligibility_summary": "Urban families that do not own a pucca house anywhere in India. Family annual income up to ₹3 Lakh for EWS, and up to ₹6 Lakh for LIG.",
        "eligibility_rules": {
            "min_age": 18,
            "max_age": 85,
            "occupations": ["any"],
            "max_income": 600000,
            "gender": "all",
            "student_only": False,
            "farmer_only": False,
            "disability_friendly": True,
            "categories": ["All", "General", "OBC", "SC", "ST", "EWS"],
            "state_specific": "All India"
        },
        "required_documents": [
            "Aadhaar Card of all family members",
            "Income Certificate issued by competent authority",
            "Proof of Land / Plot ownership (for Beneficiary-Led Construction)",
            "Bank Account Details with IFSC Code",
            "Affidavit declaring no pucca house is owned anywhere in India"
        ],
        "application_steps": [
            "Visit the official portal at pmaymis.gov.in or contact your local Municipal Corporation / Municipality office.",
            "Under 'Citizen Assessment', select 'Apply Online'.",
            "Enter your Aadhaar number and verify name.",
            "Fill in family details, current residential address, land details, and income details.",
            "Submit the application and track status using the generated Assessment ID."
        ],
        "official_url": "https://pmaymis.gov.in",
        "source_name": "Ministry of Housing and Urban Affairs (MoHUA)",
        "last_verified": "2024-09-15",
        "status": "verified"
    },
    {
        "id": "pm-mudra",
        "name": "Pradhan Mantri Mudra Yojana (PMMY)",
        "short_description": "Collateral-free institutional business loans up to ₹20 Lakh for micro and small enterprises across manufacturing, trading, and services.",
        "detailed_description": "PMMY enables micro and small enterprises to access credit from commercial banks, RRBs, Small Finance Banks, MFIs, and NBFCs. The scheme is categorized into four stages: Shishu (loans up to ₹50,000), Kishore (loans above ₹50,000 and up to ₹5 Lakh), Tarun (loans above ₹5 Lakh and up to ₹10 Lakh), and Tarun Plus (loans up to ₹20 Lakh for entrepreneurs who have previously repaid Tarun loans).",
        "category": "Small businesses",
        "government_level": "Central",
        "state": "All India",
        "benefits": "Collateral-free business loan up to ₹20 Lakh at competitive interest rates with flexible repayment terms of 3 to 5 years.",
        "eligibility_summary": "Any non-corporate, non-farm small/micro enterprise or individual entrepreneur engaged in income-generating activities in manufacturing, trading, services, or allied agriculture.",
        "eligibility_rules": {
            "min_age": 18,
            "max_age": 70,
            "occupations": ["small-business", "self-employed", "artisan", "street-vendor", "any"],
            "max_income": None,
            "gender": "all",
            "student_only": False,
            "farmer_only": False,
            "disability_friendly": True,
            "categories": ["All", "General", "OBC", "SC", "ST", "EWS"],
            "state_specific": "All India"
        },
        "required_documents": [
            "Proof of Identity (Aadhaar, Voter ID, PAN Card)",
            "Proof of Residence (Electricity bill, Ration card, Aadhaar)",
            "Business Enterprise Proof (Udyam Registration, Trade License, Shop Act)",
            "Bank Statement of last 6 months",
            "Project Report / Quotation of machinery or items to be purchased"
        ],
        "application_steps": [
            "Prepare a simple business plan and quotation for the items to be purchased.",
            "Visit the JanSamarth Portal (jansamarth.in) or your nearest commercial bank / microfinance institution.",
            "Apply under PMMY specifying the loan tier: Shishu, Kishore, or Tarun.",
            "Submit KYC documents, business proof, and quotation.",
            "Upon sanction, receive loan disbursement directly into your current/savings account with a MUDRA debit card."
        ],
        "official_url": "https://www.mudra.org.in",
        "source_name": "Department of Financial Services, Ministry of Finance",
        "last_verified": "2024-10-01",
        "status": "verified"
    },
    {
        "id": "pm-svanidhi",
        "name": "PM Street Vendor's AtmaNirbhar Nidhi (PM SVANidhi)",
        "short_description": "Collateral-free working capital micro-credit starting from ₹10,000 to ₹50,000 with 7% interest subsidy for urban street vendors.",
        "detailed_description": "PM SVANidhi is a special micro-credit scheme launched by the Ministry of Housing and Urban Affairs to provide affordable working capital loans to street vendors to resume their livelihoods. The scheme offers an initial working capital loan of up to ₹10,000 (1st tranche), upon timely repayment a 2nd tranche of up to ₹20,000, and a 3rd tranche of up to ₹50,000. It also provides a 7% interest subsidy and cashback of up to ₹1,200 per year on digital transactions.",
        "category": "Employment and skill development",
        "government_level": "Central",
        "state": "All India",
        "benefits": "Working capital loan up to ₹50,000, 7% annual interest subsidy credited via DBT, and up to ₹100/month cashback on digital merchant transactions.",
        "eligibility_summary": "Urban street vendors, hawkers, thelawalas vending in urban areas possessing a Certificate of Vending / ID card issued by Urban Local Bodies (ULBs) or Letter of Recommendation (LoR).",
        "eligibility_rules": {
            "min_age": 18,
            "max_age": 75,
            "occupations": ["street-vendor", "self-employed", "artisan", "any"],
            "max_income": 300000,
            "gender": "all",
            "student_only": False,
            "farmer_only": False,
            "disability_friendly": True,
            "categories": ["All", "General", "OBC", "SC", "ST", "EWS"],
            "state_specific": "All India"
        },
        "required_documents": [
            "Certificate of Vending (CoV) / Identity Card issued by ULB / Letter of Recommendation (LoR)",
            "Aadhaar Card",
            "Bank Account Passbook / Statement",
            "Mobile number linked to Aadhaar"
        ],
        "application_steps": [
            "Visit the official portal at pmsvanidhi.mohua.gov.in or apply via Common Service Centre (CSC).",
            "Check your name in the ULB street vendor survey list.",
            "If your name is not in survey, obtain a Letter of Recommendation (LoR) from your Urban Local Body.",
            "Fill the online loan application and select your preferred lending institution.",
            "Lending bank verifies application and disburses loan amount directly."
        ],
        "official_url": "https://pmsvanidhi.mohua.gov.in",
        "source_name": "Ministry of Housing and Urban Affairs",
        "last_verified": "2024-09-20",
        "status": "verified"
    },
    {
        "id": "nsp-post-matric",
        "name": "Post-Matric Scholarship Scheme for SC / ST / OBC Students",
        "short_description": "Financial assistance covering compulsory tuition fees and maintenance allowance for post-secondary education of marginalized students.",
        "detailed_description": "Post-Matric Scholarships are centrally sponsored schemes implemented through State Governments and UT Administrations. They provide substantial financial support to students belonging to Scheduled Castes, Scheduled Tribes, and Other Backward Classes studying at post-matriculation or post-secondary stages (Class 11 to PhD) to enable them to complete their higher education.",
        "category": "Scholarships",
        "government_level": "Central",
        "state": "All India",
        "benefits": "Full reimbursement of non-refundable compulsory course fees plus a monthly maintenance allowance ranging from ₹2,500 to ₹13,500 per year depending on hosteller/day scholar status and course group.",
        "eligibility_summary": "Indian national students belonging to SC, ST, or OBC categories pursuing post-matriculation studies in recognized institutions. Annual family income must not exceed ₹2,50,000.",
        "eligibility_rules": {
            "min_age": 15,
            "max_age": 35,
            "occupations": ["student", "any"],
            "max_income": 250000,
            "gender": "all",
            "student_only": True,
            "farmer_only": False,
            "disability_friendly": True,
            "categories": ["SC", "ST", "OBC"],
            "state_specific": "All India"
        },
        "required_documents": [
            "Community / Caste Certificate issued by competent revenue authority",
            "Annual Family Income Certificate",
            "Previous Qualifying Examination Marks Sheet",
            "Institution Fee Receipt and Bonafide Certificate",
            "Aadhaar Card and Student Bank Passbook (Aadhaar seeded)"
        ],
        "application_steps": [
            "Visit the National Scholarship Portal (scholarships.gov.in).",
            "Register as a new student to generate a One-Time Registration (OTR) number using Aadhaar.",
            "Log in and fill the Post-Matric Scholarship application form.",
            "Upload verified documents and submit application.",
            "Application is verified online by the Institution Nodal Officer and District Welfare Officer, followed by DBT disbursement."
        ],
        "official_url": "https://scholarships.gov.in",
        "source_name": "Ministry of Social Justice and Empowerment / NSP",
        "last_verified": "2024-10-05",
        "status": "verified"
    },
    {
        "id": "sukanya-samriddhi",
        "name": "Sukanya Samriddhi Yojana (SSY)",
        "short_description": "High-interest, sovereign-backed government savings scheme designed exclusively to secure the future education and marriage of the girl child.",
        "detailed_description": "Sukanya Samriddhi Account is a government-backed savings scheme launched under the 'Beti Bachao, Beti Padhao' campaign. Parents or legal guardians can open an account for a girl child from her birth up to the age of 10 years. The scheme currently offers an attractive interest rate of 8.2% per annum, compounded yearly, with triple tax exemption (EEE status under Section 80C).",
        "category": "Women and children",
        "government_level": "Central",
        "state": "All India",
        "benefits": "Government-guaranteed high interest rate (currently 8.2% p.a.), tax exemption under Section 80C, partial withdrawal allowed after age 18 for higher education, and complete maturity payout upon reaching 21 years.",
        "eligibility_summary": "Can be opened by parent or legal guardian for an Indian girl child below 10 years of age. Maximum 2 accounts per family (with exception for twins/triplets).",
        "eligibility_rules": {
            "min_age": 0,
            "max_age": 10,
            "occupations": ["any"],
            "max_income": None,
            "gender": "female",
            "student_only": False,
            "farmer_only": False,
            "disability_friendly": True,
            "categories": ["All", "General", "OBC", "SC", "ST", "EWS"],
            "state_specific": "All India"
        },
        "required_documents": [
            "Birth Certificate of the girl child (Mandatory)",
            "Identity Proof of Parent / Legal Guardian (Aadhaar, PAN, Passport)",
            "Address Proof of Parent / Guardian",
            "Passport size photos of the girl child and parent"
        ],
        "application_steps": [
            "Visit any Post Office branch or authorized public/private commercial bank (e.g. SBI, PNB, BOB).",
            "Obtain and fill the Sukanya Samriddhi Account Opening Form.",
            "Attach the girl child's birth certificate and guardian KYC documents.",
            "Deposit the initial opening amount (minimum ₹250, maximum ₹1,50,000 per financial year).",
            "Receive the SSY account passbook recording all deposits and interest credits."
        ],
        "official_url": "https://www.indiapost.gov.in",
        "source_name": "Ministry of Finance / Department of Posts",
        "last_verified": "2024-09-30",
        "status": "verified"
    },
    {
        "id": "pm-matru-vandana",
        "name": "Pradhan Mantri Matru Vandana Yojana (PMMVY)",
        "short_description": "Maternity cash incentive of ₹5,000 for the first child and ₹6,000 for a second girl child to improve maternal nutrition and health.",
        "detailed_description": "PMMVY is a Centrally Sponsored DBT scheme under Mission Shakti for pregnant women and lactating mothers. It compensates for wage loss in terms of cash incentive so that the woman can take adequate rest before and after delivery of the first living child, as well as an enhanced benefit of ₹6,000 for a second child if it is a girl child.",
        "category": "Women and children",
        "government_level": "Central",
        "state": "All India",
        "benefits": "Cash incentive of ₹5,000 in two installments for the first child and ₹6,000 in a single installment for a second girl child directly credited via DBT.",
        "eligibility_summary": "Pregnant women and lactating mothers who are 19 years of age or older. Excludes women in regular employment with Central/State Government or PSUs.",
        "eligibility_rules": {
            "min_age": 19,
            "max_age": 50,
            "occupations": ["any"],
            "max_income": 800000,
            "gender": "female",
            "student_only": False,
            "farmer_only": False,
            "disability_friendly": True,
            "categories": ["All", "General", "OBC", "SC", "ST", "EWS"],
            "state_specific": "All India"
        },
        "required_documents": [
            "Mother and Child Protection (MCP) Card registered with Anganwadi / Health Centre",
            "Aadhaar Card of the Beneficiary Woman and Husband",
            "Aadhaar-seeded Bank / Post Office Account Passbook",
            "Child Birth Certificate (for second installment / second girl child benefit)"
        ],
        "application_steps": [
            "Register pregnancy at the nearest Anganwadi Centre (AWC) or approved health facility within 570 days of LMP.",
            "Apply online through the PMMVY portal (pmmvy.wcd.gov.in) or submit Form 1A/1B at the Anganwadi Centre.",
            "Verify Aadhaar details and link your bank account.",
            "Upon fulfilling ANC check-up criteria and institutional delivery, installments are credited directly to your bank account."
        ],
        "official_url": "https://pmmvy.wcd.gov.in",
        "source_name": "Ministry of Women and Child Development",
        "last_verified": "2024-09-18",
        "status": "verified"
    },
    {
        "id": "atal-pension-yojana",
        "name": "Atal Pension Yojana (APY)",
        "short_description": "Government-guaranteed lifelong monthly pension of ₹1,000 to ₹5,000 from age 60 for citizens working in the unorganized sector.",
        "detailed_description": "Atal Pension Yojana is a periodic pension scheme administered by PFRDA focused on unorganized sector workers. Subscribers make monthly contributions depending on their entry age (between 18 and 40 years). From age 60, a guaranteed monthly pension between ₹1,000 and ₹5,000 is paid for life. After subscriber demise, the spouse continues to receive the pension, and after both pass away, the accumulated pension wealth is returned to the nominee.",
        "category": "Senior citizens",
        "government_level": "Central",
        "state": "All India",
        "benefits": "Guaranteed minimum monthly pension of ₹1,000, ₹2,000, ₹3,000, ₹4,000, or ₹5,000 from the age of 60 years till death.",
        "eligibility_summary": "Any Indian citizen between 18 and 40 years of age with an active savings bank account. Must not be an existing income-tax payer.",
        "eligibility_rules": {
            "min_age": 18,
            "max_age": 40,
            "occupations": ["unorganized-worker", "self-employed", "wage-worker", "any"],
            "max_income": 250000,
            "gender": "all",
            "student_only": False,
            "farmer_only": False,
            "disability_friendly": True,
            "categories": ["All", "General", "OBC", "SC", "ST", "EWS"],
            "state_specific": "All India"
        },
        "required_documents": [
            "Active Savings Bank Account Passbook / Account Number",
            "Aadhaar Card",
            "Mobile number registered with bank for auto-debit SMS alerts",
            "Nominee details (Aadhaar & relationship proof)"
        ],
        "application_steps": [
            "Visit your bank branch or access your bank's Internet Banking / Mobile Banking app.",
            "Fill out the APY Subscriber Registration Form.",
            "Select your desired monthly pension amount (₹1,000 to ₹5,000).",
            "Enable auto-debit consent for monthly/quarterly/half-yearly contribution from your bank account.",
            "Receive your Permanent Retirement Account Number (PRAN) card acknowledging enrollment."
        ],
        "official_url": "https://www.npscra.nsdl.co.in",
        "source_name": "Pension Fund Regulatory and Development Authority (PFRDA)",
        "last_verified": "2024-10-02",
        "status": "verified"
    },
    {
        "id": "pm-vishwakarma",
        "name": "PM Vishwakarma Scheme",
        "short_description": "Holistic support including skill training, ₹15,000 toolkit grant, and collateral-free loans up to ₹3 Lakh at 5% interest for traditional artisans.",
        "detailed_description": "PM Vishwakarma is a flagship Central Sector Scheme designed to support traditional artisans and craftspeople who work with their hands and tools. Covering 18 traditional trades such as carpenters, blacksmiths, goldsmiths, potters, sculptors, cobblers, tailors, and boat makers, it provides formal recognition through PM Vishwakarma Certificate, free skill upgradation with stipend, digital marketing support, and enterprise credit.",
        "category": "Employment and skill development",
        "government_level": "Central",
        "state": "All India",
        "benefits": "Official PM Vishwakarma Certificate & ID, basic skill training with ₹500/day stipend, ₹15,000 e-voucher for modern toolkits, and collateral-free enterprise loan: Tranche 1 up to ₹1,00,000 and Tranche 2 up to ₹2,00,000 at 5% interest.",
        "eligibility_summary": "Traditional artisans and craftspeople engaged in one of the 18 specified trades on a self-employment basis. Minimum age 18 years. One member per family.",
        "eligibility_rules": {
            "min_age": 18,
            "max_age": 75,
            "occupations": ["artisan", "self-employed", "street-vendor", "any"],
            "max_income": None,
            "gender": "all",
            "student_only": False,
            "farmer_only": False,
            "disability_friendly": True,
            "categories": ["All", "General", "OBC", "SC", "ST", "EWS"],
            "state_specific": "All India"
        },
        "required_documents": [
            "Aadhaar Card with linked mobile number",
            "Ration Card or Family Document",
            "Active Bank Account Passbook",
            "Self-declaration of practicing one of 18 traditional trades"
        ],
        "application_steps": [
            "Visit the nearest Common Service Centre (CSC) with your Aadhaar and mobile phone.",
            "Biometric authentication and verification of family details via CSC operator.",
            "Select your specific trade (e.g. Badhai, Luhar, Kumhaar, Darzi, etc.).",
            "Gram Panchayat / Urban Local Body conducts three-tier verification of artisan trade practice.",
            "Download digital PM Vishwakarma ID card and enroll in basic 5-7 days training."
        ],
        "official_url": "https://pmvishwakarma.gov.in",
        "source_name": "Ministry of Micro, Small and Medium Enterprises (MSME)",
        "last_verified": "2024-10-01",
        "status": "verified"
    },
    {
        "id": "nmms-scholarship",
        "name": "National Means-cum-Merit Scholarship Scheme (NMMSS)",
        "short_description": "Scholarship of ₹12,000 per year for meritorious students from economically weaker sections from Class 9 through Class 12.",
        "detailed_description": "NMMSS is a Centrally Sponsored Scheme aimed at arresting dropout rates after Class 8 and encouraging economically weaker meritorious students to continue secondary stage education. One lakh fresh scholarships are awarded every year to selected Class 9 students across India, continuing till Class 12 upon meeting renewal criteria.",
        "category": "Scholarships",
        "government_level": "Central",
        "state": "All India",
        "benefits": "₹12,000 per academic year (₹1,000 per month) paid directly into the student's Aadhaar-linked bank account via DBT.",
        "eligibility_summary": "Students studying in Class 8 in State Government, Local Body, or Govt-aided schools with at least 55% marks in Class 7 (50% for SC/ST). Parental annual income must not exceed ₹3,50,000.",
        "eligibility_rules": {
            "min_age": 12,
            "max_age": 19,
            "occupations": ["student", "any"],
            "max_income": 350000,
            "gender": "all",
            "student_only": True,
            "farmer_only": False,
            "disability_friendly": True,
            "categories": ["All", "General", "OBC", "SC", "ST", "EWS"],
            "state_specific": "All India"
        },
        "required_documents": [
            "Class 7 Final Examination Mark Sheet",
            "Parental Income Certificate from competent authority",
            "Caste Certificate (if applying under SC/ST/OBC quota)",
            "Disability Certificate (if applicable)",
            "Student Aadhaar Card and Aadhaar-seeded Bank Passbook"
        ],
        "application_steps": [
            "Appear for the State-level NMMS written selection exam organized in Class 8.",
            "Upon clearing the exam, register on the National Scholarship Portal (scholarships.gov.in).",
            "Submit online application under Department of School Education and Literacy.",
            "School Headmaster and District Nodal Officer verify credentials online.",
            "Scholarship amount is disbursed annually via DBT on NSP."
        ],
        "official_url": "https://scholarships.gov.in",
        "source_name": "Department of School Education & Literacy, Ministry of Education",
        "last_verified": "2024-09-10",
        "status": "verified"
    },
    {
        "id": "ignao-pension",
        "name": "Indira Gandhi National Old Age Pension Scheme (IGNOAPS)",
        "short_description": "Non-contributory monthly social pension for destitute senior citizens aged 60 years and above living below poverty line.",
        "detailed_description": "IGNOAPS is one of the core sub-schemes under the National Social Assistance Programme (NSAP). It provides monthly cash financial assistance to destitute elderly persons with little or no regular means of subsistence. The Central Government provides a core monthly pension, which is supplemented with substantial additional state contributions by various State Governments.",
        "category": "Senior citizens",
        "government_level": "Central",
        "state": "All India",
        "benefits": "Monthly pension of ₹200 to ₹500 from Central Government, supplemented with additional ₹1,000 to ₹3,000 by State Governments depending on domicile.",
        "eligibility_summary": "Indian citizens aged 60 years or older belonging to a household categorized as Below Poverty Line (BPL) according to criteria prescribed by Govt of India.",
        "eligibility_rules": {
            "min_age": 60,
            "max_age": 120,
            "occupations": ["any"],
            "max_income": 100000,
            "gender": "all",
            "student_only": False,
            "farmer_only": False,
            "disability_friendly": True,
            "categories": ["All", "General", "OBC", "SC", "ST", "EWS"],
            "state_specific": "All India"
        },
        "required_documents": [
            "Proof of Age (Aadhaar, Voter ID, Birth Certificate)",
            "BPL Ration Card / BPL Survey Inclusion Certificate",
            "Bank Passbook or Post Office Savings Account details",
            "Passport size photograph"
        ],
        "application_steps": [
            "Obtain the NSAP Old Age Pension Application Form from your local Gram Panchayat, Block Development Officer (BDO), or Municipality.",
            "Alternatively, apply online via the State Social Welfare Portal or nsap.nic.in.",
            "Attach proof of age, BPL documentation, and bank account details.",
            "Verification is performed by the Revenue Inspector or Social Security Officer.",
            "Monthly pension is credited into the beneficiary's bank account or postal savings account."
        ],
        "official_url": "https://nsap.nic.in",
        "source_name": "Ministry of Rural Development / NSAP",
        "last_verified": "2024-09-25",
        "status": "verified"
    },
    {
        "id": "igndp-pension",
        "name": "Indira Gandhi National Disability Pension Scheme (IGNDPS)",
        "short_description": "Monthly disability pension support for individuals aged 18-79 with severe or multiple disabilities living below poverty line.",
        "detailed_description": "IGNDPS is an essential component of the National Social Assistance Programme (NSAP) providing income security to severely differently-abled persons in destitute and BPL households. The Central assistance is augmented by state social welfare pensions to ensure a dignity floor of living.",
        "category": "Disability support",
        "government_level": "Central",
        "state": "All India",
        "benefits": "Monthly financial pension of ₹300 (Central component) plus additional State Government top-ups ranging from ₹1,000 to ₹3,000 per month.",
        "eligibility_summary": "Individuals aged 18 to 79 years with severe or multiple disabilities (80% disability or higher) living below the poverty line.",
        "eligibility_rules": {
            "min_age": 18,
            "max_age": 79,
            "occupations": ["any"],
            "max_income": 100000,
            "gender": "all",
            "student_only": False,
            "farmer_only": False,
            "disability_friendly": True,
            "categories": ["All", "General", "OBC", "SC", "ST", "EWS"],
            "state_specific": "All India"
        },
        "required_documents": [
            "Unique Disability ID (UDID) Card or Disability Medical Certificate certifying 80%+ disability",
            "BPL Ration Card / Proof of BPL status",
            "Aadhaar Card",
            "Bank Account Passbook"
        ],
        "application_steps": [
            "Ensure you have an authorized UDID card from swavlambancard.gov.in.",
            "Apply through your local Block Development Office (BDO), Taluk Office, or online on the State Social Security portal.",
            "Submit disability certificate along with BPL proof and bank passbook.",
            "Upon sanction, pension is disbursed monthly through DBT."
        ],
        "official_url": "https://nsap.nic.in",
        "source_name": "Ministry of Rural Development / Dept of Empowerment of Persons with Disabilities",
        "last_verified": "2024-09-12",
        "status": "verified"
    },
    {
        "id": "stand-up-india",
        "name": "Stand-Up India Scheme",
        "short_description": "Bank financing between ₹10 Lakh and ₹1 Crore for SC, ST, and Women entrepreneurs setting up greenfield enterprises.",
        "detailed_description": "Stand-Up India facilitates bank loans between ₹10 Lakh and ₹1 Crore to at least one Scheduled Caste (SC) or Scheduled Tribe (ST) borrower and at least one woman borrower per bank branch for setting up a greenfield enterprise in manufacturing, services, or trading sector, as well as activities allied to agriculture.",
        "category": "Small businesses",
        "government_level": "Central",
        "state": "All India",
        "benefits": "Composite bank loan between ₹10 Lakh and ₹1 Crore covering up to 85% of project cost with repayment over 7 years with maximum 18 months moratorium.",
        "eligibility_summary": "SC/ST and/or Woman entrepreneurs above 18 years of age. For non-individual enterprises, at least 51% shareholding and controlling stake must be held by an SC/ST or woman.",
        "eligibility_rules": {
            "min_age": 18,
            "max_age": 70,
            "occupations": ["small-business", "self-employed", "artisan", "any"],
            "max_income": None,
            "gender": "all",
            "student_only": False,
            "farmer_only": False,
            "disability_friendly": True,
            "categories": ["SC", "ST", "All"],
            "state_specific": "All India"
        },
        "required_documents": [
            "Proof of Identity and Address (Aadhaar, Passport, PAN)",
            "Caste Certificate (for SC/ST applicants)",
            "Comprehensive Project Report for the proposed enterprise",
            "Partnership Deed / Memorandum of Association (for non-individual units)",
            "Bank statement for previous 6 months"
        ],
        "application_steps": [
            "Visit the official Stand-Up Mitra portal (standupmitra.in).",
            "Register as a borrower and fill the online loan application.",
            "Select your preferred commercial bank branch or request handholding support.",
            "Submit the detailed project profile and requisite business credentials.",
            "Loan is processed and sanctioned by the lead bank branch."
        ],
        "official_url": "https://www.standupmitra.in",
        "source_name": "Department of Financial Services, Ministry of Finance",
        "last_verified": "2024-09-15",
        "status": "verified"
    },
    {
        "id": "rythu-bharosa-ap",
        "name": "YSR Rythu Bharosa / PM-KISAN (Andhra Pradesh)",
        "short_description": "Comprehensive agricultural financial assistance of ₹13,500 per year for farmer and tenant families in Andhra Pradesh.",
        "detailed_description": "YSR Rythu Bharosa is a flagship welfare program of the Government of Andhra Pradesh providing ₹13,500 per annum per farmer family (comprising ₹6,000 from Central PM-KISAN and ₹7,500 contributed by Andhra Pradesh State Government). Uniquely, the scheme also extends full financial assistance of ₹13,500 entirely funded by the state to landless eligible SC, ST, BC, and Minority tenant farmers and ROFR cultivators.",
        "category": "Farmers and agriculture",
        "government_level": "State",
        "state": "Andhra Pradesh",
        "benefits": "₹13,500 per farmer family per year disbursed in three seasonal phases (₹7,500 in May before Kharif, ₹4,000 in October for Rabi, and ₹2,000 in January for Sankranti harvest).",
        "eligibility_summary": "Resident farmer families in Andhra Pradesh holding agricultural land, or registered tenant farmers belonging to SC, ST, BC, and Minority communities with CCRC agreements.",
        "eligibility_rules": {
            "min_age": 18,
            "max_age": 100,
            "occupations": ["farmer", "agriculture", "any"],
            "max_income": None,
            "gender": "all",
            "student_only": False,
            "farmer_only": True,
            "disability_friendly": True,
            "categories": ["All", "General", "OBC", "SC", "ST", "EWS"],
            "state_specific": "Andhra Pradesh"
        },
        "required_documents": [
            "Aadhaar Card of the farmer",
            "Pattadar Passbook / Land Record (ROR 1-B title deed)",
            "Crop Cultivator Rights Card (CCRC) for tenant farmers",
            "Aadhaar-linked Bank Account details"
        ],
        "application_steps": [
            "Visit your local Rythu Bharosa Kendram (RBK) / Village Secretariats in Andhra Pradesh.",
            "Consult the Village Agriculture Assistant (VAA) to verify inclusion in the Webland land records database.",
            "Tenant farmers submit the tripartite CCRC agreement countersigned by the landowner.",
            "Social audit list is displayed at the RBK for transparent community verification.",
            "Benefits are disbursed directly via DBT into the farmer's bank account."
        ],
        "official_url": "https://ysrrythubharosa.ap.gov.in",
        "source_name": "Department of Agriculture, Government of Andhra Pradesh",
        "last_verified": "2024-09-01",
        "status": "verified"
    },
    {
        "id": "kalaignar-magalir-tn",
        "name": "Kalaignar Magalir Urimai Thogai (Tamil Nadu)",
        "short_description": "Rights grant of ₹1,000 per month directly to women heads of eligible households across Tamil Nadu to honor unpaid domestic work.",
        "detailed_description": "Kalaignar Magalir Urimai Thogai is a landmark basic income security scheme launched by the Government of Tamil Nadu. It provides an unalienable monthly rights entitlement of ₹1,000 to female family heads. The scheme recognizes women's unpaid household contributions, fosters financial independence, and improves the socio-economic standing of working-class families across the state.",
        "category": "Women and children",
        "government_level": "State",
        "state": "Tamil Nadu",
        "benefits": "Direct monthly transfer of ₹1,000 (₹12,000 annually) into the beneficiary woman's bank account.",
        "eligibility_summary": "Women aged 21 or older who are heads of families in Tamil Nadu. Family annual income must be below ₹2.5 Lakh, annual domestic electricity consumption below 3,600 units, and family landholding under 5 acres wetland or 10 acres dryland.",
        "eligibility_rules": {
            "min_age": 21,
            "max_age": 100,
            "occupations": ["any"],
            "max_income": 250000,
            "gender": "female",
            "student_only": False,
            "farmer_only": False,
            "disability_friendly": True,
            "categories": ["All", "General", "OBC", "SC", "ST", "EWS"],
            "state_specific": "Tamil Nadu"
        },
        "required_documents": [
            "Smart Family Ration Card issued in Tamil Nadu",
            "Aadhaar Card of the woman applicant",
            "Recent Domestic Electricity Consumer Bill number",
            "Bank Passbook linked to Aadhaar"
        ],
        "application_steps": [
            "Collect application token from your fair price ration shop.",
            "Attend the special enrollment camp organized at your ward/village with your smart ration card, Aadhaar, and electricity bill.",
            "Submit biometric verification at the e-Seva camp counter.",
            "Applications undergo field verification through designated government inspectors.",
            "Monthly assistance is credited on the 15th of every calendar month via DBT."
        ],
        "official_url": "https://kmut.tn.gov.in",
        "source_name": "Special Programme Implementation Department, Govt of Tamil Nadu",
        "last_verified": "2024-09-10",
        "status": "verified"
    },
    {
        "id": "ladli-behna-mp",
        "name": "Mukhyamantri Ladli Behna Yojana (Madhya Pradesh)",
        "short_description": "Monthly economic assistance of ₹1,250 transferred to bank accounts of women residents in Madhya Pradesh to foster economic autonomy.",
        "detailed_description": "Mukhyamantri Ladli Behna Yojana was launched by the Government of Madhya Pradesh to foster health, nutritional wellness, and self-reliance among women. The scheme deposits ₹1,250 per month directly into the Aadhaar-linked DBT bank accounts of married women, widows, divorcees, and abandoned women aged 21 to 60 residing in Madhya Pradesh.",
        "category": "Women and children",
        "government_level": "State",
        "state": "Madhya Pradesh",
        "benefits": "Monthly financial aid of ₹1,250 (₹15,000 per annum) directly deposited into beneficiary's bank account via Aadhaar-enabled DBT.",
        "eligibility_summary": "Resident women of Madhya Pradesh aged 21 to 60 years. Total family annual income must be less than ₹2.5 Lakh. No family member should be a government employee or income tax payer.",
        "eligibility_rules": {
            "min_age": 21,
            "max_age": 60,
            "occupations": ["any"],
            "max_income": 250000,
            "gender": "female",
            "student_only": False,
            "farmer_only": False,
            "disability_friendly": True,
            "categories": ["All", "General", "OBC", "SC", "ST", "EWS"],
            "state_specific": "Madhya Pradesh"
        },
        "required_documents": [
            "Samagra Family ID and Individual Member ID",
            "Aadhaar Card",
            "Active Bank Account seeded with Aadhaar and DBT enabled",
            "Active Mobile Number"
        ],
        "application_steps": [
            "Ensure your Samagra e-KYC is updated and your bank account is DBT active.",
            "Attend the Ladli Behna camp at your Gram Panchayat or Ward office.",
            "Government volunteers complete the online form on cmladlibehna.mp.gov.in and take your live photograph.",
            "Receive an acknowledgment slip with your unique registration number.",
            "Funds are credited directly on the 10th of every month."
        ],
        "official_url": "https://cmladlibehna.mp.gov.in",
        "source_name": "Department of Women and Child Development, Govt of Madhya Pradesh",
        "last_verified": "2024-08-30",
        "status": "verified"
    },
    {
        "id": "yuva-nidhi-karnataka",
        "name": "Yuva Nidhi Scheme (Karnataka)",
        "short_description": "Monthly financial assistance of ₹3,000 for degree holders and ₹1,500 for diploma holders for up to 2 years while seeking employment.",
        "detailed_description": "Yuva Nidhi is an unemployment allowance and youth empowerment initiative by the Government of Karnataka. It assists educated youth who have passed out with a recognized degree or diploma from Karnataka institutions and have remained unemployed for at least 6 months after graduation, helping cover costs while they pursue skill training or look for career opportunities.",
        "category": "Employment and skill development",
        "government_level": "State",
        "state": "Karnataka",
        "benefits": "₹3,000 per month for unemployed graduates and ₹1,500 per month for unemployed diploma holders for up to 24 months, along with free skill training options.",
        "eligibility_summary": "Karnataka domicile youth who graduated or completed diplomas from Karnataka institutions and have not secured employment or enrolled in higher studies within 6 months of course completion.",
        "eligibility_rules": {
            "min_age": 19,
            "max_age": 30,
            "occupations": ["unemployed", "student", "any"],
            "max_income": 800000,
            "gender": "all",
            "student_only": False,
            "farmer_only": False,
            "disability_friendly": True,
            "categories": ["All", "General", "OBC", "SC", "ST", "EWS"],
            "state_specific": "Karnataka"
        },
        "required_documents": [
            "Degree / Diploma Passing Certificate and Mark Sheets",
            "Karnataka Domicile Certificate / SSLC Marks Card showing 10 years study in Karnataka",
            "Aadhaar Card",
            "Bank Account linked to Aadhaar with DBT active",
            "Self-declaration of unemployment"
        ],
        "application_steps": [
            "Visit the Karnataka Seva Sindhu portal (sevasindhu.karnataka.gov.in).",
            "Log in or register using your Aadhaar number.",
            "Select Yuva Nidhi scheme application.",
            "Provide education credentials, university roll number, and domicile details.",
            "Submit monthly self-declaration on the portal confirming continuing unemployment to receive subsequent disbursements."
        ],
        "official_url": "https://sevasindhu.karnataka.gov.in",
        "source_name": "Dept of Skill Development, Entrepreneurship and Livelihood, Karnataka",
        "last_verified": "2024-09-01",
        "status": "verified"
    }
]

# -----------------------------------------------------------------------------
# Multilingual Translations (English, Telugu, Hindi)
# -----------------------------------------------------------------------------
TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "en": {
        "nav_home": "Home",
        "nav_explore": "Explore Schemes",
        "nav_checker": "Eligibility Checker",
        "nav_assistant": "AI Assistant",
        "nav_saved": "Saved Schemes",
        "hero_badge": "Government Scheme Guidance for Every Indian Citizen",
        "hero_title": "Discover Government Schemes You Are Eligible For",
        "hero_subtitle": "SchemeSathi AI simplifies Indian central and state government welfare programs. Check eligibility in minutes, find required documents, and get direct links to official application portals.",
        "hero_search_placeholder": "Search by scheme name, keyword (e.g. scholarship, farmer, housing)...",
        "hero_search_button": "Find Schemes",
        "stat_schemes": "Curated Schemes",
        "stat_states": "States & UTs Covered",
        "stat_free": "100% Free & Neutral",
        "popular_categories": "Popular Categories",
        "cat_farmers": "Farmers & Agriculture",
        "cat_health": "Health & Healthcare",
        "cat_education": "Students & Scholarships",
        "cat_women": "Women & Children",
        "cat_business": "Small Businesses",
        "cat_housing": "Housing",
        "cat_seniors": "Senior Citizens",
        "cat_disability": "Disability Support",
        "cat_all": "All Schemes",
        "filter_state": "Filter by State / UT",
        "filter_category": "Filter by Category",
        "filter_level": "Government Level",
        "filter_all_levels": "All Levels (Central & State)",
        "filter_central": "Central Government",
        "filter_state_level": "State Government",
        "filter_sort": "Sort By",
        "sort_relevance": "Most Relevant",
        "sort_name": "Scheme Name (A-Z)",
        "results_count": "Showing {count} schemes",
        "clear_filters": "Clear Filters",
        "card_benefits": "Key Benefits",
        "card_eligibility": "Eligibility Overview",
        "card_documents": "Key Documents",
        "btn_check_eligibility": "Check Eligibility",
        "btn_view_details": "View Full Details",
        "btn_save": "Save Scheme",
        "btn_saved": "Saved",
        "btn_remove": "Remove",
        "official_portal_link": "Official Government Portal",
        "last_verified_label": "Last Verified",
        "checker_title": "Smart Eligibility Checker",
        "checker_subtitle": "Answer a few basic, non-intrusive questions. We evaluate rules locally to show schemes that match your profile. No Aadhaar or personal ID required.",
        "form_age": "Your Age",
        "form_state": "State / Union Territory",
        "form_occupation": "Primary Occupation / Status",
        "form_student": "Are you currently a student?",
        "form_income": "Annual Family Income Range",
        "form_category": "Social Category (Optional / Scheme Quotas)",
        "form_farmer": "Do you or your family own agricultural land / farm?",
        "form_disability": "Do you have a certified disability (PwD)?",
        "form_gender": "Gender",
        "form_submit": "Evaluate My Eligibility",
        "form_reset": "Reset Form",
        "result_status_eligible": "Potentially Eligible",
        "result_status_review": "More Information Required",
        "result_status_ineligible": "Likely Not Eligible",
        "why_match": "Why this may match your profile",
        "missing_criteria": "Points to check or verify",
        "assistant_title": "SchemeSathi AI Assistant",
        "assistant_subtitle": "Ask questions in plain language about central & state welfare schemes, document checklists, and application steps.",
        "chat_placeholder": "Ask: Which scholarships suit college students? What schemes exist for AP farmers?",
        "chat_send": "Send",
        "chat_clear": "Clear Chat",
        "chat_welcome": "Namaste! I am your SchemeSathi Assistant. Ask me about government schemes, eligibility requirements, or documents for schemes like PM-KISAN, Ayushman Bharat, PMMVY, or Mudra loans.",
        "chat_prompt_1": "Which scholarships suit college students?",
        "chat_prompt_2": "Schemes for farmers in Andhra Pradesh?",
        "chat_prompt_3": "How can I apply for Ayushman Bharat?",
        "chat_prompt_4": "What documents are needed for PM Mudra loan?",
        "saved_title": "Your Saved Schemes",
        "saved_subtitle": "Schemes you bookmark are saved locally in your browser for quick review. You can print or copy this list as an application checklist.",
        "saved_empty": "You haven't saved any schemes yet. Click the heart or 'Save Scheme' button on any scheme card to keep it here.",
        "btn_print_checklist": "Print / Export Checklist",
        "btn_clear_saved": "Clear All Saved",
        "how_it_works_title": "How SchemeSathi Works",
        "how_step_1_title": "1. Explore & Filter",
        "how_step_1_desc": "Browse verified Central and State government schemes categorized by your life stage, profession, or need.",
        "how_step_2_title": "2. Check Eligibility",
        "how_step_2_desc": "Use our rule evaluation tool or ask the AI assistant to instantly see which welfare programs you may qualify for.",
        "how_step_3_title": "3. Apply on Official Portals",
        "how_step_3_desc": "Review the required documents checklist and navigate directly to official government portals to submit your application safely.",
        "disclaimer_title": "Important Official Disclaimer",
        "disclaimer_body": "SchemeSathi AI is an independent educational and informational guide. It is not affiliated with or endorsed by any government department. Eligibility checks provided here are indicative and based on publicly available guidelines. Final eligibility, approval, and disbursements rest exclusively with the respective Government of India and State Government authorities. Never share bank passwords, OTPs, or pay any unauthorized agents.",
        "footer_tagline": "Empowering citizens with clarity on public welfare programs.",
        "footer_official_sources": "Official Portals: myScheme.gov.in | india.gov.in | scholarships.gov.in | pmjay.gov.in",
        "footer_rights": "SchemeSathi AI - Public Information Platform. Free to use."
    },
    "te": {
        "nav_home": "హోమ్",
        "nav_explore": "పథకాలను చూడండి",
        "nav_checker": "అర్హత పరిశీలన",
        "nav_assistant": "AI సహాయకుడు",
        "nav_saved": "సేవ్ చేసిన పథకాలు",
        "hero_badge": "ప్రతి భారతీయ పౌరుడికి ప్రభుత్వ పథకాల మార్గదర్శి",
        "hero_title": "మీకు అర్హత ఉన్న ప్రభుత్వ పథకాలను కనుగొనండి",
        "hero_subtitle": "స్కీమ్‌సాథి AI కేంద్ర మరియు రాష్ట్ర ప్రభుత్వ సంక్షేమ పథకాలను సులభతరం చేస్తుంది. నిమిషాల్లో అర్హతను తనిఖీ చేయండి, అవసరమైన పత్రాలను తెలుసుకోండి మరియు అధికారిక దరఖాస్తు లింకులను పొందండి.",
        "hero_search_placeholder": "పథకం పేరు, కీవర్డ్ ద్వారా వెతకండి (ఉదా: స్కాలర్‌షిప్, రైతు, ఇల్లు)...",
        "hero_search_button": "పథకాలను వెతకండి",
        "stat_schemes": "పరిశీలించిన పథకాలు",
        "stat_states": "రాష్ట్రాలు & కేంద్రపాలిత ప్రాంతాలు",
        "stat_free": "100% ఉచితం & నిష్పాక్షికం",
        "popular_categories": "ప్రసిద్ధ విభాగాలు",
        "cat_farmers": "రైతులు & వ్యవసాయం",
        "cat_health": "ఆరోగ్యం & వైద్యం",
        "cat_education": "విద్యార్థులు & స్కాలర్‌షిప్‌లు",
        "cat_women": "మహిళలు & పిల్లలు",
        "cat_business": "చిన్న వ్యాపారాలు",
        "cat_housing": "గృహ నిర్మాణం",
        "cat_seniors": "వృద్ధులు",
        "cat_disability": "దివ్యాంగుల సహాయం",
        "cat_all": "అన్ని పథకాలు",
        "filter_state": "రాష్ట్రం ప్రకారం ఫిల్టర్ చేయండి",
        "filter_category": "విభాగం ప్రకారం ఫిల్టర్ చేయండి",
        "filter_level": "ప్రభుత్వ స్థాయి",
        "filter_all_levels": "అన్ని స్థాయిలు (కేంద్ర & రాష్ట్ర)",
        "filter_central": "కేంద్ర ప్రభుత్వం",
        "filter_state_level": "రాష్ట్ర ప్రభుత్వం",
        "filter_sort": "క్రమబద్ధీకరించు",
        "sort_relevance": "సంబంధితమైనవి",
        "sort_name": "పథకం పేరు (A-Z)",
        "results_count": "{count} పథకాలు చూపబడుతున్నాయి",
        "clear_filters": "ఫిల్టర్లు తొలగించండి",
        "card_benefits": "ప్రధాన ప్రయోజనాలు",
        "card_eligibility": "అర్హత సారాంశం",
        "card_documents": "కావలసిన పత్రాలు",
        "btn_check_eligibility": "అర్హత తనిఖీ చేయండి",
        "btn_view_details": "పూర్తి వివరాలు చూడండి",
        "btn_save": "సేవ్ చేయండి",
        "btn_saved": "సేవ్ చేయబడింది",
        "btn_remove": "తొలగించండి",
        "official_portal_link": "అధికారిక ప్రభుత్వ పోర్టల్",
        "last_verified_label": "చివరిగా ధృవీకరించబడింది",
        "checker_title": "స్మార్ట్ అర్హత పరిశీలన",
        "checker_subtitle": "కొన్ని ప్రాథమిక ప్రశ్నలకు సమాధానం ఇవ్వండి. మీ ప్రొఫైల్‌కు సరిపోయే పథకాలను మేము స్థానికంగా లెక్కిస్తాము. ఆధార్ లేదా సున్నితమైన వివరాలు అవసరం లేదు.",
        "form_age": "మీ వయస్సు",
        "form_state": "రాష్ట్రం / కేంద్రపాలిత ప్రాంతం",
        "form_occupation": "వృత్తి లేదా స్థితి",
        "form_student": "మీరు ప్రస్తుతం విద్యార్థినా?",
        "form_income": "వార్షిక కుటుంబ ఆదాయం",
        "form_category": "సామాజిక వర్గం (రిజర్వేషన్ కోటా కోసం)",
        "form_farmer": "మీకు లేదా మీ కుటుంబానికి వ్యవసాయ భూమి ఉందా?",
        "form_disability": "దివ్యాంగ సర్టిఫికేట్ (PwD) ఉందా?",
        "form_gender": "లింగం",
        "form_submit": "నా అర్హతను పరిశీలించు",
        "form_reset": "రీసెట్ చేయండి",
        "result_status_eligible": "అర్హత ఉండే అవకాశం ఉంది",
        "result_status_review": "మరింత సమాచారం అవసరం",
        "result_status_ineligible": "నిబంధనల ప్రకారం అర్హత తక్కువ",
        "why_match": "మీ ప్రొఫైల్‌కు ఇది ఎందుకు సరిపోతుంది",
        "missing_criteria": "సరిచూసుకోవాల్సిన అంశాలు",
        "assistant_title": "స్కీమ్‌సాథి AI అసిస్టెంట్",
        "assistant_subtitle": "కేంద్ర, రాష్ట్ర పథకాలు, అవసరమైన డాక్యుమెంట్లు మరియు దరఖాస్తు విధానం గురించి మీ ప్రశ్నలను సులభంగా అడగండి.",
        "chat_placeholder": "ఉదా: డిగ్రీ విద్యార్థులకు ఏ స్కాలర్‌షిప్‌లు ఉన్నాయి? రైతు భరోసా వివరాలు ఏమిటి?",
        "chat_send": "పంపండి",
        "chat_clear": "చాట్ క్లియర్ చేయండి",
        "chat_welcome": "నమస్కారం! నేను మీ స్కీమ్‌సాథి అసిస్టెంట్‌ని. పిఎం-కిసాన్, ఆయుష్మాన్ భారత్, రైతు భరోసా లేదా ముద్రా రుణాల గురించి నన్ను అడగండి.",
        "chat_prompt_1": "కాలేజీ విద్యార్థులకు ఏ స్కాలర్‌షిప్‌లు ఉన్నాయి?",
        "chat_prompt_2": "ఆంధ్రప్రదేశ్ రైతులకు ఏ పథకాలు ఉన్నాయి?",
        "chat_prompt_3": "ఆయుష్మాన్ భారత్ కార్డు ఎలా పొందాలి?",
        "chat_prompt_4": "పీఎం ముద్రా లోన్‌కు కావలసిన పత్రాలు ఏమిటి?",
        "saved_title": "మీరు సేవ్ చేసుకున్న పథకాలు",
        "saved_subtitle": "మీరు బుక్‌మార్క్ చేసిన పథకాలు మీ బ్రౌజర్‌లో సేవ్ చేయబడతాయి. వీటిని ప్రింట్ లేదా కాపీ చేసి చెక్‌లిస్ట్‌గా ఉపయోగించవచ్చు.",
        "saved_empty": "మీరు ఇంకా ఏ పథకాన్నీ సేవ్ చేయలేదు. పథకం కార్డుపై ఉన్న గుండె గుర్తుపై క్లిక్ చేసి ఇక్కడ భద్రపరుచుకోండి.",
        "btn_print_checklist": "చెక్‌లిస్ట్ ప్రింట్ చేయండి",
        "btn_clear_saved": "అన్నీ తొలగించండి",
        "how_it_works_title": "స్కీమ్‌సాథి ఎలా పనిచేస్తుంది",
        "how_step_1_title": "1. శోధించండి & ఫిల్టర్ చేయండి",
        "how_step_1_desc": "మీ వయస్సు, వృత్తి లేదా అవసరానికి తగినట్లుగా ధృవీకరించబడిన కేంద్ర మరియు రాష్ట్ర ప్రభుత్వ పథకాలను అన్వేషించండి.",
        "how_step_2_title": "2. అర్హతను పరిశీలించండి",
        "how_step_2_desc": "మా అర్హత కాలిక్యులేటర్ లేదా AI అసిస్టెంట్ ద్వారా మీకు ఏ పథకాలు వర్తిస్తాయో తక్షణమే తెలుసుకోండి.",
        "how_step_3_title": "3. అధికారిక పోర్టల్ ద్వారా దరఖాస్తు చేసుకోండి",
        "how_step_3_desc": "కావలసిన పత్రాల జాబితాను పరిశీలించి, నేరుగా అధికారిక ప్రభుత్వ వెబ్‌సైట్‌కు వెళ్లి సురక్షితంగా దరఖాస్తు చేయండి.",
        "disclaimer_title": "ముఖ్యమైన అధికారిక గమనిక",
        "disclaimer_body": "స్కీమ్‌సాథి AI ఒక స్వతంత్ర సమాచార వేదిక మాత్రమే. ఇది ఏ ప్రభుత్వ విభాగంతోనూ అధికారిక సంబంధం కలిగి లేదు. ఇక్కడ చూపబడే అర్హత కేవలం సూచిక మాత్రమే. తుది ఆమోదం సంబంధిత ప్రభుత్వ అధికారుల నిర్ణయంపై ఆధారపడి ఉంటుంది. ఎవరితోనూ బ్యాంక్ పాస్‌వర్డ్‌లు, ఓటీపీలు పంచుకోకండి.",
        "footer_tagline": "ప్రజా సంక్షేమ పథకాల సమాచారంతో పౌరులకు సాధికారత.",
        "footer_official_sources": "అధికారిక వెబ్‌సైట్లు: myScheme.gov.in | india.gov.in | scholarships.gov.in | pmjay.gov.in",
        "footer_rights": "స్కీమ్‌సాథి AI - ఉచిత ప్రజా సమాచార వేదిక."
    },
    "hi": {
        "nav_home": "होम",
        "nav_explore": "योजनाएं देखें",
        "nav_checker": "पात्रता जांचें",
        "nav_assistant": "एआई सहायक",
        "nav_saved": "सहेजी गई योजनाएं",
        "hero_badge": "प्रत्येक भारतीय नागरिक के लिए सरकारी योजना मार्गदर्शिका",
        "hero_title": "अपने लिए उपयुक्त सरकारी योजनाओं की खोज करें",
        "hero_subtitle": "स्कीमसाथी AI केंद्र और राज्य सरकार की कल्याणकारी योजनाओं को आसान बनाता है। मिनटों में अपनी पात्रता जांचें, आवश्यक दस्तावेज जानें और आधिकारिक आवेदन लिंक प्राप्त करें।",
        "hero_search_placeholder": "योजना का नाम, कीवर्ड से खोजें (उदा. छात्रवृत्ति, किसान, आवास)...",
        "hero_search_button": "योजनाएं खोजें",
        "stat_schemes": "सत्यापित योजनाएं",
        "stat_states": "राज्य और केंद्र शासित प्रदेश",
        "stat_free": "100% निःशुल्क और निष्पक्ष",
        "popular_categories": "प्रमुख श्रेणियां",
        "cat_farmers": "किसान और कृषि",
        "cat_health": "स्वास्थ्य और चिकित्सा",
        "cat_education": "विद्यार्थी और छात्रवृत्तियां",
        "cat_women": "महिलाएं और बच्चे",
        "cat_business": "लघु व्यवसाय व स्वरोजगार",
        "cat_housing": "आवास योजनाएं",
        "cat_seniors": "वरिष्ठ नागरिक",
        "cat_disability": "दिव्यांगजन सहायता",
        "cat_all": "सभी योजनाएं",
        "filter_state": "राज्य अनुसार फ़िल्टर करें",
        "filter_category": "श्रेणी अनुसार फ़िल्टर करें",
        "filter_level": "सरकार का स्तर",
        "filter_all_levels": "सभी स्तर (केंद्र व राज्य)",
        "filter_central": "केंद्र सरकार",
        "filter_state_level": "राज्य सरकार",
        "filter_sort": "क्रमबद्ध करें",
        "sort_relevance": "प्रासंगिकता अनुसार",
        "sort_name": "योजना का नाम (A-Z)",
        "results_count": "{count} योजनाएं दिखाई जा रही हैं",
        "clear_filters": "फ़िल्टर हटाएं",
        "card_benefits": "प्रमुख लाभ",
        "card_eligibility": "पात्रता सारांश",
        "card_documents": "आवश्यक दस्तावेज",
        "btn_check_eligibility": "पात्रता जांचें",
        "btn_view_details": "पूरी जानकारी देखें",
        "btn_save": "योजना सहेजें",
        "btn_saved": "सहेजा गया",
        "btn_remove": "हटाएं",
        "official_portal_link": "आधिकारिक सरकारी पोर्टल",
        "last_verified_label": "सत्यापन तिथि",
        "checker_title": "स्मार्ट पात्रता चेकर",
        "checker_subtitle": "कुछ बुनियादी प्रश्नों के उत्तर दें। हम आपकी प्रोफ़ाइल से मेल खाने वाली योजनाओं का मूल्यांकन करते हैं। आधार या कोई संवेदनशील जानकारी नहीं मांगी जाती।",
        "form_age": "आपकी आयु",
        "form_state": "राज्य / केंद्र शासित प्रदेश",
        "form_occupation": "मुख्य व्यवसाय या स्थिति",
        "form_student": "क्या आप वर्तमान में छात्र हैं?",
        "form_income": "वार्षिक पारिवारिक आय",
        "form_category": "सामाजिक श्रेणी (आरक्षण कोटा हेतु)",
        "form_farmer": "क्या आपके या आपके परिवार के पास कृषि भूमि है?",
        "form_disability": "क्या आप प्रमाणित दिव्यांगजन (PwD) हैं?",
        "form_gender": "लिंग",
        "form_submit": "मेरी पात्रता का मूल्यांकन करें",
        "form_reset": "रीसेट करें",
        "result_status_eligible": "संभावित रूप से पात्र",
        "result_status_review": "अतिरिक्त जानकारी आवश्यक",
        "result_status_ineligible": "वर्तमान नियमों के अनुसार अपात्र",
        "why_match": "यह योजना आपकी प्रोफ़ाइल से क्यों मेल खाती है",
        "missing_criteria": "सत्यापित करने योग्य मुख्य बिंदु",
        "assistant_title": "स्कीमसाथी AI सहायक",
        "assistant_subtitle": "सरकारी योजनाओं, आवश्यक दस्तावेजों और आवेदन प्रक्रियाओं के बारे में सरल भाषा में सवाल पूछें।",
        "chat_placeholder": "पूछें: कॉलेज छात्रों के लिए कौन सी छात्रवृत्तियां हैं? पीएम किसान की पात्रता क्या है?",
        "chat_send": "भेजें",
        "chat_clear": "चैट साफ़ करें",
        "chat_welcome": "नमस्ते! मैं आपका स्कीमसाथी सहायक हूँ। मुझसे पीएम-किसान, आयुष्मान भारत, पीएम आवास, लाडली बहना या मुद्रा लोन जैसी योजनाओं के बारे में पूछें।",
        "chat_prompt_1": "कॉलेज छात्रों के लिए प्रमुख छात्रवृत्तियां कौन सी हैं?",
        "chat_prompt_2": "किसानों के लिए प्रमुख सरकारी योजनाएं बताएं?",
        "chat_prompt_3": "आयुष्मान भारत कार्ड कैसे बनवाएं?",
        "chat_prompt_4": "मुद्रा लोन के लिए कौन से दस्तावेज चाहिए?",
        "saved_title": "आपकी सहेजी गई योजनाएं",
        "saved_subtitle": "आपके द्वारा बुकमार्क की गई योजनाएं आपके ब्राउज़र में सुरक्षित रहती हैं। इन्हें आप प्रिंट करके आवेदन चेकलिस्ट के रूप में उपयोग कर सकते हैं।",
        "saved_empty": "आपने अभी तक कोई योजना सहेजी नहीं है। किसी भी योजना कार्ड पर 'सहेजें' बटन दबाकर उसे यहाँ रखें।",
        "btn_print_checklist": "चेकलिस्ट प्रिंट / डाउनलोड करें",
        "btn_clear_saved": "सभी हटाएं",
        "how_it_works_title": "स्कीमसाथी कैसे काम करता है",
        "how_step_1_title": "1. खोजें और फ़िल्टर करें",
        "how_step_1_desc": "अपनी आयु, व्यवसाय या आवश्यकता के आधार पर सत्यापित केंद्र और राज्य सरकारी योजनाओं को ब्राउज़ करें।",
        "how_step_2_title": "2. पात्रता की जांच करें",
        "how_step_2_desc": "हमारे पात्रता कैलकुलेटर या एआई सहायक के माध्यम से तुरंत जानें कि आप किन योजनाओं के योग्य हैं।",
        "how_step_3_title": "3. आधिकारिक पोर्टल पर आवेदन करें",
        "how_step_3_desc": "दस्तावेजों की सूची देखकर सीधे सरकार के आधिकारिक पोर्टल पर जाएं और सुरक्षित आवेदन करें।",
        "disclaimer_title": "महत्वपूर्ण आधिकारिक अस्वीकरण",
        "disclaimer_body": "स्कीमसाथी AI एक स्वतंत्र सूचनात्मक व मार्गदर्शक मंच है। इसका किसी भी सरकारी विभाग से सीधा संबंध नहीं है। यहां दी गई पात्रता संकेत मात्र है। अंतिम निर्णय और अनुमोदन संबंधित सरकारी अधिकारियों द्वारा ही किया जाता है। कभी भी अपने बैंक पासवर्ड या ओटीपी किसी के साथ साझा न करें।",
        "footer_tagline": "सरकारी कल्याणकारी योजनाओं की स्पष्ट जानकारी से नागरिकों का सशक्तिकरण।",
        "footer_official_sources": "आधिकारिक पोर्टल: myScheme.gov.in | india.gov.in | scholarships.gov.in | pmjay.gov.in",
        "footer_rights": "स्कीमसाथी AI - निःशुल्क सार्वजनिक सेवा मंच।"
    }
}

# -----------------------------------------------------------------------------
# Supabase & Data Access Helpers
# -----------------------------------------------------------------------------
def is_supabase_configured() -> bool:
    """Check if Supabase credentials are provided."""
    return bool(SUPABASE_URL and SUPABASE_KEY and SUPABASE_URL.startswith("http"))

def get_schemes_from_supabase() -> Optional[List[Dict[str, Any]]]:
    """Fetch schemes from Supabase if configured and reachable."""
    if not (is_supabase_configured() and HAS_REQUESTS):
        return None
    try:
        url = f"{SUPABASE_URL}/rest/v1/schemes?select=*"
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json"
        }
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list) and len(data) > 0:
                logger.info(f"Loaded {len(data)} schemes from Supabase.")
                return data
    except Exception as e:
        logger.warning(f"Could not fetch schemes from Supabase: {e}. Falling back to curated dataset.")
    return None

def get_all_schemes() -> List[Dict[str, Any]]:
    """Return all schemes from Supabase if available, otherwise from curated list."""
    sb_schemes = get_schemes_from_supabase()
    if sb_schemes:
        return sb_schemes
    return CURATED_SCHEMES

def find_scheme_by_id(scheme_id: str) -> Optional[Dict[str, Any]]:
    """Look up a scheme by its unique identifier."""
    schemes = get_all_schemes()
    for s in schemes:
        if s.get("id") == scheme_id:
            return s
    return None

# -----------------------------------------------------------------------------
# Eligibility Checking Engine
# -----------------------------------------------------------------------------
def evaluate_scheme_eligibility(profile: Dict[str, Any], scheme: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates a user profile against a scheme's eligibility rules.
    Returns status: 'potentially_eligible', 'more_info_required', or 'likely_not_eligible'
    along with detailed reasons, missing/uncertain criteria, and guidance.
    """
    rules = scheme.get("eligibility_rules", {})
    matching_reasons: List[str] = []
    missing_criteria: List[str] = []
    uncertain_criteria: List[str] = []
    ineligible = False

    user_age = profile.get("age")
    user_state = (profile.get("state") or "").strip()
    user_occupation = (profile.get("occupation") or "any").strip().lower()
    is_student = bool(profile.get("is_student", False))
    annual_income = profile.get("annual_income")
    social_category = (profile.get("social_category") or "All").strip()
    is_farmer = bool(profile.get("is_farmer", False))
    has_disability = bool(profile.get("has_disability", False))
    user_gender = (profile.get("gender") or "all").strip().lower()

    # 1. State / Union Territory Rule
    scheme_state = scheme.get("state", "All India")
    scheme_level = scheme.get("government_level", "Central")
    if scheme_state != "All India":
        if user_state:
            if user_state.lower() == scheme_state.lower():
                matching_reasons.append(f"State match: You reside in {scheme_state}, where this scheme is operational.")
            else:
                ineligible = True
                missing_criteria.append(f"State specific: This scheme is exclusive to residents of {scheme_state}. Your selected state is {user_state}.")
        else:
            uncertain_criteria.append(f"Requires residence in {scheme_state}. Please confirm your state.")
    else:
        matching_reasons.append("Geographic coverage: Open to all Indian citizens across all States and Union Territories.")

    # 2. Age Rule
    min_age = rules.get("min_age")
    max_age = rules.get("max_age")
    if user_age is not None:
        try:
            age_int = int(user_age)
            if min_age is not None and age_int < min_age:
                ineligible = True
                missing_criteria.append(f"Age minimum: Requires at least {min_age} years of age (Your age: {age_int}).")
            elif max_age is not None and age_int > max_age:
                ineligible = True
                missing_criteria.append(f"Age limit: Applicable up to {max_age} years of age (Your age: {age_int}).")
            else:
                matching_reasons.append(f"Age criterion satisfied ({min_age or 0} to {max_age or 'any'} years).")
        except (ValueError, TypeError):
            uncertain_criteria.append("Age could not be verified from input.")
    elif min_age or max_age:
        uncertain_criteria.append(f"Age requirements exist ({min_age or 0} - {max_age or 'any'} years).")

    # 3. Gender Rule
    req_gender = (rules.get("gender") or "all").lower()
    if req_gender != "all":
        if user_gender and user_gender != "all":
            if user_gender == req_gender:
                matching_reasons.append(f"Gender requirement met: Targeted for {req_gender.capitalize()} beneficiaries.")
            else:
                ineligible = True
                missing_criteria.append(f"Gender specific: Targeted specifically for {req_gender.capitalize()} beneficiaries.")
        else:
            uncertain_criteria.append(f"Scheme is targeted towards {req_gender.capitalize()} citizens. Please verify your eligibility.")

    # 4. Student Requirement
    if rules.get("student_only"):
        if is_student or user_occupation == "student":
            matching_reasons.append("Student status: Matches your active student / scholar enrollment.")
        else:
            ineligible = True
            missing_criteria.append("Requires being an enrolled student in a recognized institution.")

    # 5. Farmer / Agricultural Requirement
    if rules.get("farmer_only"):
        if is_farmer or "farmer" in user_occupation:
            matching_reasons.append("Farmer status: Matches your agricultural landholding / farmer background.")
        else:
            ineligible = True
            missing_criteria.append("Requires being a landholding farmer, agricultural cultivator, or tenant cultivator.")

    # 6. Occupation Alignment
    scheme_occupations = [o.lower() for o in rules.get("occupations", ["any"])]
    if "any" not in scheme_occupations and user_occupation:
        if user_occupation in scheme_occupations or (is_farmer and "farmer" in scheme_occupations) or (is_student and "student" in scheme_occupations):
            matching_reasons.append(f"Occupation alignment: Suited for {user_occupation.replace('-', ' ').title()}.")
        else:
            # Not an automatic disqualifier for some schemes, but noted as uncertain
            uncertain_criteria.append(f"Primary intended occupations: {', '.join([o.title() for o in scheme_occupations])}.")

    # 7. Income Ceiling Rule
    max_income = rules.get("max_income")
    if max_income is not None:
        if annual_income is not None:
            try:
                income_val = float(annual_income)
                if income_val > max_income:
                    ineligible = True
                    missing_criteria.append(f"Income threshold: Family annual income limit is ₹{max_income:,.0f}. Provided income: ₹{income_val:,.0f}.")
                else:
                    matching_reasons.append(f"Income criterion met: Family annual income is within the ₹{max_income:,.0f} limit.")
            except (ValueError, TypeError):
                uncertain_criteria.append(f"Income verification needed (Threshold: ₹{max_income:,.0f}/year).")
        else:
            uncertain_criteria.append(f"Income ceiling applies: Up to ₹{max_income:,.0f}/year. Please check your family income certificate.")

    # 8. Disability Focus
    if scheme.get("category") == "Disability support":
        if has_disability:
            matching_reasons.append("Disability criterion: Matches your indicated disability status.")
        else:
            uncertain_criteria.append("This scheme is intended for individuals with certified benchmark disabilities (PwD/UDID).")

    # 9. Social Category Quota (SC / ST / OBC / EWS)
    req_categories = rules.get("categories", ["All"])
    if "All" not in req_categories:
        if social_category and social_category != "All":
            if social_category in req_categories:
                matching_reasons.append(f"Category alignment: Matches reserved scheme group ({social_category}).")
            else:
                uncertain_criteria.append(f"Special reservation/target group: {', '.join(req_categories)}. You indicated: {social_category}.")
        else:
            uncertain_criteria.append(f"Specific social categories targeted: {', '.join(req_categories)}.")

    # Determine Overall Result
    if ineligible:
        status = "likely_not_eligible"
        status_label = "Likely Not Eligible"
    elif uncertain_criteria and len(matching_reasons) < 2:
        status = "more_info_required"
        status_label = "More Information Required"
    else:
        status = "potentially_eligible"
        status_label = "Potentially Eligible"

    return {
        "scheme_id": scheme.get("id"),
        "scheme_name": scheme.get("name"),
        "category": scheme.get("category"),
        "government_level": scheme.get("government_level"),
        "state": scheme.get("state"),
        "status": status,
        "status_label": status_label,
        "benefits": scheme.get("benefits"),
        "official_url": scheme.get("official_url"),
        "required_documents": scheme.get("required_documents", []),
        "matching_reasons": matching_reasons,
        "missing_criteria": missing_criteria,
        "uncertain_criteria": uncertain_criteria,
        "disclaimer": "This evaluation is indicative. Final eligibility and approval rests with the respective government department."
    }

# -----------------------------------------------------------------------------
# AI Assistant Engine (Live LLM with Intelligent Rule-Based Fallback)
# -----------------------------------------------------------------------------
def run_rule_based_assistant(question: str, history: List[Dict[str, str]], language: str = "en") -> Dict[str, Any]:
    """
    Intelligent, grounded assistant using the local verified scheme database.
    Activates when no external AI key is configured or when the external API fails.
    """
    q_lower = question.lower()
    schemes = get_all_schemes()
    matched_schemes: List[Dict[str, Any]] = []

    # Keyword mappings
    keyword_map = {
        "farmer": ["Farmers and agriculture", "pm-kisan", "rythu-bharosa-ap"],
        "kisan": ["Farmers and agriculture", "pm-kisan", "rythu-bharosa-ap"],
        "agriculture": ["Farmers and agriculture", "pm-kisan"],
        "scholarship": ["Scholarships", "nsp-post-matric", "nmms-scholarship"],
        "student": ["Students and education", "Scholarships", "nsp-post-matric", "nmms-scholarship", "yuva-nidhi-karnataka"],
        "education": ["Students and education", "Scholarships"],
        "health": ["Health and healthcare", "pmjay-ayushman"],
        "hospital": ["Health and healthcare", "pmjay-ayushman"],
        "ayushman": ["pmjay-ayushman"],
        "card": ["pmjay-ayushman", "pm-vishwakarma"],
        "house": ["Housing", "pmay-urban"],
        "housing": ["Housing", "pmay-urban"],
        "awas": ["pmay-urban"],
        "loan": ["Small businesses", "pm-mudra", "pm-svanidhi", "stand-up-india", "pm-vishwakarma"],
        "mudra": ["pm-mudra"],
        "business": ["Small businesses", "pm-mudra", "stand-up-india", "pm-vishwakarma"],
        "vendor": ["pm-svanidhi"],
        "street": ["pm-svanidhi"],
        "women": ["Women and children", "sukanya-samriddhi", "pm-matru-vandana", "kalaignar-magalir-tn", "ladli-behna-mp"],
        "girl": ["sukanya-samriddhi", "Women and children"],
        "sukanya": ["sukanya-samriddhi"],
        "maternity": ["pm-matru-vandana"],
        "pension": ["Senior citizens", "atal-pension-yojana", "ignao-pension", "igndp-pension"],
        "elderly": ["Senior citizens", "ignao-pension", "atal-pension-yojana"],
        "senior": ["Senior citizens", "ignao-pension", "atal-pension-yojana"],
        "disability": ["Disability support", "igndp-pension"],
        "handicap": ["Disability support", "igndp-pension"],
        "divyang": ["Disability support", "igndp-pension"],
        "andhra": ["rythu-bharosa-ap"],
        "tamil": ["kalaignar-magalir-tn"],
        "madhya": ["ladli-behna-mp"],
        "karnataka": ["yuva-nidhi-karnataka"],
        "vishwakarma": ["pm-vishwakarma"],
        "artisan": ["pm-vishwakarma"]
    }

    # Match based on keywords or exact scheme names
    matched_ids = set()
    for kw, targets in keyword_map.items():
        if kw in q_lower:
            for t in targets:
                for s in schemes:
                    if s["id"] == t or s["category"] == t or kw in s["name"].lower():
                        matched_ids.add(s["id"])

    # Fallback to search through text if no keyword matched
    if not matched_ids:
        for s in schemes:
            searchable_text = f"{s['name']} {s['category']} {s['short_description']} {s['state']}".lower()
            tokens = [t for t in re.split(r"\W+", q_lower) if len(t) > 3]
            if any(tok in searchable_text for tok in tokens):
                matched_ids.add(s["id"])

    matched_schemes = [s for s in schemes if s["id"] in matched_ids][:3]
    if not matched_schemes:
        matched_schemes = schemes[:2]  # Show featured schemes if query is general

    # Build response in selected language
    if language == "te":
        greeting = "నమస్కారం! మీ ప్రశ్నకు సంబంధించిన ధృవీకరించబడిన ప్రభుత్వ పథకాల వివరాలు ఇక్కడ ఉన్నాయి:\n\n"
        mode_note = "\n\n*(గమనిక: ఇది స్థానిక పథకాల డేటాబేస్ నుండి రూపొందించబడిన సమాధానం. ముఖ్యమైన వివరాలను అధికారిక ప్రభుత్వ పోర్టల్‌లో సరిచూసుకోండి.)*"
    elif language == "hi":
        greeting = "नमस्ते! आपके प्रश्न के आधार पर सत्यापित सरकारी योजनाओं की जानकारी नीचे दी गई है:\n\n"
        mode_note = "\n\n*(नोट: यह उत्तर हमारे सत्यापित स्थानीय डेटाबेस से तैयार किया गया है। कृपया आधिकारिक सरकारी पोर्टल पर भी विवरण जांचें।)*"
    else:
        greeting = "Namaste! Here are verified government schemes that address your query:\n\n"
        mode_note = "\n\n*(Note: Generated via SchemeSathi Knowledge Engine using our curated database. Always verify final requirements on official government portals.)*"

    body_parts = []
    for s in matched_schemes:
        docs_list = ", ".join(s.get("required_documents", [])[:3])
        item_text = (
            f"### **{s['name']}** ({s['government_level']} Government)\n"
            f"- **Benefits**: {s['benefits']}\n"
            f"- **Eligibility**: {s['eligibility_summary']}\n"
            f"- **Key Documents**: {docs_list}\n"
            f"- **Official Portal**: [{s['official_url']}]({s['official_url']})\n"
        )
        body_parts.append(item_text)

    response_text = greeting + "\n".join(body_parts) + mode_note
    return {
        "reply": response_text,
        "engine": "rule_based",
        "matched_schemes": [s["name"] for s in matched_schemes],
        "is_ai_live": False
    }

def run_external_ai_assistant(question: str, history: List[Dict[str, str]], language: str = "en") -> Dict[str, Any]:
    """
    Connects to external AI (OpenAI or Gemini) using the API key from environment.
    Falls back gracefully to the rule-based assistant if key is missing or call fails.
    """
    if not AI_API_KEY or not HAS_REQUESTS:
        return run_rule_based_assistant(question, history, language)

    # Build context from curated scheme database
    schemes = get_all_schemes()
    context_summary = []
    for s in schemes:
        context_summary.append(
            f"Scheme: {s['name']}\n"
            f"Category: {s['category']} | Level: {s['government_level']} | State: {s['state']}\n"
            f"Benefits: {s['benefits']}\n"
            f"Eligibility: {s['eligibility_summary']}\n"
            f"Documents: {', '.join(s.get('required_documents', []))}\n"
            f"Official Link: {s['official_url']}\n"
        )
    context_str = "\n---\n".join(context_summary)

    lang_instruction = "Respond in English."
    if language == "te":
        lang_instruction = "Respond in clear, natural Telugu (తెలుగు). Keep official scheme names and portal URLs recognizable."
    elif language == "hi":
        lang_instruction = "Respond in clear, natural Hindi (हिन्दी). Keep official scheme names and portal URLs recognizable."

    system_prompt = (
        "You are SchemeSathi AI, an expert, empathetic, and neutral guide to Indian Central and State Government schemes.\n"
        "Your mission is to help Indian citizens discover schemes, understand eligibility, know required documents, and find official links.\n"
        "GUIDELINES:\n"
        "1. Prioritize verified Indian government schemes from the provided context.\n"
        "2. Never fabricate scheme names, benefits, deadlines, or non-existent government websites.\n"
        "3. Always mention that final eligibility rests with the respective government department, not this AI.\n"
        "4. Include official .gov.in / .nic.in URLs when mentioning schemes.\n"
        "5. Explain requirements in simple, structured bullet points.\n"
        f"6. {lang_instruction}\n\n"
        f"VERIFIED SCHEMES DATABASE CONTEXT:\n{context_str}"
    )

    # Attempt Google Gemini API or OpenAI API
    try:
        # Check if Google Gemini Key
        if GEMINI_API_KEY or "gemini" in AI_MODEL.lower():
            gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/{AI_MODEL}:generateContent?key={AI_API_KEY}"
            contents = []
            contents.append({"role": "user", "parts": [{"text": f"System context:\n{system_prompt}\n\nUser Question: {question}"}]})

            payload = {
                "contents": contents,
                "generationConfig": {
                    "temperature": 0.3,
                    "maxOutputTokens": 800
                }
            }
            resp = requests.post(gemini_url, json=payload, timeout=12)
            if resp.status_code == 200:
                data = resp.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                return {
                    "reply": text,
                    "engine": "gemini_api",
                    "model": AI_MODEL,
                    "is_ai_live": True
                }
            else:
                logger.warning(f"Gemini API returned status {resp.status_code}: {resp.text[:200]}. Falling back.")
        
        # Check OpenAI compatible endpoint
        if OPENAI_API_KEY or AI_PROVIDER == "openai":
            openai_url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {AI_API_KEY}",
                "Content-Type": "application/json"
            }
            messages = [{"role": "system", "content": system_prompt}]
            for h in history[-4:]:
                if h.get("role") and h.get("content"):
                    messages.append({"role": h["role"], "content": h["content"]})
            messages.append({"role": "user", "content": question})

            payload = {
                "model": AI_MODEL if not "gemini" in AI_MODEL else "gpt-3.5-turbo",
                "messages": messages,
                "temperature": 0.3,
                "max_tokens": 800
            }
            resp = requests.post(openai_url, headers=headers, json=payload, timeout=12)
            if resp.status_code == 200:
                data = resp.json()
                text = data["choices"][0]["message"]["content"]
                return {
                    "reply": text,
                    "engine": "openai_api",
                    "model": payload["model"],
                    "is_ai_live": True
                }
            else:
                logger.warning(f"OpenAI API returned status {resp.status_code}: {resp.text[:200]}. Falling back.")
    except Exception as e:
        logger.warning(f"External AI request failed: {e}. Executing rule-based assistant fallback.")

    return run_rule_based_assistant(question, history, language)

# -----------------------------------------------------------------------------
# REST API Endpoints
# -----------------------------------------------------------------------------
@app.route("/api/health", methods=["GET"])
def api_health():
    """Application health and runtime status."""
    return jsonify({
        "status": "healthy",
        "app": APP_NAME,
        "version": APP_VERSION,
        "database_status": "connected (supabase)" if is_supabase_configured() else "demo_mode (curated local dataset)",
        "ai_status": "live_api" if bool(AI_API_KEY) else "rule_based_engine (fallback active)",
        "schemes_count": len(get_all_schemes()),
        "timestamp": int(time.time())
    })

@app.route("/api/config", methods=["GET"])
def api_config():
    """Safe public configuration without exposing any keys or secrets."""
    return jsonify({
        "app_name": APP_NAME,
        "tagline": APP_TAGLINE,
        "version": APP_VERSION,
        "supported_languages": ["en", "te", "hi"],
        "demo_mode": not is_supabase_configured(),
        "ai_live_enabled": bool(AI_API_KEY),
        "total_schemes": len(get_all_schemes()),
        "categories_count": len(CATEGORIES),
        "states_count": len(INDIAN_STATES)
    })

@app.route("/api/categories", methods=["GET"])
def api_categories():
    """Return available scheme categories with counts."""
    schemes = get_all_schemes()
    cat_counts: Dict[str, int] = {}
    for c in CATEGORIES:
        cat_counts[c] = 0
    for s in schemes:
        cat = s.get("category")
        if cat:
            cat_counts[cat] = cat_counts.get(cat, 0) + 1
    result = [{"name": c, "count": cat_counts.get(c, 0)} for c in CATEGORIES]
    return jsonify(result)

@app.route("/api/states", methods=["GET"])
def api_states():
    """Return available Indian States and Union Territories."""
    return jsonify({
        "all_india": "All India",
        "states": INDIAN_STATES
    })

@app.route("/api/schemes", methods=["GET"])
def api_schemes():
    """
    Search and filter schemes with support for:
    - q / search: Keyword query across name, description, benefits, documents
    - category: Filter by category name
    - state: Filter by state or 'All India'
    - level: Filter by 'Central' or 'State'
    - sort: 'relevance', 'name_asc', 'name_desc'
    - page: Page number (1-indexed)
    - limit: Items per page (default 20)
    """
    query = request.args.get("q", "").strip().lower()
    category = request.args.get("category", "").strip()
    state = request.args.get("state", "").strip()
    level = request.args.get("level", "").strip()
    sort_by = request.args.get("sort", "relevance").strip()
    page = max(1, int(request.args.get("page", 1)))
    limit = min(50, max(1, int(request.args.get("limit", 20))))

    schemes = get_all_schemes()
    filtered: List[Dict[str, Any]] = []

    for s in schemes:
        # Category filter
        if category and category.lower() != "all" and s.get("category", "").lower() != category.lower():
            continue

        # Level filter (Central vs State)
        if level and level.lower() != "all" and s.get("government_level", "").lower() != level.lower():
            continue

        # State filter
        if state and state.lower() != "all" and state.lower() != "all india":
            s_state = s.get("state", "All India")
            if s_state != "All India" and s_state.lower() != state.lower():
                continue

        # Search Query filter
        if query:
            searchable = (
                f"{s.get('name', '')} {s.get('short_description', '')} "
                f"{s.get('detailed_description', '')} {s.get('category', '')} "
                f"{s.get('state', '')} {' '.join(s.get('required_documents', []))}"
            ).lower()
            tokens = [t for t in re.split(r"\W+", query) if t]
            if not any(token in searchable for token in tokens):
                continue

        filtered.append(s)

    # Sorting
    if sort_by == "name_asc":
        filtered.sort(key=lambda x: x.get("name", "").lower())
    elif sort_by == "name_desc":
        filtered.sort(key=lambda x: x.get("name", "").lower(), reverse=True)

    # Pagination
    total = len(filtered)
    start_idx = (page - 1) * limit
    paginated = filtered[start_idx:start_idx + limit]

    return jsonify({
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit if total > 0 else 1,
        "schemes": paginated
    })

@app.route("/api/schemes/<scheme_id>", methods=["GET"])
def api_scheme_detail(scheme_id: str):
    """Retrieve full details for a single government scheme."""
    scheme = find_scheme_by_id(scheme_id)
    if not scheme:
        return jsonify({"error": "Scheme not found", "scheme_id": scheme_id}), 404
    return jsonify(scheme)

@app.route("/api/eligibility", methods=["POST"])
def api_eligibility():
    """
    Backend eligibility evaluation. Accepts user profile data and
    evaluates all available schemes against structured rules.
    """
    if not request.is_json:
        return jsonify({"error": "Request body must be valid JSON"}), 400

    profile = request.get_json()
    if not isinstance(profile, dict):
        return jsonify({"error": "Invalid payload format"}), 400

    # Input validation
    age = profile.get("age")
    if age is not None:
        try:
            age = int(age)
            if age < 0 or age > 130:
                return jsonify({"error": "Age must be between 0 and 130"}), 400
            profile["age"] = age
        except (ValueError, TypeError):
            return jsonify({"error": "Age must be an integer"}), 400

    income = profile.get("annual_income")
    if income is not None and income != "":
        try:
            income = float(income)
            if income < 0:
                return jsonify({"error": "Annual income cannot be negative"}), 400
            profile["annual_income"] = income
        except (ValueError, TypeError):
            return jsonify({"error": "Annual income must be a valid number"}), 400

    schemes = get_all_schemes()
    evaluations: List[Dict[str, Any]] = []

    for s in schemes:
        res = evaluate_scheme_eligibility(profile, s)
        evaluations.append(res)

    # Group results
    eligible = [e for e in evaluations if e["status"] == "potentially_eligible"]
    review = [e for e in evaluations if e["status"] == "more_info_required"]
    ineligible = [e for e in evaluations if e["status"] == "likely_not_eligible"]

    return jsonify({
        "summary": {
            "total_evaluated": len(evaluations),
            "potentially_eligible_count": len(eligible),
            "more_info_required_count": len(review),
            "likely_not_eligible_count": len(ineligible)
        },
        "potentially_eligible": eligible,
        "more_info_required": review,
        "likely_not_eligible": ineligible,
        "disclaimer": "This is an automated indicative assessment based on publicly stated rules. Final decision is made by the competent government authority."
    })

@app.route("/api/chat", methods=["POST"])
def api_chat():
    """
    SchemeSathi AI Chat Endpoint.
    Accepts question, session history, and chosen language.
    """
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    question = (data.get("question") or "").strip()
    if not question:
        return jsonify({"error": "Question cannot be empty"}), 400

    if len(question) > 1000:
        return jsonify({"error": "Question too long (max 1000 characters)"}), 400

    history = data.get("history", [])
    if not isinstance(history, list):
        history = []

    language = data.get("language", "en")
    if language not in ["en", "te", "hi"]:
        language = "en"

    assistant_result = run_external_ai_assistant(question, history, language)
    return jsonify(assistant_result)

# -----------------------------------------------------------------------------
# Embedded Complete Single-Page Application (HTML, CSS, JS)
# -----------------------------------------------------------------------------
HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SchemeSathi AI - Your Guide to Government Schemes</title>
  <meta name="description" content="Discover Indian central and state government schemes, check eligibility, explore required documents, and get official application links.">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
  
  <style>
    :root {
      --primary: #0f2744;
      --primary-light: #1e3e62;
      --primary-dark: #09182b;
      --teal: #0d9488;
      --teal-light: #14b8a6;
      --teal-dark: #0f766e;
      --accent: #f97316;
      --accent-light: #ffedd5;
      --bg: #f8fafc;
      --card-bg: #ffffff;
      --text: #1e293b;
      --text-muted: #64748b;
      --border: #e2e8f0;
      --border-focus: #0d9488;
      --success: #15803d;
      --success-bg: #dcfce7;
      --warning: #b45309;
      --warning-bg: #fef3c7;
      --danger: #b91c1c;
      --danger-bg: #fee2e2;
      --radius-sm: 6px;
      --radius: 10px;
      --radius-lg: 16px;
      --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
      --shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
      --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);
      --font: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: var(--font);
      background-color: var(--bg);
      color: var(--text);
      line-height: 1.6;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }

    /* Container */
    .container {
      max-width: 1200px;
      margin: 0 auto;
      padding: 0 1.25rem;
      width: 100%;
    }

    /* Navigation Bar */
    header.site-header {
      background-color: var(--primary);
      color: #ffffff;
      position: sticky;
      top: 0;
      z-index: 1000;
      box-shadow: 0 2px 8px rgba(0,0,0,0.15);
    }
    .nav-wrapper {
      display: flex;
      align-items: center;
      justify-content: space-between;
      height: 70px;
    }
    .brand-logo {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      text-decoration: none;
      color: #ffffff;
    }
    .brand-logo svg {
      width: 32px;
      height: 32px;
      fill: var(--teal-light);
    }
    .brand-text h1 {
      font-size: 1.25rem;
      font-weight: 800;
      letter-spacing: -0.02em;
      line-height: 1.1;
    }
    .brand-text span {
      font-size: 0.7rem;
      color: #94a3b8;
      display: block;
      letter-spacing: 0.05em;
      text-transform: uppercase;
    }
    nav.nav-links {
      display: flex;
      align-items: center;
      gap: 1.5rem;
    }
    nav.nav-links a {
      color: #cbd5e1;
      text-decoration: none;
      font-size: 0.9rem;
      font-weight: 500;
      padding: 0.5rem 0.25rem;
      transition: color 0.2s, border-color 0.2s;
      border-bottom: 2px solid transparent;
      cursor: pointer;
    }
    nav.nav-links a:hover, nav.nav-links a.active {
      color: #ffffff;
      border-color: var(--teal-light);
    }
    .nav-actions {
      display: flex;
      align-items: center;
      gap: 1rem;
    }
    .lang-selector {
      background-color: rgba(255, 255, 255, 0.1);
      border: 1px solid rgba(255, 255, 255, 0.2);
      color: #ffffff;
      padding: 0.35rem 0.65rem;
      border-radius: var(--radius-sm);
      font-size: 0.85rem;
      font-weight: 500;
      cursor: pointer;
      outline: none;
    }
    .lang-selector option {
      background: var(--primary);
      color: #ffffff;
    }
    .saved-badge-btn {
      position: relative;
      background: rgba(255,255,255,0.12);
      border: 1px solid rgba(255,255,255,0.25);
      color: #ffffff;
      padding: 0.4rem 0.85rem;
      border-radius: var(--radius-sm);
      font-size: 0.85rem;
      font-weight: 500;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 0.4rem;
      transition: background 0.2s;
    }
    .saved-badge-btn:hover {
      background: rgba(255,255,255,0.2);
    }
    .badge-count {
      background: var(--accent);
      color: #ffffff;
      font-size: 0.7rem;
      font-weight: 700;
      padding: 2px 6px;
      border-radius: 999px;
    }
    .mobile-menu-toggle {
      display: none;
      background: none;
      border: none;
      color: #ffffff;
      font-size: 1.5rem;
      cursor: pointer;
    }

    /* Hero Section */
    .hero-section {
      background: linear-gradient(135deg, var(--primary) 0%, #17385c 60%, #0d4a58 100%);
      color: #ffffff;
      padding: 3.5rem 0 3rem;
      text-align: center;
      position: relative;
    }
    .hero-badge {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      background: rgba(255, 255, 255, 0.1);
      backdrop-filter: blur(8px);
      border: 1px solid rgba(255, 255, 255, 0.2);
      padding: 0.35rem 1rem;
      border-radius: 999px;
      font-size: 0.8rem;
      font-weight: 600;
      color: #99f6e4;
      margin-bottom: 1.25rem;
    }
    .hero-title {
      font-size: 2.5rem;
      font-weight: 800;
      letter-spacing: -0.03em;
      line-height: 1.2;
      max-width: 850px;
      margin: 0 auto 1rem;
    }
    .hero-subtitle {
      font-size: 1.05rem;
      color: #cbd5e1;
      max-width: 700px;
      margin: 0 auto 2rem;
      line-height: 1.6;
    }

    /* Hero Search Bar */
    .hero-search-box {
      max-width: 680px;
      margin: 0 auto 2.5rem;
      display: flex;
      background: #ffffff;
      border-radius: var(--radius);
      padding: 0.35rem;
      box-shadow: var(--shadow-lg);
    }
    .hero-search-box input {
      flex: 1;
      border: none;
      padding: 0.85rem 1.25rem;
      font-size: 1rem;
      color: var(--text);
      outline: none;
      border-radius: var(--radius) 0 0 var(--radius);
      font-family: inherit;
    }
    .hero-search-box button {
      background: var(--teal);
      color: #ffffff;
      border: none;
      padding: 0.85rem 1.5rem;
      font-size: 0.95rem;
      font-weight: 600;
      border-radius: var(--radius);
      cursor: pointer;
      transition: background 0.2s;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }
    .hero-search-box button:hover {
      background: var(--teal-dark);
    }

    /* Hero Stats */
    .hero-stats {
      display: flex;
      justify-content: center;
      gap: 2.5rem;
      flex-wrap: wrap;
    }
    .stat-item {
      text-align: center;
    }
    .stat-number {
      font-size: 1.6rem;
      font-weight: 800;
      color: #38bdf8;
    }
    .stat-label {
      font-size: 0.8rem;
      color: #94a3b8;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    /* Quick Category Pills */
    .category-pills {
      display: flex;
      gap: 0.5rem;
      justify-content: center;
      flex-wrap: wrap;
      margin-bottom: 2rem;
    }
    .cat-pill {
      background: #ffffff;
      border: 1px solid var(--border);
      color: var(--text);
      padding: 0.45rem 0.9rem;
      border-radius: 999px;
      font-size: 0.825rem;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.2s;
    }
    .cat-pill:hover, .cat-pill.active {
      background: var(--teal);
      color: #ffffff;
      border-color: var(--teal);
    }

    /* Main Tab Navigation */
    .tab-nav {
      background: #ffffff;
      border-bottom: 1px solid var(--border);
      position: sticky;
      top: 70px;
      z-index: 900;
      box-shadow: var(--shadow-sm);
    }
    .tab-list {
      display: flex;
      gap: 1rem;
      overflow-x: auto;
      padding: 0.5rem 0;
    }
    .tab-btn {
      background: none;
      border: none;
      padding: 0.65rem 1rem;
      font-size: 0.9rem;
      font-weight: 600;
      color: var(--text-muted);
      cursor: pointer;
      border-radius: var(--radius-sm);
      white-space: nowrap;
      transition: all 0.2s;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }
    .tab-btn:hover {
      color: var(--primary);
      background: #f1f5f9;
    }
    .tab-btn.active {
      color: var(--teal-dark);
      background: #ccfbf1;
    }

    /* Section Containers */
    .view-section {
      display: none;
      padding: 2.5rem 0 3.5rem;
    }
    .view-section.active {
      display: block;
    }

    /* Explore Section Filter Toolbar */
    .filter-toolbar {
      background: #ffffff;
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 1.25rem;
      margin-bottom: 2rem;
      box-shadow: var(--shadow-sm);
    }
    .filter-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 1rem;
      align-items: end;
    }
    .form-group {
      display: flex;
      flex-direction: column;
      gap: 0.4rem;
    }
    .form-group label {
      font-size: 0.8rem;
      font-weight: 600;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }
    .form-control {
      width: 100%;
      padding: 0.6rem 0.85rem;
      border: 1px solid var(--border);
      border-radius: var(--radius-sm);
      font-size: 0.9rem;
      color: var(--text);
      background: #ffffff;
      outline: none;
      font-family: inherit;
    }
    .form-control:focus {
      border-color: var(--teal);
      box-shadow: 0 0 0 3px rgba(13, 148, 136, 0.15);
    }
    .toolbar-actions {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-top: 1rem;
      padding-top: 1rem;
      border-top: 1px solid var(--border);
    }
    .results-badge {
      font-size: 0.9rem;
      font-weight: 600;
      color: var(--text-muted);
    }
    .btn-clear-filter {
      background: none;
      border: 1px solid var(--border);
      color: var(--text-muted);
      padding: 0.4rem 0.85rem;
      border-radius: var(--radius-sm);
      font-size: 0.85rem;
      font-weight: 500;
      cursor: pointer;
    }
    .btn-clear-filter:hover {
      background: #f1f5f9;
      color: var(--text);
    }

    /* Scheme Cards Grid */
    .schemes-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
      gap: 1.5rem;
    }
    .scheme-card {
      background: #ffffff;
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 1.5rem;
      box-shadow: var(--shadow-sm);
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      transition: transform 0.2s, box-shadow 0.2s;
      position: relative;
    }
    .scheme-card:hover {
      transform: translateY(-3px);
      box-shadow: var(--shadow);
      border-color: #cbd5e1;
    }
    .card-top {
      margin-bottom: 1rem;
    }
    .card-badges {
      display: flex;
      gap: 0.4rem;
      flex-wrap: wrap;
      margin-bottom: 0.75rem;
    }
    .badge {
      font-size: 0.7rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      padding: 0.2rem 0.55rem;
      border-radius: 999px;
    }
    .badge-central {
      background: #dbeafe;
      color: #1e40af;
    }
    .badge-state {
      background: #fef3c7;
      color: #92400e;
    }
    .badge-category {
      background: #f1f5f9;
      color: #475569;
    }
    .badge-verified {
      background: #dcfce7;
      color: #166534;
      display: inline-flex;
      align-items: center;
      gap: 3px;
    }
    .scheme-title {
      font-size: 1.15rem;
      font-weight: 700;
      color: var(--primary);
      margin-bottom: 0.5rem;
      line-height: 1.35;
    }
    .scheme-desc {
      font-size: 0.875rem;
      color: #475569;
      margin-bottom: 1rem;
      line-height: 1.5;
    }
    .scheme-snippet {
      background: #f8fafc;
      border-left: 3px solid var(--teal);
      padding: 0.65rem 0.85rem;
      border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
      margin-bottom: 1.25rem;
    }
    .snippet-label {
      font-size: 0.7rem;
      font-weight: 700;
      text-transform: uppercase;
      color: var(--teal-dark);
      margin-bottom: 0.15rem;
    }
    .snippet-val {
      font-size: 0.825rem;
      color: var(--text);
      font-weight: 500;
    }
    .card-footer {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 0.5rem;
      padding-top: 1rem;
      border-top: 1px solid #f1f5f9;
    }
    .btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 0.4rem;
      padding: 0.55rem 1rem;
      border-radius: var(--radius-sm);
      font-size: 0.85rem;
      font-weight: 600;
      cursor: pointer;
      text-decoration: none;
      transition: all 0.2s;
      border: none;
    }
    .btn-primary {
      background: var(--teal);
      color: #ffffff;
    }
    .btn-primary:hover {
      background: var(--teal-dark);
    }
    .btn-outline {
      background: #ffffff;
      border: 1px solid var(--border);
      color: var(--text);
    }
    .btn-outline:hover {
      background: #f8fafc;
      border-color: #cbd5e1;
    }
    .btn-save-icon {
      background: none;
      border: 1px solid var(--border);
      color: #64748b;
      padding: 0.5rem;
      border-radius: var(--radius-sm);
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: all 0.2s;
    }
    .btn-save-icon:hover {
      color: #e11d48;
      border-color: #fca5a5;
    }
    .btn-save-icon.saved {
      color: #e11d48;
      background: #ffe4e6;
      border-color: #f43f5e;
    }

    /* Eligibility Checker Form */
    .checker-layout {
      display: grid;
      grid-template-columns: 1fr 1.1fr;
      gap: 2rem;
      align-items: start;
    }
    .checker-card {
      background: #ffffff;
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 2rem;
      box-shadow: var(--shadow);
    }
    .checker-header {
      margin-bottom: 1.5rem;
    }
    .checker-header h2 {
      font-size: 1.5rem;
      font-weight: 800;
      color: var(--primary);
      margin-bottom: 0.5rem;
    }
    .checker-header p {
      font-size: 0.875rem;
      color: var(--text-muted);
    }
    .checker-form {
      display: flex;
      flex-direction: column;
      gap: 1.25rem;
    }
    .form-row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1rem;
    }
    .toggle-group {
      display: flex;
      gap: 1.5rem;
      align-items: center;
    }
    .toggle-label {
      font-size: 0.9rem;
      color: var(--text);
      font-weight: 500;
    }
    .toggle-btn {
      position: relative;
      width: 48px;
      height: 26px;
      background: #cbd5e1;
      border-radius: 999px;
      cursor: pointer;
      transition: background 0.2s;
    }
    .toggle-btn.active {
      background: var(--teal);
    }
    .toggle-knob {
      position: absolute;
      top: 3px;
      left: 3px;
      width: 20px;
      height: 20px;
      background: #ffffff;
      border-radius: 50%;
      transition: transform 0.2s;
    }
    .toggle-btn.active .toggle-knob {
      transform: translateX(22px);
    }
    .checker-results {
      background: #ffffff;
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 2rem;
      box-shadow: var(--shadow);
    }
    .eligibility-category-block {
      margin-bottom: 2rem;
    }
    .eligibility-category-header {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 1.1rem;
      font-weight: 700;
      margin-bottom: 1rem;
      padding-bottom: 0.5rem;
      border-bottom: 2px solid var(--border);
    }
    .status-badge-lg {
      display: inline-block;
      font-size: 0.75rem;
      font-weight: 700;
      padding: 0.25rem 0.75rem;
      border-radius: 999px;
      text-transform: uppercase;
    }
    .status-eligible { background: var(--success-bg); color: var(--success); }
    .status-review { background: var(--warning-bg); color: var(--warning); }
    .status-ineligible { background: var(--danger-bg); color: var(--danger); }

    .result-item-card {
      background: #f8fafc;
      border: 1px solid var(--border);
      border-radius: var(--radius-sm);
      padding: 1.25rem;
      margin-bottom: 1rem;
    }
    .result-item-title {
      font-size: 1rem;
      font-weight: 700;
      color: var(--primary);
      margin-bottom: 0.4rem;
    }
    .reason-list {
      list-style-type: none;
      margin: 0.75rem 0;
      font-size: 0.825rem;
    }
    .reason-list li {
      padding: 0.2rem 0;
      display: flex;
      align-items: flex-start;
      gap: 0.5rem;
    }
    .reason-list li.match { color: var(--success); }
    .reason-list li.missing { color: var(--danger); }
    .reason-list li.uncertain { color: var(--warning); }

    /* AI Assistant Interface */
    .assistant-layout {
      max-width: 850px;
      margin: 0 auto;
      background: #ffffff;
      border: 1px solid var(--border);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      display: flex;
      flex-direction: column;
      height: 680px;
      overflow: hidden;
    }
    .assistant-topbar {
      background: var(--primary);
      color: #ffffff;
      padding: 1rem 1.5rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .assistant-info h3 {
      font-size: 1.1rem;
      font-weight: 700;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }
    .assistant-mode-pill {
      font-size: 0.7rem;
      font-weight: 600;
      background: rgba(255,255,255,0.15);
      padding: 0.2rem 0.6rem;
      border-radius: 999px;
      color: #99f6e4;
    }
    .assistant-messages {
      flex: 1;
      padding: 1.5rem;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 1.25rem;
      background: #f8fafc;
    }
    .message-bubble {
      max-width: 85%;
      padding: 1rem 1.25rem;
      border-radius: var(--radius);
      font-size: 0.9rem;
      line-height: 1.5;
    }
    .message-user {
      align-self: flex-end;
      background: var(--primary-light);
      color: #ffffff;
      border-bottom-right-radius: 2px;
    }
    .message-assistant {
      align-self: flex-start;
      background: #ffffff;
      color: var(--text);
      border: 1px solid var(--border);
      border-bottom-left-radius: 2px;
      box-shadow: var(--shadow-sm);
    }
    .message-assistant a {
      color: var(--teal-dark);
      font-weight: 600;
      word-break: break-all;
    }
    .message-assistant ul, .message-assistant ol {
      margin-left: 1.25rem;
      margin-top: 0.5rem;
    }
    .message-assistant h3 {
      font-size: 0.95rem;
      margin: 0.5rem 0 0.25rem;
      color: var(--primary);
    }
    .suggested-chips {
      padding: 0.75rem 1.5rem;
      background: #ffffff;
      border-top: 1px solid var(--border);
      display: flex;
      gap: 0.5rem;
      overflow-x: auto;
    }
    .prompt-chip {
      background: #f1f5f9;
      border: 1px solid var(--border);
      padding: 0.35rem 0.75rem;
      border-radius: 999px;
      font-size: 0.75rem;
      font-weight: 500;
      color: #475569;
      cursor: pointer;
      white-space: nowrap;
      transition: all 0.2s;
    }
    .prompt-chip:hover {
      background: #e2e8f0;
      color: var(--primary);
    }
    .chat-input-bar {
      padding: 1rem 1.5rem;
      background: #ffffff;
      border-top: 1px solid var(--border);
      display: flex;
      gap: 0.75rem;
    }
    .chat-input-bar input {
      flex: 1;
      padding: 0.75rem 1rem;
      border: 1px solid var(--border);
      border-radius: var(--radius-sm);
      font-size: 0.95rem;
      outline: none;
      font-family: inherit;
    }
    .chat-input-bar input:focus {
      border-color: var(--teal);
    }

    /* Saved Schemes View */
    .saved-schemes-card {
      background: #ffffff;
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 2rem;
      box-shadow: var(--shadow);
    }
    .saved-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 2rem;
      padding-bottom: 1rem;
      border-bottom: 1px solid var(--border);
    }

    /* Modal / Dialog */
    .modal-backdrop {
      display: none;
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(15, 23, 42, 0.7);
      backdrop-filter: blur(4px);
      z-index: 2000;
      align-items: center;
      justify-content: center;
      padding: 1rem;
    }
    .modal-backdrop.active {
      display: flex;
    }
    .modal-content {
      background: #ffffff;
      border-radius: var(--radius);
      width: 100%;
      max-width: 750px;
      max-height: 90vh;
      display: flex;
      flex-direction: column;
      box-shadow: var(--shadow-lg);
      overflow: hidden;
      animation: modalFadeIn 0.2s ease-out;
    }
    @keyframes modalFadeIn {
      from { opacity: 0; transform: scale(0.96); }
      to { opacity: 1; transform: scale(1); }
    }
    .modal-header {
      padding: 1.25rem 1.75rem;
      background: var(--primary);
      color: #ffffff;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .modal-header h3 {
      font-size: 1.2rem;
      font-weight: 700;
    }
    .modal-close-btn {
      background: none;
      border: none;
      color: #ffffff;
      font-size: 1.5rem;
      cursor: pointer;
    }
    .modal-body {
      padding: 1.75rem;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
    }
    .detail-section h4 {
      font-size: 0.95rem;
      font-weight: 700;
      color: var(--primary);
      margin-bottom: 0.5rem;
      display: flex;
      align-items: center;
      gap: 0.4rem;
    }
    .checklist {
      list-style-type: none;
      display: flex;
      flex-direction: column;
      gap: 0.4rem;
    }
    .checklist li {
      display: flex;
      align-items: center;
      gap: 0.6rem;
      font-size: 0.875rem;
    }
    .modal-footer {
      padding: 1.25rem 1.75rem;
      background: #f8fafc;
      border-top: 1px solid var(--border);
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    /* How It Works & Directory Section */
    .info-section {
      padding: 3.5rem 0;
      background: #ffffff;
      border-top: 1px solid var(--border);
      border-bottom: 1px solid var(--border);
    }
    .section-header {
      text-align: center;
      max-width: 650px;
      margin: 0 auto 2.5rem;
    }
    .section-header h2 {
      font-size: 2rem;
      font-weight: 800;
      color: var(--primary);
      margin-bottom: 0.5rem;
    }
    .section-header p {
      color: var(--text-muted);
      font-size: 0.95rem;
    }
    .steps-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 2rem;
    }
    .step-card {
      background: #f8fafc;
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 2rem;
      text-align: center;
    }
    .step-icon {
      width: 50px;
      height: 50px;
      background: #ccfbf1;
      color: var(--teal-dark);
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1.25rem;
      font-weight: 800;
      margin: 0 auto 1.25rem;
    }
    .step-card h3 {
      font-size: 1.1rem;
      font-weight: 700;
      color: var(--primary);
      margin-bottom: 0.5rem;
    }
    .step-card p {
      font-size: 0.875rem;
      color: #64748b;
      line-height: 1.5;
    }

    /* Disclaimer Banner */
    .disclaimer-banner {
      background: #fffbeb;
      border: 1px solid #fde68a;
      border-radius: var(--radius);
      padding: 1.5rem;
      margin: 2.5rem 0;
      display: flex;
      align-items: flex-start;
      gap: 1rem;
    }
    .disclaimer-icon {
      font-size: 1.5rem;
      color: #d97706;
      line-height: 1;
    }
    .disclaimer-text h4 {
      font-size: 0.95rem;
      font-weight: 700;
      color: #92400e;
      margin-bottom: 0.25rem;
    }
    .disclaimer-text p {
      font-size: 0.825rem;
      color: #b45309;
      line-height: 1.5;
    }

    /* Footer */
    footer.site-footer {
      background: var(--primary-dark);
      color: #94a3b8;
      padding: 3rem 0 2rem;
      margin-top: auto;
      font-size: 0.85rem;
    }
    .footer-content {
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 1.5rem;
      padding-bottom: 2rem;
      border-bottom: 1px solid rgba(255,255,255,0.1);
      margin-bottom: 1.5rem;
    }
    .footer-links {
      display: flex;
      gap: 1.5rem;
      flex-wrap: wrap;
    }
    .footer-links a {
      color: #cbd5e1;
      text-decoration: none;
      transition: color 0.2s;
    }
    .footer-links a:hover {
      color: #ffffff;
    }
    .footer-bottom {
      text-align: center;
      font-size: 0.8rem;
      color: #64748b;
    }

    /* Empty States & Loaders */
    .empty-state {
      text-align: center;
      padding: 3rem 1rem;
      background: #ffffff;
      border: 1px dashed var(--border);
      border-radius: var(--radius);
      color: var(--text-muted);
    }
    .empty-state h3 {
      font-size: 1.1rem;
      color: var(--text);
      margin-bottom: 0.5rem;
    }
    .spinner {
      border: 3px solid rgba(0,0,0,0.1);
      border-top-color: var(--teal);
      border-radius: 50%;
      width: 24px;
      height: 24px;
      animation: spin 0.8s linear infinite;
      display: inline-block;
    }
    @keyframes spin {
      to { transform: rotate(360deg); }
    }

    /* Mobile Responsive */
    @media (max-width: 868px) {
      .hero-title { font-size: 1.85rem; }
      .checker-layout { grid-template-columns: 1fr; }
      .form-row { grid-template-columns: 1fr; }
      .schemes-grid { grid-template-columns: 1fr; }
      nav.nav-links { display: none; }
      .mobile-menu-toggle { display: block; }
      nav.nav-links.mobile-open {
        display: flex;
        flex-direction: column;
        position: absolute;
        top: 70px;
        left: 0;
        right: 0;
        background: var(--primary);
        padding: 1.5rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
      }
    }
  </style>
</head>
<body>

  <!-- Top Header Navigation -->
  <header class="site-header">
    <div class="container nav-wrapper">
      <a href="#home" class="brand-logo" onclick="switchTab('explore')">
        <svg viewBox="0 0 24 24">
          <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2" fill="none"/>
          <path d="M12 2v20M2 12h20M4.93 4.93l14.14 14.14M4.93 19.07L19.07 4.93" stroke="currentColor" stroke-width="1.5"/>
        </svg>
        <div class="brand-text">
          <h1>SchemeSathi AI</h1>
          <span data-i18n="hero_badge">Guide to Government Schemes</span>
        </div>
      </a>

      <nav class="nav-links" id="mainNav">
        <a class="active" onclick="switchTab('explore')" data-i18n="nav_explore">Explore Schemes</a>
        <a onclick="switchTab('checker')" data-i18n="nav_checker">Eligibility Checker</a>
        <a onclick="switchTab('assistant')" data-i18n="nav_assistant">AI Assistant</a>
        <a onclick="switchTab('saved')" data-i18n="nav_saved">Saved Schemes</a>
      </nav>

      <div class="nav-actions">
        <select class="lang-selector" id="langSelector" onchange="changeLanguage(this.value)">
          <option value="en">English</option>
          <option value="te">తెలుగు (Telugu)</option>
          <option value="hi">हिन्दी (Hindi)</option>
        </select>
        
        <button class="saved-badge-btn" onclick="switchTab('saved')">
          <span data-i18n="btn_saved">Saved</span>
          <span class="badge-count" id="savedCount">0</span>
        </button>

        <button class="mobile-menu-toggle" onclick="toggleMobileNav()">☰</button>
      </div>
    </div>
  </header>

  <!-- Hero Section -->
  <section class="hero-section" id="heroSection">
    <div class="container">
      <div class="hero-badge">
        <span style="font-size: 1rem;">🇮🇳</span>
        <span data-i18n="hero_badge">Government Scheme Guidance for Every Indian Citizen</span>
      </div>
      <h2 class="hero-title" data-i18n="hero_title">Discover Government Schemes You Are Eligible For</h2>
      <p class="hero-subtitle" data-i18n="hero_subtitle">
        SchemeSathi AI simplifies Indian central and state government welfare programs. Check eligibility in minutes, find required documents, and get direct links to official application portals.
      </p>

      <div class="hero-search-box">
        <input type="text" id="heroSearchInput" placeholder="Search by scheme name, keyword (e.g. scholarship, farmer, housing)..." data-i18n-attr="placeholder:hero_search_placeholder">
        <button type="button" onclick="executeHeroSearch()">
          <span data-i18n="hero_search_button">Find Schemes</span>
          <span>🔍</span>
        </button>
      </div>

      <div class="hero-stats">
        <div class="stat-item">
          <div class="stat-number" id="statSchemesCount">18+</div>
          <div class="stat-label" data-i18n="stat_schemes">Curated Schemes</div>
        </div>
        <div class="stat-item">
          <div class="stat-number">36</div>
          <div class="stat-label" data-i18n="stat_states">States & UTs Covered</div>
        </div>
        <div class="stat-item">
          <div class="stat-number">100%</div>
          <div class="stat-label" data-i18n="stat_free">Free & Neutral</div>
        </div>
      </div>
    </div>
  </section>

  <!-- Sticky Tab Bar -->
  <div class="tab-nav">
    <div class="container tab-list">
      <button class="tab-btn active" id="tabBtnExplore" onclick="switchTab('explore')">
        <span>📋</span> <span data-i18n="nav_explore">Explore Schemes</span>
      </button>
      <button class="tab-btn" id="tabBtnChecker" onclick="switchTab('checker')">
        <span>⚖️</span> <span data-i18n="nav_checker">Eligibility Checker</span>
      </button>
      <button class="tab-btn" id="tabBtnAssistant" onclick="switchTab('assistant')">
        <span>🤖</span> <span data-i18n="nav_assistant">AI Assistant</span>
      </button>
      <button class="tab-btn" id="tabBtnSaved" onclick="switchTab('saved')">
        <span>❤️</span> <span data-i18n="nav_saved">Saved Schemes</span>
      </button>
    </div>
  </div>

  <main class="container">
    
    <!-- VIEW 1: EXPLORE SCHEMES -->
    <section class="view-section active" id="viewExplore">
      <!-- Quick Category Filter Pills -->
      <div class="category-pills" id="categoryPills">
        <button class="cat-pill active" onclick="selectCategory('all')" data-i18n="cat_all">All Schemes</button>
        <button class="cat-pill" onclick="selectCategory('Farmers and agriculture')" data-i18n="cat_farmers">Farmers & Agriculture</button>
        <button class="cat-pill" onclick="selectCategory('Health and healthcare')" data-i18n="cat_health">Health & Healthcare</button>
        <button class="cat-pill" onclick="selectCategory('Scholarships')" data-i18n="cat_education">Students & Scholarships</button>
        <button class="cat-pill" onclick="selectCategory('Women and children')" data-i18n="cat_women">Women & Children</button>
        <button class="cat-pill" onclick="selectCategory('Small businesses')" data-i18n="cat_business">Small Businesses</button>
        <button class="cat-pill" onclick="selectCategory('Housing')" data-i18n="cat_housing">Housing</button>
        <button class="cat-pill" onclick="selectCategory('Senior citizens')" data-i18n="cat_seniors">Senior Citizens</button>
        <button class="cat-pill" onclick="selectCategory('Disability support')" data-i18n="cat_disability">Disability Support</button>
      </div>

      <!-- Filter Controls Toolbar -->
      <div class="filter-toolbar">
        <div class="filter-grid">
          <div class="form-group">
            <label data-i18n="filter_state">Filter by State / UT</label>
            <select class="form-control" id="filterState" onchange="applyFilters()">
              <option value="all">All India (Central & All States)</option>
            </select>
          </div>
          <div class="form-group">
            <label data-i18n="filter_level">Government Level</label>
            <select class="form-control" id="filterLevel" onchange="applyFilters()">
              <option value="all" data-i18n="filter_all_levels">All Levels (Central & State)</option>
              <option value="Central" data-i18n="filter_central">Central Government</option>
              <option value="State" data-i18n="filter_state_level">State Government</option>
            </select>
          </div>
          <div class="form-group">
            <label data-i18n="filter_sort">Sort By</label>
            <select class="form-control" id="filterSort" onchange="applyFilters()">
              <option value="relevance" data-i18n="sort_relevance">Most Relevant</option>
              <option value="name_asc" data-i18n="sort_name">Scheme Name (A-Z)</option>
            </select>
          </div>
        </div>

        <div class="toolbar-actions">
          <div class="results-badge" id="resultsCount">Loading schemes...</div>
          <button class="btn-clear-filter" onclick="resetFilters()" data-i18n="clear_filters">Clear Filters</button>
        </div>
      </div>

      <!-- Schemes Cards Grid -->
      <div class="schemes-grid" id="schemesGrid">
        <!-- Rendered dynamically by JavaScript -->
      </div>
    </section>

    <!-- VIEW 2: ELIGIBILITY CHECKER -->
    <section class="view-section" id="viewChecker">
      <div class="checker-layout">
        <!-- Input Form -->
        <div class="checker-card">
          <div class="checker-header">
            <h2 data-i18n="checker_title">Smart Eligibility Checker</h2>
            <p data-i18n="checker_subtitle">Answer a few basic questions. We evaluate rules locally to show schemes that match your profile. No Aadhaar or personal ID required.</p>
          </div>

          <form class="checker-form" id="eligibilityForm" onsubmit="handleEligibilitySubmit(event)">
            <div class="form-row">
              <div class="form-group">
                <label data-i18n="form_age">Your Age (Years)</label>
                <input type="number" class="form-control" id="checkAge" min="0" max="120" placeholder="e.g. 24" required>
              </div>
              <div class="form-group">
                <label data-i18n="form_gender">Gender</label>
                <select class="form-control" id="checkGender">
                  <option value="all">Any / Prefer not to say</option>
                  <option value="female">Female</option>
                  <option value="male">Male</option>
                </select>
              </div>
            </div>

            <div class="form-group">
              <label data-i18n="form_state">State / Union Territory</label>
              <select class="form-control" id="checkState" required>
                <!-- Populated dynamically -->
              </select>
            </div>

            <div class="form-group">
              <label data-i18n="form_occupation">Primary Occupation / Status</label>
              <select class="form-control" id="checkOccupation">
                <option value="any">General / Other</option>
                <option value="farmer">Farmer / Agricultural Worker</option>
                <option value="student">Student / Scholar</option>
                <option value="street-vendor">Street Vendor / Hawking</option>
                <option value="artisan">Artisan / Craftsperson (Vishwakarma)</option>
                <option value="small-business">Small Business / Micro Entrepreneur</option>
                <option value="unemployed">Unemployed Youth</option>
                <option value="unorganized-worker">Daily Wage / Unorganized Worker</option>
              </select>
            </div>

            <div class="form-group">
              <label data-i18n="form_income">Annual Family Income Range</label>
              <select class="form-control" id="checkIncome">
                <option value="90000">Below ₹1,00,000 (BPL / Very Low)</option>
                <option value="200000">₹1,00,000 - ₹2,50,000 (Low Income / EWS)</option>
                <option value="400000">₹2,50,000 - ₹5,00,000 (LIG)</option>
                <option value="750000">₹5,00,000 - ₹8,00,000 (MIG)</option>
                <option value="1200000">Above ₹8,00,000</option>
              </select>
            </div>

            <div class="form-group">
              <label data-i18n="form_category">Social Category (For Quotas/Special Grants)</label>
              <select class="form-control" id="checkCategory">
                <option value="All">General / All</option>
                <option value="OBC">OBC (Other Backward Classes)</option>
                <option value="SC">SC (Scheduled Caste)</option>
                <option value="ST">ST (Scheduled Tribe)</option>
                <option value="EWS">EWS (Economically Weaker Section)</option>
              </select>
            </div>

            <div class="toggle-group">
              <div class="toggle-btn" id="toggleStudent" onclick="toggleSwitch('toggleStudent')">
                <div class="toggle-knob"></div>
              </div>
              <span class="toggle-label" data-i18n="form_student">Currently enrolled student?</span>
            </div>

            <div class="toggle-group">
              <div class="toggle-btn" id="toggleFarmer" onclick="toggleSwitch('toggleFarmer')">
                <div class="toggle-knob"></div>
              </div>
              <span class="toggle-label" data-i18n="form_farmer">Family owns agricultural land / farm?</span>
            </div>

            <div class="toggle-group">
              <div class="toggle-btn" id="toggleDisability" onclick="toggleSwitch('toggleDisability')">
                <div class="toggle-knob"></div>
              </div>
              <span class="toggle-label" data-i18n="form_disability">Certified disability (PwD / UDID)?</span>
            </div>

            <div style="display: flex; gap: 1rem; margin-top: 1rem;">
              <button type="submit" class="btn btn-primary" style="flex: 2; padding: 0.8rem;" id="btnSubmitEligibility">
                <span data-i18n="form_submit">Evaluate My Eligibility</span>
              </button>
              <button type="button" class="btn btn-outline" style="flex: 1;" onclick="resetEligibilityForm()" data-i18n="form_reset">
                Reset
              </button>
            </div>
          </form>
        </div>

        <!-- Evaluation Results Display -->
        <div class="checker-results" id="checkerResultsBox">
          <div class="empty-state">
            <span style="font-size: 2.5rem;">🎯</span>
            <h3 style="margin-top: 1rem;" data-i18n="checker_title">Ready to evaluate</h3>
            <p>Fill out the profile on the left and click "Evaluate My Eligibility" to see which schemes match your circumstances.</p>
          </div>
        </div>
      </div>
    </section>

    <!-- VIEW 3: AI ASSISTANT -->
    <section class="view-section" id="viewAssistant">
      <div class="assistant-layout">
        <div class="assistant-topbar">
          <div class="assistant-info">
            <h3 data-i18n="assistant_title">
              <span>🤖</span> SchemeSathi AI Assistant
            </h3>
            <div style="font-size: 0.75rem; color: #94a3b8;" data-i18n="assistant_subtitle">
              Ask about welfare schemes, required documents, or application guidelines
            </div>
          </div>
          <div style="display: flex; align-items: center; gap: 0.75rem;">
            <span class="assistant-mode-pill" id="assistantModeBadge">Knowledge Engine</span>
            <button class="btn-clear-filter" style="color: #cbd5e1; border-color: rgba(255,255,255,0.2);" onclick="clearAssistantChat()" data-i18n="chat_clear">Clear Chat</button>
          </div>
        </div>

        <div class="assistant-messages" id="assistantMessages">
          <div class="message-bubble message-assistant" id="assistantWelcomeMessage">
            <strong>Namaste!</strong> I am your SchemeSathi Assistant. Ask me questions about Indian government welfare schemes, required documents, or how to apply for scholarships, farmer support, housing aid, and small business loans.
          </div>
        </div>

        <div class="suggested-chips">
          <button class="prompt-chip" onclick="sendSuggestedQuestion('Which scholarships suit college students?')" data-i18n="chat_prompt_1">Which scholarships suit college students?</button>
          <button class="prompt-chip" onclick="sendSuggestedQuestion('Schemes for farmers in Andhra Pradesh?')" data-i18n="chat_prompt_2">Schemes for farmers in AP?</button>
          <button class="prompt-chip" onclick="sendSuggestedQuestion('How can I apply for Ayushman Bharat?')" data-i18n="chat_prompt_3">How to apply for Ayushman Bharat?</button>
          <button class="prompt-chip" onclick="sendSuggestedQuestion('What documents are needed for PM Mudra loan?')" data-i18n="chat_prompt_4">Documents for PM Mudra loan?</button>
        </div>

        <form class="chat-input-bar" onsubmit="handleChatSubmit(event)">
          <input type="text" id="chatInput" placeholder="Ask in English, Telugu, or Hindi..." data-i18n-attr="placeholder:chat_placeholder" autocomplete="off" required>
          <button type="submit" class="btn btn-primary" id="btnChatSend" data-i18n="chat_send">Send</button>
        </form>
      </div>
    </section>

    <!-- VIEW 4: SAVED SCHEMES -->
    <section class="view-section" id="viewSaved">
      <div class="saved-schemes-card">
        <div class="saved-header">
          <div>
            <h2 style="font-size: 1.5rem; color: var(--primary);" data-i18n="saved_title">Your Saved Schemes</h2>
            <p style="font-size: 0.875rem; color: var(--text-muted);" data-i18n="saved_subtitle">
              Schemes you bookmark are saved locally in your browser for quick review. You can print or copy this list as an application checklist.
            </p>
          </div>
          <div style="display: flex; gap: 0.75rem;">
            <button class="btn btn-outline" onclick="window.print()" data-i18n="btn_print_checklist">Print / Export</button>
            <button class="btn-clear-filter" onclick="clearAllSavedSchemes()" data-i18n="btn_clear_saved">Clear All</button>
          </div>
        </div>

        <div id="savedSchemesContainer">
          <!-- Rendered dynamically -->
        </div>
      </div>
    </section>

    <!-- How It Works Section -->
    <section class="info-section">
      <div class="section-header">
        <h2 data-i18n="how_it_works_title">How SchemeSathi Works</h2>
        <p>Three straightforward steps to bridge the gap between government welfare programs and citizen entitlements.</p>
      </div>

      <div class="steps-grid">
        <div class="step-card">
          <div class="step-icon">1</div>
          <h3 data-i18n="how_step_1_title">1. Explore & Filter</h3>
          <p data-i18n="how_step_1_desc">Browse verified Central and State government schemes categorized by your life stage, profession, or need.</p>
        </div>
        <div class="step-card">
          <div class="step-icon">2</div>
          <h3 data-i18n="how_step_2_title">2. Check Eligibility</h3>
          <p data-i18n="how_step_2_desc">Use our rule evaluation tool or ask the AI assistant to instantly see which welfare programs you may qualify for.</p>
        </div>
        <div class="step-card">
          <div class="step-icon">3</div>
          <h3 data-i18n="how_step_3_title">3. Apply on Official Portals</h3>
          <p data-i18n="how_step_3_desc">Review the required documents checklist and navigate directly to official government portals to submit your application safely.</p>
        </div>
      </div>

      <!-- Disclaimer Banner -->
      <div class="disclaimer-banner">
        <div class="disclaimer-icon">⚠️</div>
        <div class="disclaimer-text">
          <h4 data-i18n="disclaimer_title">Important Official Disclaimer</h4>
          <p data-i18n="disclaimer_body">
            SchemeSathi AI is an independent educational and informational guide. It is not affiliated with or endorsed by any government department. Eligibility checks provided here are indicative and based on publicly available guidelines. Final eligibility, approval, and disbursements rest exclusively with the respective Government of India and State Government authorities. Never share bank passwords, OTPs, or pay any unauthorized agents.
          </p>
        </div>
      </div>
    </section>

  </main>

  <!-- Scheme Details Modal Dialog -->
  <div class="modal-backdrop" id="schemeModal" onclick="closeModalOnBackdrop(event)">
    <div class="modal-content">
      <div class="modal-header">
        <h3 id="modalSchemeTitle">Scheme Details</h3>
        <button class="modal-close-btn" onclick="closeSchemeModal()">&times;</button>
      </div>
      <div class="modal-body" id="modalSchemeBody">
        <!-- Rendered dynamically -->
      </div>
      <div class="modal-footer">
        <button class="btn btn-outline" id="modalSaveBtn" onclick="toggleSaveCurrentModalScheme()">Save Scheme</button>
        <a href="#" target="_blank" rel="noopener noreferrer" class="btn btn-primary" id="modalOfficialLink" data-i18n="official_portal_link">
          Go to Official Portal ↗
        </a>
      </div>
    </div>
  </div>

  <!-- Site Footer -->
  <footer class="site-footer">
    <div class="container">
      <div class="footer-content">
        <div>
          <h4 style="color: #ffffff; font-size: 1.1rem; margin-bottom: 0.35rem;">SchemeSathi AI</h4>
          <p data-i18n="footer_tagline">Empowering citizens with clarity on public welfare programs.</p>
        </div>
        <div class="footer-links">
          <a href="https://www.myscheme.gov.in" target="_blank" rel="noopener noreferrer">myScheme.gov.in</a>
          <a href="https://www.india.gov.in" target="_blank" rel="noopener noreferrer">india.gov.in</a>
          <a href="https://scholarships.gov.in" target="_blank" rel="noopener noreferrer">scholarships.gov.in</a>
          <a href="https://pmjay.gov.in" target="_blank" rel="noopener noreferrer">pmjay.gov.in</a>
        </div>
      </div>
      <div class="footer-bottom">
        <p data-i18n="footer_rights">SchemeSathi AI - Public Information Platform. Free to use.</p>
        <p style="margin-top: 0.25rem;">Built for Indian Citizens across all 28 States and 8 Union Territories.</p>
      </div>
    </div>
  </footer>

  <!-- Embedded Vanilla JavaScript Application Logic -->
  <script>
    // State Management
    let currentLanguage = 'en';
    let allSchemes = [];
    let savedSchemeIds = JSON.parse(localStorage.getItem('schemesathi_saved') || '[]');
    let currentActiveCategory = 'all';
    let currentModalScheme = null;
    let chatHistory = [];

    // Translations Dictionary injected from Python
    const I18N = {{ translations_json | safe }};

    // Initialize application on DOM ready
    document.addEventListener('DOMContentLoaded', async () => {
      // Check stored language preference
      const savedLang = localStorage.getItem('schemesathi_lang');
      if (savedLang && I18N[savedLang]) {
        currentLanguage = savedLang;
        document.getElementById('langSelector').value = savedLang;
      }

      updateSavedCounter();
      applyLanguage(currentLanguage);

      // Load States and Schemes from Flask REST API
      await loadStates();
      await fetchSchemes();
      await checkSystemHealth();
    });

    // Check application health
    async function checkSystemHealth() {
      try {
        const res = await fetch('/api/health');
        if (res.ok) {
          const health = await res.json();
          const badge = document.getElementById('assistantModeBadge');
          if (badge) {
            badge.textContent = health.ai_status.includes('live_api') ? 'AI Assistant (Live)' : 'Scheme Knowledge Engine';
          }
          if (health.schemes_count) {
            document.getElementById('statSchemesCount').textContent = health.schemes_count + '+';
          }
        }
      } catch (err) {
        console.warn('Health check warning:', err);
      }
    }

    // Load States and UTs dropdowns
    async function loadStates() {
      try {
        const res = await fetch('/api/states');
        if (res.ok) {
          const data = await res.json();
          const filterSelect = document.getElementById('filterState');
          const checkSelect = document.getElementById('checkState');
          
          data.states.forEach(state => {
            const opt1 = document.createElement('option');
            opt1.value = state;
            opt1.textContent = state;
            filterSelect.appendChild(opt1);

            const opt2 = document.createElement('option');
            opt2.value = state;
            opt2.textContent = state;
            checkSelect.appendChild(opt2);
          });
        }
      } catch (err) {
        console.error('Failed to load states:', err);
      }
    }

    // Fetch Schemes from Backend
    async function fetchSchemes(params = {}) {
      const grid = document.getElementById('schemesGrid');
      grid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 3rem;"><div class="spinner"></div><p style="margin-top: 0.5rem; color: #64748b;">Loading verified schemes...</p></div>';

      try {
        const queryParams = new URLSearchParams();
        if (params.search) queryParams.set('q', params.search);
        if (params.category && params.category !== 'all') queryParams.set('category', params.category);
        if (params.state && params.state !== 'all') queryParams.set('state', params.state);
        if (params.level && params.level !== 'all') queryParams.set('level', params.level);
        if (params.sort) queryParams.set('sort', params.sort);

        const res = await fetch('/api/schemes?' + queryParams.toString());
        if (res.ok) {
          const data = await res.json();
          allSchemes = data.schemes;
          renderSchemes(allSchemes);
          document.getElementById('resultsCount').textContent = `Showing ${data.schemes.length} of ${data.total} schemes`;
        } else {
          grid.innerHTML = '<div class="empty-state" style="grid-column: 1/-1;"><h3>Could not load schemes</h3><p>Please check your connection and refresh.</p></div>';
        }
      } catch (err) {
        console.error('Error fetching schemes:', err);
        grid.innerHTML = '<div class="empty-state" style="grid-column: 1/-1;"><h3>Network Error</h3><p>Failed to connect to SchemeSathi server.</p></div>';
      }
    }

    // Render scheme cards
    function renderSchemes(schemes) {
      const grid = document.getElementById('schemesGrid');
      if (!schemes || schemes.length === 0) {
        grid.innerHTML = `
          <div class="empty-state" style="grid-column: 1/-1;">
            <span style="font-size: 2.5rem;">🔍</span>
            <h3 style="margin-top: 0.75rem;">No schemes matched your criteria</h3>
            <p>Try clearing your search terms or selecting a different category or state filter.</p>
            <button class="btn btn-outline" style="margin-top: 1rem;" onclick="resetFilters()">Reset All Filters</button>
          </div>
        `;
        return;
      }

      grid.innerHTML = schemes.map(s => {
        const isSaved = savedSchemeIds.includes(s.id);
        const levelBadgeClass = s.government_level === 'Central' ? 'badge-central' : 'badge-state';
        const stateText = s.state === 'All India' ? 'All India (Central)' : s.state;

        return `
          <div class="scheme-card" id="card-${s.id}">
            <div class="card-top">
              <div class="card-badges">
                <span class="badge ${levelBadgeClass}">${s.government_level}</span>
                <span class="badge badge-category">${s.category}</span>
                <span class="badge badge-verified">✓ Verified</span>
                <span class="badge" style="background: #f1f5f9; color: #475569;">📍 ${stateText}</span>
              </div>
              <h3 class="scheme-title">${escapeHtml(s.name)}</h3>
              <p class="scheme-desc">${escapeHtml(s.short_description)}</p>

              <div class="scheme-snippet">
                <div class="snippet-label">Benefits</div>
                <div class="snippet-val">${escapeHtml(s.benefits)}</div>
              </div>

              <div style="font-size: 0.8rem; color: #64748b; margin-bottom: 0.5rem;">
                <strong>Eligibility:</strong> ${escapeHtml(s.eligibility_summary)}
              </div>
            </div>

            <div class="card-footer">
              <button class="btn btn-outline" onclick="openSchemeDetail('${s.id}')">
                View Details
              </button>
              <div style="display: flex; gap: 0.5rem;">
                <button class="btn btn-primary" onclick="prefillEligibility('${s.id}')">
                  Check Eligibility
                </button>
                <button class="btn-save-icon ${isSaved ? 'saved' : ''}" title="${isSaved ? 'Remove from Saved' : 'Save Scheme'}" onclick="toggleSaveScheme('${s.id}', this)">
                  ${isSaved ? '❤️' : '🤍'}
                </button>
              </div>
            </div>
          </div>
        `;
      }).join('');
    }

    // Filter handling
    function selectCategory(category) {
      currentActiveCategory = category;
      document.querySelectorAll('.cat-pill').forEach(btn => {
        btn.classList.toggle('active', btn.getAttribute('onclick').includes(`'${category}'`));
      });
      applyFilters();
    }

    function applyFilters() {
      const searchVal = document.getElementById('heroSearchInput').value.trim();
      const stateVal = document.getElementById('filterState').value;
      const levelVal = document.getElementById('filterLevel').value;
      const sortVal = document.getElementById('filterSort').value;

      fetchSchemes({
        search: searchVal,
        category: currentActiveCategory,
        state: stateVal,
        level: levelVal,
        sort: sortVal
      });
    }

    function resetFilters() {
      document.getElementById('heroSearchInput').value = '';
      document.getElementById('filterState').value = 'all';
      document.getElementById('filterLevel').value = 'all';
      document.getElementById('filterSort').value = 'relevance';
      selectCategory('all');
    }

    function executeHeroSearch() {
      switchTab('explore');
      applyFilters();
    }

    // Navigation and Tab Switching
    function switchTab(tabName) {
      document.querySelectorAll('.view-section').forEach(sec => sec.classList.remove('active'));
      document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
      document.querySelectorAll('nav.nav-links a').forEach(a => a.classList.remove('active'));

      const sec = document.getElementById('view' + capitalize(tabName));
      const btn = document.getElementById('tabBtn' + capitalize(tabName));
      if (sec) sec.classList.add('active');
      if (btn) btn.classList.add('active');

      if (tabName === 'saved') {
        renderSavedSchemes();
      }

      // Close mobile navigation menu if open
      const nav = document.getElementById('mainNav');
      if (nav) nav.classList.remove('mobile-open');

      window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    function toggleMobileNav() {
      const nav = document.getElementById('mainNav');
      if (nav) nav.classList.toggle('mobile-open');
    }

    // Scheme Modal Dialog
    async function openSchemeDetail(schemeId) {
      try {
        const res = await fetch(`/api/schemes/${schemeId}`);
        if (!res.ok) return;
        const scheme = await res.json();
        currentModalScheme = scheme;

        document.getElementById('modalSchemeTitle').textContent = scheme.name;
        document.getElementById('modalOfficialLink').href = scheme.official_url;

        const isSaved = savedSchemeIds.includes(scheme.id);
        const saveBtn = document.getElementById('modalSaveBtn');
        saveBtn.textContent = isSaved ? '❤️ Saved in Checklist' : '🤍 Save Scheme';

        const docsHtml = scheme.required_documents.map(d => `<li><input type="checkbox" style="accent-color: var(--teal);"> <span>${escapeHtml(d)}</span></li>`).join('');
        const stepsHtml = scheme.application_steps.map((st, i) => `<li><strong>Step ${i+1}:</strong> ${escapeHtml(st)}</li>`).join('');

        document.getElementById('modalSchemeBody').innerHTML = `
          <div class="card-badges">
            <span class="badge ${scheme.government_level === 'Central' ? 'badge-central' : 'badge-state'}">${scheme.government_level} Government</span>
            <span class="badge badge-category">${scheme.category}</span>
            <span class="badge badge-verified">✓ Verified Source</span>
            <span class="badge" style="background:#f1f5f9; color:#475569;">📍 ${scheme.state}</span>
          </div>

          <div class="detail-section">
            <h4>📖 Overview</h4>
            <p style="font-size: 0.9rem; color: #334155; line-height: 1.6;">${escapeHtml(scheme.detailed_description)}</p>
          </div>

          <div class="detail-section">
            <h4>🎁 Key Benefits</h4>
            <div style="background: #f0fdf4; border-left: 3px solid var(--success); padding: 0.75rem 1rem; border-radius: 4px; font-size: 0.9rem; color: #166534;">
              ${escapeHtml(scheme.benefits)}
            </div>
          </div>

          <div class="detail-section">
            <h4>🎯 Eligibility Criteria</h4>
            <p style="font-size: 0.875rem; color: #334155;">${escapeHtml(scheme.eligibility_summary)}</p>
          </div>

          <div class="detail-section">
            <h4>📑 Required Documents Checklist</h4>
            <p style="font-size: 0.8rem; color: #64748b; margin-bottom: 0.5rem;">You can tick these off as you gather your paperwork:</p>
            <ul class="checklist">${docsHtml}</ul>
          </div>

          <div class="detail-section">
            <h4>🚀 Step-by-Step Application Guide</h4>
            <ol style="margin-left: 1.25rem; font-size: 0.875rem; color: #334155; display: flex; flex-direction: column; gap: 0.4rem;">
              ${stepsHtml}
            </ol>
          </div>

          <div style="font-size: 0.75rem; color: #94a3b8; border-top: 1px solid var(--border); padding-top: 0.75rem;">
            Source: ${escapeHtml(scheme.source_name)} | Last Verified: ${escapeHtml(scheme.last_verified)}
          </div>
        `;

        document.getElementById('schemeModal').classList.add('active');
      } catch (err) {
        console.error('Failed to open scheme detail:', err);
      }
    }

    function closeSchemeModal() {
      document.getElementById('schemeModal').classList.remove('active');
      currentModalScheme = null;
    }

    function closeModalOnBackdrop(e) {
      if (e.target.id === 'schemeModal') {
        closeSchemeModal();
      }
    }

    // Saved Schemes Management
    function toggleSaveScheme(schemeId, btnElement) {
      const idx = savedSchemeIds.indexOf(schemeId);
      if (idx > -1) {
        savedSchemeIds.splice(idx, 1);
        if (btnElement) {
          btnElement.classList.remove('saved');
          btnElement.textContent = '🤍';
          btnElement.title = 'Save Scheme';
        }
      } else {
        savedSchemeIds.push(schemeId);
        if (btnElement) {
          btnElement.classList.add('saved');
          btnElement.textContent = '❤️';
          btnElement.title = 'Remove from Saved';
        }
      }
      localStorage.setItem('schemesathi_saved', JSON.stringify(savedSchemeIds));
      updateSavedCounter();
      if (document.getElementById('viewSaved').classList.contains('active')) {
        renderSavedSchemes();
      }
    }

    function toggleSaveCurrentModalScheme() {
      if (!currentModalScheme) return;
      toggleSaveScheme(currentModalScheme.id);
      const isSaved = savedSchemeIds.includes(currentModalScheme.id);
      const saveBtn = document.getElementById('modalSaveBtn');
      saveBtn.textContent = isSaved ? '❤️ Saved in Checklist' : '🤍 Save Scheme';
      const cardBtn = document.querySelector(`#card-${currentModalScheme.id} .btn-save-icon`);
      if (cardBtn) {
        cardBtn.classList.toggle('saved', isSaved);
        cardBtn.textContent = isSaved ? '❤️' : '🤍';
      }
    }

    function updateSavedCounter() {
      document.getElementById('savedCount').textContent = savedSchemeIds.length;
    }

    function clearAllSavedSchemes() {
      if (confirm('Clear all saved schemes from your local storage?')) {
        savedSchemeIds = [];
        localStorage.setItem('schemesathi_saved', JSON.stringify(savedSchemeIds));
        updateSavedCounter();
        renderSavedSchemes();
        // Update all buttons on cards
        document.querySelectorAll('.btn-save-icon').forEach(btn => {
          btn.classList.remove('saved');
          btn.textContent = '🤍';
        });
      }
    }

    async function renderSavedSchemes() {
      const container = document.getElementById('savedSchemesContainer');
      if (savedSchemeIds.length === 0) {
        container.innerHTML = `
          <div class="empty-state">
            <span style="font-size: 2.5rem;">📋</span>
            <h3 style="margin-top: 0.75rem;" data-i18n="saved_empty">You haven't saved any schemes yet</h3>
            <p>Click the heart icon on any scheme card while exploring to keep it here as an application checklist.</p>
            <button class="btn btn-primary" style="margin-top: 1rem;" onclick="switchTab('explore')">Explore Schemes</button>
          </div>
        `;
        return;
      }

      container.innerHTML = '<div style="text-align: center; padding: 2rem;"><div class="spinner"></div></div>';
      
      const savedItems = [];
      for (const id of savedSchemeIds) {
        try {
          const res = await fetch(`/api/schemes/${id}`);
          if (res.ok) {
            const data = await res.json();
            savedItems.push(data);
          }
        } catch (e) {}
      }

      container.innerHTML = `
        <div style="display: flex; flex-direction: column; gap: 1rem;">
          ${savedItems.map(s => `
            <div class="result-item-card" style="display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem;">
              <div style="flex: 1;">
                <div class="card-badges" style="margin-bottom: 0.35rem;">
                  <span class="badge ${s.government_level === 'Central' ? 'badge-central' : 'badge-state'}">${s.government_level}</span>
                  <span class="badge badge-category">${s.category}</span>
                </div>
                <h4 style="font-size: 1.05rem; color: var(--primary); margin-bottom: 0.25rem;">${escapeHtml(s.name)}</h4>
                <p style="font-size: 0.85rem; color: #475569; margin-bottom: 0.5rem;">${escapeHtml(s.benefits)}</p>
                <div style="font-size: 0.8rem; color: #64748b;">
                  <strong>Required Documents:</strong> ${s.required_documents.join(', ')}
                </div>
              </div>
              <div style="display: flex; flex-direction: column; gap: 0.5rem; align-items: flex-end;">
                <button class="btn btn-outline" style="font-size: 0.8rem; padding: 0.35rem 0.75rem;" onclick="openSchemeDetail('${s.id}')">View</button>
                <a href="${s.official_url}" target="_blank" rel="noopener noreferrer" class="btn btn-primary" style="font-size: 0.8rem; padding: 0.35rem 0.75rem;">Apply ↗</a>
                <button class="btn-clear-filter" style="font-size: 0.75rem; color: #e11d48;" onclick="toggleSaveScheme('${s.id}'); renderSavedSchemes();">Remove</button>
              </div>
            </div>
          `).join('')}
        </div>
      `;
    }

    // Toggle switch handler
    function toggleSwitch(id) {
      const el = document.getElementById(id);
      el.classList.toggle('active');
    }

    // Prefill and jump to eligibility checker
    function prefillEligibility(schemeId) {
      switchTab('checker');
      const scheme = allSchemes.find(s => s.id === schemeId);
      if (scheme && scheme.state !== 'All India') {
        document.getElementById('checkState').value = scheme.state;
      }
    }

    function resetEligibilityForm() {
      document.getElementById('eligibilityForm').reset();
      document.getElementById('toggleStudent').classList.remove('active');
      document.getElementById('toggleFarmer').classList.remove('active');
      document.getElementById('toggleDisability').classList.remove('active');
      document.getElementById('checkerResultsBox').innerHTML = `
        <div class="empty-state">
          <span style="font-size: 2.5rem;">🎯</span>
          <h3 style="margin-top: 1rem;">Ready to evaluate</h3>
          <p>Fill out the profile on the left and click "Evaluate My Eligibility".</p>
        </div>
      `;
    }

    // Submit Eligibility Assessment
    async function handleEligibilitySubmit(e) {
      e.preventDefault();
      const submitBtn = document.getElementById('btnSubmitEligibility');
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<div class="spinner" style="width: 16px; height: 16px; vertical-align: middle;"></div> Evaluating...';

      const resultsBox = document.getElementById('checkerResultsBox');
      resultsBox.innerHTML = '<div style="text-align: center; padding: 3rem;"><div class="spinner"></div><p style="margin-top: 0.5rem; color: #64748b;">Evaluating scheme eligibility rules...</p></div>';

      const payload = {
        age: parseInt(document.getElementById('checkAge').value),
        gender: document.getElementById('checkGender').value,
        state: document.getElementById('checkState').value,
        occupation: document.getElementById('checkOccupation').value,
        annual_income: parseFloat(document.getElementById('checkIncome').value),
        social_category: document.getElementById('checkCategory').value,
        is_student: document.getElementById('toggleStudent').classList.contains('active'),
        is_farmer: document.getElementById('toggleFarmer').classList.contains('active'),
        has_disability: document.getElementById('toggleDisability').classList.contains('active')
      };

      try {
        const res = await fetch('/api/eligibility', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        if (res.ok) {
          const data = await res.json();
          renderEligibilityResults(data);
        } else {
          resultsBox.innerHTML = '<div class="empty-state"><h3>Evaluation Error</h3><p>Could not process eligibility rules.</p></div>';
        }
      } catch (err) {
        console.error('Eligibility error:', err);
        resultsBox.innerHTML = '<div class="empty-state"><h3>Connection Failed</h3><p>Unable to connect to backend server.</p></div>';
      } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = 'Evaluate My Eligibility';
      }
    }

    function renderEligibilityResults(data) {
      const resultsBox = document.getElementById('checkerResultsBox');
      const { summary, potentially_eligible, more_info_required, likely_not_eligible } = data;

      resultsBox.innerHTML = `
        <div style="margin-bottom: 1.5rem; padding-bottom: 1rem; border-bottom: 1px solid var(--border);">
          <h3 style="color: var(--primary); font-size: 1.25rem; margin-bottom: 0.35rem;">Eligibility Evaluation Report</h3>
          <p style="font-size: 0.825rem; color: var(--text-muted);">
            Evaluated ${summary.total_evaluated} schemes: 
            <strong style="color: var(--success);">${summary.potentially_eligible_count} Potentially Eligible</strong>, 
            <strong style="color: var(--warning);">${summary.more_info_required_count} More Info Needed</strong>, 
            <strong style="color: var(--danger);">${summary.likely_not_eligible_count} Likely Ineligible</strong>.
          </p>
        </div>

        <!-- Section 1: Potentially Eligible -->
        <div class="eligibility-category-block">
          <div class="eligibility-category-header" style="color: var(--success);">
            <span>✅</span>
            <span>Potentially Eligible (${potentially_eligible.length})</span>
          </div>
          ${potentially_eligible.length === 0 ? '<p style="font-size: 0.85rem; color: #64748b;">No schemes met all primary criteria perfectly. Review schemes in "More Information Required".</p>' : ''}
          ${potentially_eligible.map(item => renderResultSchemeCard(item, 'eligible')).join('')}
        </div>

        <!-- Section 2: More Info Required -->
        <div class="eligibility-category-block">
          <div class="eligibility-category-header" style="color: var(--warning);">
            <span>⚠️</span>
            <span>More Information Required (${more_info_required.length})</span>
          </div>
          ${more_info_required.map(item => renderResultSchemeCard(item, 'review')).join('')}
        </div>

        <!-- Section 3: Likely Not Eligible -->
        <div class="eligibility-category-block">
          <div class="eligibility-category-header" style="color: var(--danger);">
            <span>❌</span>
            <span>Likely Not Eligible (${likely_not_eligible.length})</span>
          </div>
          ${likely_not_eligible.slice(0, 5).map(item => renderResultSchemeCard(item, 'ineligible')).join('')}
        </div>

        <div style="font-size: 0.75rem; color: #64748b; background: #f8fafc; padding: 0.75rem; border-radius: var(--radius-sm); border-left: 3px solid var(--warning);">
          <strong>Disclaimer:</strong> ${escapeHtml(data.disclaimer)}
        </div>
      `;
    }

    function renderResultSchemeCard(item, type) {
      const statusBadge = type === 'eligible' 
        ? '<span class="status-badge-lg status-eligible">Potentially Eligible</span>'
        : (type === 'review' 
            ? '<span class="status-badge-lg status-review">Verification Needed</span>'
            : '<span class="status-badge-lg status-ineligible">Ineligible based on rules</span>');

      const matchesHtml = item.matching_reasons.map(r => `<li class="match">✓ ${escapeHtml(r)}</li>`).join('');
      const missingHtml = item.missing_criteria.map(m => `<li class="missing">✗ ${escapeHtml(m)}</li>`).join('');
      const uncertainHtml = item.uncertain_criteria.map(u => `<li class="uncertain">⚠️ ${escapeHtml(u)}</li>`).join('');

      return `
        <div class="result-item-card">
          <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 0.5rem; margin-bottom: 0.5rem;">
            <h4 class="result-item-title">${escapeHtml(item.scheme_name)}</h4>
            ${statusBadge}
          </div>

          <div style="font-size: 0.825rem; color: #475569; margin-bottom: 0.5rem;">
            <strong>Benefits:</strong> ${escapeHtml(item.benefits)}
          </div>

          <ul class="reason-list">
            ${matchesHtml}
            ${missingHtml}
            ${uncertainHtml}
          </ul>

          <div style="display: flex; gap: 0.5rem; justify-content: flex-end; margin-top: 0.75rem;">
            <button class="btn btn-outline" style="font-size: 0.75rem; padding: 0.3rem 0.6rem;" onclick="openSchemeDetail('${item.scheme_id}')">Details</button>
            <a href="${item.official_url}" target="_blank" rel="noopener noreferrer" class="btn btn-primary" style="font-size: 0.75rem; padding: 0.3rem 0.6rem;">Official Portal ↗</a>
          </div>
        </div>
      `;
    }

    // AI Assistant Handlers
    function sendSuggestedQuestion(q) {
      document.getElementById('chatInput').value = q;
      handleChatSubmit(new Event('submit'));
    }

    function clearAssistantChat() {
      const messagesContainer = document.getElementById('assistantMessages');
      messagesContainer.innerHTML = `
        <div class="message-bubble message-assistant">
          <strong>Namaste!</strong> Chat history has been cleared. What government scheme information can I help you find?
        </div>
      `;
      chatHistory = [];
    }

    async function handleChatSubmit(e) {
      if (e) e.preventDefault();
      const input = document.getElementById('chatInput');
      const question = input.value.trim();
      if (!question) return;

      input.value = '';
      const sendBtn = document.getElementById('btnChatSend');
      sendBtn.disabled = true;
      sendBtn.textContent = '...';

      const messagesContainer = document.getElementById('assistantMessages');

      // Append user message
      const userBubble = document.createElement('div');
      userBubble.className = 'message-bubble message-user';
      userBubble.textContent = question;
      messagesContainer.appendChild(userBubble);
      messagesContainer.scrollTop = messagesContainer.scrollHeight;

      // Append loading indicator
      const loadingBubble = document.createElement('div');
      loadingBubble.className = 'message-bubble message-assistant';
      loadingBubble.innerHTML = '<div class="spinner" style="width: 16px; height: 16px; vertical-align: middle;"></div> <span style="font-size: 0.85rem; color: #64748b;">Consulting government scheme database...</span>';
      messagesContainer.appendChild(loadingBubble);
      messagesContainer.scrollTop = messagesContainer.scrollHeight;

      try {
        const res = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            question: question,
            history: chatHistory,
            language: currentLanguage
          })
        });

        if (res.ok) {
          const data = await res.json();
          loadingBubble.innerHTML = formatChatReply(data.reply);
          chatHistory.push({ role: 'user', content: question });
          chatHistory.push({ role: 'assistant', content: data.reply });
        } else {
          loadingBubble.innerHTML = '<span style="color: var(--danger);">Sorry, an error occurred while processing your request. Please try again.</span>';
        }
      } catch (err) {
        console.error('Chat error:', err);
        loadingBubble.innerHTML = '<span style="color: var(--danger);">Unable to connect to the assistant service. Please check your network.</span>';
      } finally {
        sendBtn.disabled = false;
        sendBtn.textContent = 'Send';
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
      }
    }

    // Markdown-like formatting for chat replies
    function formatChatReply(text) {
      if (!text) return '';
      let formatted = escapeHtml(text);
      // Bold
      formatted = formatted.replace(/\\*\\*(.*?)\\*\\*/g, '<strong>$1</strong>');
      // Headings
      formatted = formatted.replace(/^### (.*$)/gim, '<h3>$1</h3>');
      // Links [text](url)
      formatted = formatted.replace(/\\[(.*?)\\]\\((https?:\\/\\/[^\\s]+)\\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1 ↗</a>');
      // Line breaks and list bullets
      formatted = formatted.replace(/^- (.*$)/gim, '<li>$1</li>');
      formatted = formatted.replace(/\\n/g, '<br>');
      return formatted;
    }

    // Multilingual Switcher
    function changeLanguage(lang) {
      if (!I18N[lang]) return;
      currentLanguage = lang;
      localStorage.setItem('schemesathi_lang', lang);
      applyLanguage(lang);
    }

    function applyLanguage(lang) {
      const dict = I18N[lang] || I18N['en'];
      document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (dict[key]) {
          el.textContent = dict[key];
        }
      });

      document.querySelectorAll('[data-i18n-attr]').forEach(el => {
        const [attr, key] = el.getAttribute('data-i18n-attr').split(':');
        if (dict[key]) {
          el.setAttribute(attr, dict[key]);
        }
      });
    }

    // Utilities
    function escapeHtml(str) {
      if (!str) return '';
      const div = document.createElement('div');
      div.textContent = str;
      return div.innerHTML;
    }

    function capitalize(str) {
      if (!str) return '';
      return str.charAt(0).toUpperCase() + str.slice(1);
    }
  </script>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def index():
    """Serve the complete SchemeSathi AI single-page application."""
    translations_json = json.dumps(TRANSLATIONS)
    return render_template_string(HTML_PAGE, translations_json=translations_json)

# -----------------------------------------------------------------------------
# Global Error Handlers (JSON for /api/*, clean response for Web)
# -----------------------------------------------------------------------------
@app.errorhandler(404)
def handle_not_found(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Endpoint not found", "path": request.path}), 404
    return make_response("<h3>404 - Page Not Found</h3><p><a href='/'>Return to SchemeSathi AI Home</a></p>", 404)

@app.errorhandler(400)
def handle_bad_request(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Bad request", "message": str(e)}), 400
    return make_response("<h3>400 - Bad Request</h3>", 400)

@app.errorhandler(500)
def handle_server_error(e):
    logger.error(f"Internal server error: {e}")
    if request.path.startswith("/api/"):
        return jsonify({"error": "An internal error occurred. Please try again later."}), 500
    return make_response("<h3>500 - Server Error</h3><p>An unexpected error occurred. Please try again later.</p>", 500)

# -----------------------------------------------------------------------------
# Main Execution Entrypoint
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    print(f"==================================================")
    print(f"  {APP_NAME} v{APP_VERSION} Starting")
    print(f"  Tagline: {APP_TAGLINE}")
    print(f"  Host: {HOST}:{PORT}")
    print(f"  Database: {'Supabase Connected' if is_supabase_configured() else 'Demo Mode (Curated Dataset)'}")
    print(f"  AI Mode: {'Live External API' if AI_API_KEY else 'Rule-Based Knowledge Engine'}")
    print(f"==================================================")
    app.run(host=HOST, port=PORT, debug=DEBUG)
