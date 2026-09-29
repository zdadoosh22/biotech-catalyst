"""Configuration settings, API constants, and default biotech mappings for BioCatalyst.
"""

import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# Database path
DB_PATH = os.environ.get("BIOCATALYST_DB_PATH", str(DATA_DIR / "biocatalyst.db"))

# API keys from environment
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
NCBI_API_KEY = os.environ.get("NCBI_API_KEY")

# Rate limiting and timeouts
CLINICAL_TRIALS_API_URL = "https://clinicaltrials.gov/api/v2/studies"
NCBI_PUBMED_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
OPENFDA_BASE_URL = "https://api.fda.gov/drug"
UNIPROT_BASE_URL = "https://rest.uniprot.org/uniprotkb"
DEFAULT_TIMEOUT_SEC = 15

# Canonical high-profile biotech sponsors, tickers, and modality specialization
KNOWN_BIOTECH_REGISTRY = {
    # mRNA Pioneers
    "moderna": {"ticker": "MRNA", "name": "Moderna, Inc.", "focus": "mRNA, Oncology Neoantigens, Vaccines"},
    "modernatx": {"ticker": "MRNA", "name": "Moderna, Inc.", "focus": "mRNA, Oncology Neoantigens, Vaccines"},
    "biontech": {"ticker": "BNTX", "name": "BioNTech SE", "focus": "mRNA, CAR-T, Bispecific Antibodies"},
    "curevac": {"ticker": "CVAC", "name": "CureVac N.V.", "focus": "mRNA Therapeutics"},

    # Gene Editing & RNA Interference
    "crispr therapeutics": {"ticker": "CRSP", "name": "CRISPR Therapeutics AG", "focus": "CRISPR/Cas9 Gene Editing"},
    "intellia therapeutics": {"ticker": "NTLA", "name": "Intellia Therapeutics, Inc.", "focus": "In-vivo CRISPR Editing"},
    "beam therapeutics": {"ticker": "BEAM", "name": "Beam Therapeutics Inc.", "focus": "Base Editing, Genetic Disease"},
    "alnylam": {"ticker": "ALNY", "name": "Alnylam Pharmaceuticals, Inc.", "focus": "RNAi (RNA Interference)"},
    "ionis": {"ticker": "IONS", "name": "Ionis Pharmaceuticals, Inc.", "focus": "Antisense Oligonucleotides (ASO)"},
    "sarepta": {"ticker": "SRPT", "name": "Sarepta Therapeutics, Inc.", "focus": "Gene Therapy, Duchenne Muscular Dystrophy"},

    # Metabolic & Obesity (GLP-1 / Dual-Triple Agonists)
    "viking therapeutics": {"ticker": "VKTX", "name": "Viking Therapeutics, Inc.", "focus": "GLP-1/GIP Agonists, NASH/MASH, Obesity"},
    "altimmune": {"ticker": "ALT", "name": "Altimmune, Inc.", "focus": "GLP-1/Glucagon Dual Agonists"},
    "zealand pharma": {"ticker": "ZEAL.CO", "name": "Zealand Pharma A/S", "focus": "Amylin Analogs, Peptide Therapeutics"},

    # Precision Oncology & Small Molecules
    "vertex": {"ticker": "VRTX", "name": "Vertex Pharmaceuticals Inc.", "focus": "CFTR Modulators, Pain, CRISPR Partner"},
    "seagen": {"ticker": "PFE", "name": "Pfizer (acquired Seagen)", "focus": "Antibody-Drug Conjugates (ADC)"},
    "daiichi sankyo": {"ticker": "DSNKY", "name": "Daiichi Sankyo Company", "focus": "Antibody-Drug Conjugates (ADC)"},
    "incyte": {"ticker": "INCY", "name": "Incyte Corporation", "focus": "JAK Inhibitors, Hematology"},
    "blueprint medicines": {"ticker": "BPMC", "name": "Blueprint Medicines Corp.", "focus": "Kinase Inhibitors, Mastocytosis"},
    "revolution medicines": {"ticker": "RVMD", "name": "Revolution Medicines, Inc.", "focus": "RAS(ON) Multi-Target Inhibitors"},
    "mirati": {"ticker": "BMY", "name": "Bristol Myers Squibb (Mirati)", "focus": "KRAS G12C Inhibitors"},
    "kura oncology": {"ticker": "KURA", "name": "Kura Oncology, Inc.", "focus": "Menin-MLL Inhibitors, Leukemia"},

    # Central Nervous System & Rare Disease
    "karuna therapeutics": {"ticker": "BMY", "name": "Bristol Myers Squibb (Karuna)", "focus": "Muscarinic Agonists, Schizophrenia"},
    "sage therapeutics": {"ticker": "SAGE", "name": "Sage Therapeutics, Inc.", "focus": "GABA/NMDA Neuroactive Steroids"},
    "intra-cellular therapies": {"ticker": "ITCI", "name": "Intra-Cellular Therapies, Inc.", "focus": "Lumateperone, CNS Disorders"},
    "bridgebio pharma": {"ticker": "BBIO", "name": "BridgeBio Pharma, Inc.", "focus": "Genetic Diseases, ATTR Amyloidosis"},
    "alector": {"ticker": "ALEC", "name": "Alector, Inc.", "focus": "Immuno-Neurology, Alzheimer's"},

    # Large Pharma Reference Sponsors
    "eli lilly": {"ticker": "LLY", "name": "Eli Lilly and Company", "focus": "Incretins/GLP-1, Oncology, Neuro"},
    "novo nordisk": {"ticker": "NVO", "name": "Novo Nordisk A/S", "focus": "Semaglutide, Obesity, Diabetes"},
    "pfizer": {"ticker": "PFE", "name": "Pfizer Inc.", "focus": "Vaccines, Oncology, Immunology"},
    "merck": {"ticker": "MRK", "name": "Merck & Co., Inc.", "focus": "Keytruda, Oncology, mRNA Vaccines Partner"},
    "regeneron": {"ticker": "REGN", "name": "Regeneron Pharmaceuticals", "focus": "VelocImmune Monoclonals, Dupixent"},
}

# High priority therapeutic areas and modalities to scan
THERAPEUTIC_AREAS = [
    "mRNA Vaccines & Therapeutics",
    "Oncology - KRAS & Targeted Kinases",
    "Oncology - Antibody Drug Conjugates (ADC)",
    "Metabolic - GLP-1 & Incretin Mimetics",
    "Cell & Gene Therapy (CRISPR / CAR-T)",
    "Neurodegenerative (Alzheimer's & Parkinson's)",
    "Rare Genetic Diseases",
]
