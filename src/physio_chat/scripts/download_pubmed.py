#!/usr/bin/env python3
import csv
import time
from pathlib import Path

import requests
from Bio import Entrez
import xml.etree.ElementTree as ET

# Script for pulling pubmed articles
# Created by ChatGPT
# -------- Configuration --------

EMAIL = "tara.reman@hesav.ch"  # Replace with your email
QUERY = (
    '(endometriosis AND physiotherapy [TIAB]) '
    'OR (endometriosis AND "physical therapy" [TIAB]) '
    'AND "last 10 years"[dp] '
    'AND free full text[sb] '
)
MAX_ARTICLES = 500
OUTPUT_DIR = Path("pubmed_pdfs")

AWS_BUCKET = "https://pmc-oa-opendata.s3.amazonaws.com"

Entrez.email = EMAIL
Entrez.tool = "PubmedPDFCollector"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

session = requests.Session()
session.headers.update({
    "User-Agent": f"PubmedPDFCollector/1.0 (mailto:{EMAIL})"
})

def get_json(url, params=None):
    """Retrieve JSON with basic retry handling."""
    for attempt in range(3):
        try:
            response = session.get(
                url, params=params, timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            if attempt == 2:
                return {}
            time.sleep(2 ** attempt)
    return {}


def search_pubmed(query, limit):
    """Get PubMed IDs matching a search query."""
    with Entrez.esearch(
        db="pubmed", term=query, retmax=limit
    ) as handle:
        result = Entrez.read(handle)

    print(f"Total PubMed matches: {result['Count']}")
    return result["IdList"]



def get_pmc_versions(pmcid):
    """List available AWS versions for a PMCID."""

    response = session.get(
        AWS_BUCKET + "/",
        params={
            "list-type": "2",
            "prefix": f"{pmcid}.",
            "delimiter": "/"
        },
        timeout=30
    )
    response.raise_for_status()

    root = ET.fromstring(response.content)
    ns = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}

    versions = []

    for element in root.findall("s3:CommonPrefixes", ns):
        prefix = element.findtext("s3:Prefix", namespaces=ns)
        if prefix:
            version = prefix.rstrip("/")
            versions.append(version)

    return sorted(
        versions,
        key=lambda v: int(v.rsplit(".", 1)[-1]),
        reverse=True
    )


def aws_pmc_pdf(pmcid):
    """Find an available PMC PDF using the AWS Cloud Service."""

    if not pmcid:
        return None

    versions = get_pmc_versions(pmcid)

    for version in versions:
        metadata_url = (
            f"{AWS_BUCKET}/metadata/{version}.json"
        )

        response = session.get(metadata_url, timeout=30)

        if response.status_code == 404:
            continue

        response.raise_for_status()
        metadata = response.json()

        pdf_url = metadata.get("pdf_url")

        if pdf_url:
            # NCBI metadata may describe objects using S3 URLs.
            if pdf_url.startswith("s3://pmc-oa-opendata/"):
                pdf_url = pdf_url.replace(
                    "s3://pmc-oa-opendata/",
                    AWS_BUCKET + "/",
                    1
                )

            return pdf_url

    return None



def get_metadata(pmids):
    """Retrieve DOI, PMCID, and title for each PubMed ID."""
    articles = []

    for start in range(0, len(pmids), 100):
        batch = pmids[start:start + 100]

        with Entrez.efetch(
            db="pubmed",
            id=",".join(batch),
            retmode="xml"
        ) as handle:
            records = Entrez.read(handle)

        for record in records["PubmedArticle"]:
            citation = record["MedlineCitation"]
            pmid = str(citation["PMID"])
            title = str(citation["Article"]["ArticleTitle"])

            doi = None
            pmcid = None

            for identifier in record["PubmedData"]["ArticleIdList"]:
                id_type = identifier.attributes.get("IdType")

                if id_type == "doi":
                    doi = str(identifier)
                elif id_type == "pmc":
                    pmcid = str(identifier)

            articles.append({
                "pmid": pmid,
                "pmcid": pmcid,
                "doi": doi,
                "title": title
            })

        time.sleep(0.4)

    return articles


def europe_pmc_pdf(pmid):
    """Find a PDF link using Europe PMC metadata."""
    url = (
        "https://www.ebi.ac.uk/europepmc/"
        f"webservices/rest/article/MED/{pmid}"
    )

    data = get_json(
        url, {"format": "json", "resultType": "core"}
    )

    links = data.get("result", {}).get(
        "fullTextUrlList", {}
    ).get("fullTextUrl", [])

    for item in links:
        if item.get("documentStyle", "").lower() == "pdf":
            return item.get("url")

    return None


def unpaywall_pdf(doi):
    """Find an open-access PDF using the DOI."""
    if not doi:
        return None

    data = get_json(
        f"https://api.unpaywall.org/v2/{doi}",
        {"email": EMAIL}
    )

    locations = [
        data.get("best_oa_location"),
        *data.get("oa_locations", [])
    ]

    for location in locations:
        if location and location.get("url_for_pdf"):
            return location["url_for_pdf"]

    return None


def download_pdf(url, destination):
    """Download and verify that the file is a PDF."""
    if destination.exists():
        return True

    temporary = destination.with_suffix(".part")

    try:
        with session.get(
            url, stream=True, timeout=60
        ) as response:
            response.raise_for_status()

            with open(temporary, "wb") as f:
                for chunk in response.iter_content(65536):
                    if chunk:
                        f.write(chunk)

        with open(temporary, "rb") as f:
            valid = f.read(5) == b"%PDF-"

        if valid:
            temporary.replace(destination)
            return True

    except requests.RequestException as error:
        print(f"  Download error: {error}")

    finally:
        temporary.unlink(missing_ok=True)

    return False


def main():
    pmids = search_pubmed(QUERY, MAX_ARTICLES)
    articles = get_metadata(pmids)
    results = []

    for i, article in enumerate(articles, 1):

        pmid = article["pmid"]
        destination = OUTPUT_DIR / f"PMID_{pmid}.pdf"

        print(f"[{i}/{len(articles)}] {article['title'][:75]}")

        status = "Not found"
        source = ""

        if destination.exists():
            status = "Already downloaded"
        else:
            urls = []

            if article["pmcid"]:
                try:
                    aws_url = aws_pmc_pdf(article["pmcid"])

                    if aws_url:
                        urls.append(aws_url)

                except (requests.RequestException, ET.ParseError) as error:
                    print(f"  AWS lookup failed: {error}")

            # Fall back to Unpaywall
            unpaywall_url = unpaywall_pdf(article["doi"])

            if unpaywall_url:
                urls.append(unpaywall_url)

            for url in dict.fromkeys(urls):
                if download_pdf(url, destination):
                    status = "Downloaded"
                    source = url
                    break

                time.sleep(1)

        results.append({
            **article,
            "status": status,
            "pdf_url": source
        })

        print(f"  {status}")
        time.sleep(1)

    with open(
        OUTPUT_DIR / "results.csv",
        "w",
        newline="",
        encoding="utf-8"
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["pmid", "pmcid", "doi", "title", "status", "pdf_url"]
        )
        writer.writeheader()
        writer.writerows(results)

    print("\nFinished!")
    print(f"Results saved in: {OUTPUT_DIR.resolve()}")


if __name__ == "__main__":
    main()

# Try AWS first, then Unpaywall

