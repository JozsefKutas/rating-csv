import argparse
import csv
from datetime import date
from typing import Literal, Callable, Optional
from zipfile import ZipFile

try:
    from lxml import etree
except ImportError:
    import xml.etree.ElementTree as etree


RATINGS_NAMESPACE = "{http://xbrl.sec.gov/ratings/2015-03-31}"  # noqa

SEQUENCE_TAGS = {
    RATINGS_NAMESPACE + "OD": RATINGS_NAMESPACE + "ORD",
    RATINGS_NAMESPACE + "ISD": RATINGS_NAMESPACE + "IND",
    RATINGS_NAMESPACE + "IND": RATINGS_NAMESPACE + "IRD"
}

AGENCY_FIELDS = {
    "RAN": "rating_agency_name",
    "FCD": "file_creation_date"
}

OBLIGOR_FIELDS = {
    "OSC": "obligor_subclass",
    "OIG": "obligor_industry_group",
    "OBNAME": "obligor_name",
    "LEI": "legal_entity_identifier",
    "CIK": "central_index_key",
    "OI": "obligor_identifier",
    "OIS": "obligor_identifier_schema",
    "OIOS": "obligor_identifier_other_schema"
}

ISSUER_FIELDS = {
    "SSC": "sec_subcategory",
    "IG": "industry_group",
    "ISSNAME": "issuer_name",
    "ISI": "issuer_identifier",
    "ISIS": "issuer_identifier_scheme",
    "ISIOS": "issuer_identifier_other_scheme",
    "OBT": "object_type",
    "INSTNAME": "instrument_name",
    "CUSIP": "cusip",
    "INI": "instrument_identifier",
    "INIS": "instrument_identifier_scheme",
    "INIOS": "instrument_identifier_other_scheme",
    "IRTD": "interest_rate_type_description",
    "CR": "coupon_rate",
    "MD": "maturity_date",
    "PV": "par_value",
    "ISUD": "issuance_date",
    "RODC": "other_debt_category"
}

RATING_FIELDS = {
    "IP": "issuer_paid",
    "R": "rating",
    "RAD": "rating_action_date",
    "RAC": "rating_action_classification",
    "WST": "watch_status",
    "ROL": "rating_outlook",
    "OAN": "other_announcement",
    "RT": "rating_type",
    "RST": "rating_subtype",
    "RTT": "rating_type_term"
}

RatingType = Literal["obligor", "issuer"]


def ratings_to_csv(
        zip_path: str,
        csv_path: str,
        rating_type: RatingType,
        asof: Optional[date] = None) -> None:

    if rating_type == "obligor":
        fieldnames = list(AGENCY_FIELDS | OBLIGOR_FIELDS | RATING_FIELDS)
    elif rating_type == "issuer":
        fieldnames = list(AGENCY_FIELDS | ISSUER_FIELDS | RATING_FIELDS)
    else:
        raise ValueError("Invalid rating type: " + rating_type)

    with open(csv_path, "w", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        with ZipFile(zip_path, "r") as zip_file:
            for filename in zip_file.namelist():
                if not filename.endswith(".xml"):
                    continue
                try:
                    with zip_file.open(filename) as file:
                        tree = etree.parse(file)
                    records = xml_to_records(tree, rating_type, asof)
                    writer.writerows(records)
                except UnicodeEncodeError:
                    pass


def xml_to_records(
        tree: etree.ElementTree,
        rating_type: RatingType,
        asof: Optional[date] = None) -> list[dict[str, str]]:

    root = tree.getroot()
    if rating_type == "obligor":
        element = root.find(".//" + RATINGS_NAMESPACE + "OD")
    elif rating_type == "issuer":
        element = root.find(".//" + RATINGS_NAMESPACE + "ISD")
    else:
        raise ValueError("Invalid rating type: " + rating_type)

    if element is not None:
        transformation = None if asof is None else filter_asof(asof)
        records = element_to_records(element, transformation)
        ran = root.findtext(".//" + RATINGS_NAMESPACE + "RAN")
        fcd = root.findtext(".//" + RATINGS_NAMESPACE + "FCD")
        for record in records:
            record["RAN"] = ran
            record["FCD"] = fcd
        return records
    else:
        return []


def element_to_records(
        element: etree.Element,
        transformation: Optional[Callable]) -> list[dict[str, str]]:

    this = {}
    records = []
    sequence_tag = SEQUENCE_TAGS.get(element.tag)

    stack = list(element)[::-1]
    while stack:
        e = stack.pop()
        if e.tag == sequence_tag:
            # process each element in sequence
            records.extend(element_to_records(e, transformation))
        elif len(e):
            # ignore other non-leaf nodes and add children to stack
            stack.extend(list(e)[::-1])
        else:
            # extract text from leaf nodes
            this[e.tag[40:]] = e.text

    if sequence_tag is None:
        records = [this]
    else:
        for record in records:
            record.update(this)

    if transformation is None:
        return records
    else:
        return transformation(records, element)


def filter_asof(asof: date) -> Callable:
    rating_detail_tags = [RATINGS_NAMESPACE + "OD", RATINGS_NAMESPACE + "IND"]

    def filter_records(records, element):
        if element.tag in rating_detail_tags:
            # this will hold the most recent ratings for each rating type
            by_type = {}
            # iterate through ratings and update
            for record in records:
                rad = date.fromisoformat(record["RAD"])
                if rad > asof:
                    # rating is after asof date
                    continue
                key = record.get("RT"), record.get("RST"), record.get("RTT")
                old = by_type.get(key)
                if old is None or date.fromisoformat(old["RAD"]) < rad:
                    # rating is most recent encountered so far
                    by_type[key] = record
            return by_type.values()
        else:
            return records

    return filter_records


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="rating-csv",
        description="Converts XBRL files using the Record of Credit Ratings "
                    "(ROCR) taxonomy to CSV.")
    parser.add_argument(
        "zip_path",
        help="The path of the ZIP archive containing the XBRL files to read.")
    parser.add_argument(
        "csv_path",
        help="The path of the CSV file to write to.")
    parser.add_argument(
        "rating_type",
        choices=["obligor", "issuer"],
        help="The type of ratings to extract.")
    parser.add_argument(
        "--asof",
        type=date.fromisoformat,
        help="If specified, only extract the most recent ratings as of this "
             "date. Must be in ISO 8601 format.")
    args = parser.parse_args()
    ratings_to_csv(args.zip_path, args.csv_path, args.rating_type, args.asof)
