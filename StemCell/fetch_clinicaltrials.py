import csv
import json
import time
import urllib.request
import urllib.parse

BASE = "https://clinicaltrials.gov/api/v2/studies"
FIELDS = ",".join([
    "NCTId", "BriefTitle", "OverallStatus", "Phase", "StudyType",
    "Condition", "LeadSponsorName", "LeadSponsorClass",
    "InterventionName", "InterventionType", "StartDate", "CompletionDate",
    "LocationCountry", "OrgFullName", "StudyFirstPostDate",
])

OUT_JSON = "/Work1/Zijiang/StemCell/raw_studies.jsonl"
OUT_CSV = "/Work1/Zijiang/StemCell/clinicaltrials_stem_cell.csv"


def fetch_all(query_term='"stem cell"', page_size=1000):
    token = None
    total = 0
    with open(OUT_JSON, "w") as fout:
        while True:
            params = {
                "query.term": query_term,
                "pageSize": page_size,
                "fields": FIELDS,
                "countTotal": "true",
            }
            if token:
                params["pageToken"] = token
            url = BASE + "?" + urllib.parse.urlencode(params)
            for attempt in range(5):
                try:
                    with urllib.request.urlopen(url, timeout=60) as resp:
                        data = json.load(resp)
                    break
                except Exception as e:
                    print("retry", attempt, e)
                    time.sleep(3)
            else:
                raise RuntimeError("failed after retries")

            studies = data.get("studies", [])
            for s in studies:
                fout.write(json.dumps(s) + "\n")
            total += len(studies)
            print(f"fetched {total} (page has {len(studies)})")
            token = data.get("nextPageToken")
            if not token or not studies:
                break
    return total


def get(d, *path, default=None):
    cur = d
    for p in path:
        if cur is None:
            return default
        cur = cur.get(p)
    return cur if cur is not None else default


def flatten():
    rows = []
    with open(OUT_JSON) as f:
        for line in f:
            s = json.loads(line)
            ps = s.get("protocolSection", {})
            ident = ps.get("identificationModule", {})
            status = ps.get("statusModule", {})
            sponsor = ps.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {})
            conditions = ps.get("conditionsModule", {}).get("conditions", []) or []
            design = ps.get("designModule", {})
            interventions = ps.get("armsInterventionsModule", {}).get("interventions", []) or []
            locations = ps.get("contactsLocationsModule", {}).get("locations", []) or []

            countries = []
            for loc in locations:
                c = loc.get("country")
                if c and c not in countries:
                    countries.append(c)

            interv_names = [i.get("name", "") for i in interventions if i.get("name")]
            interv_types = sorted(set(i.get("type", "") for i in interventions if i.get("type")))

            rows.append({
                "NCT_ID": ident.get("nctId", ""),
                "Title": ident.get("briefTitle", ""),
                "Org": get(ident, "organization", "fullName", default=""),
                "Condition": "; ".join(conditions),
                "Sponsor": sponsor.get("name", ""),
                "Sponsor_Class": sponsor.get("class", ""),
                "Phase": "; ".join(design.get("phases", []) or []),
                "Study_Type": design.get("studyType", ""),
                "Overall_Status": status.get("overallStatus", ""),
                "Intervention_Name": "; ".join(interv_names),
                "Intervention_Type": "; ".join(interv_types),
                "Start_Date": get(status, "startDateStruct", "date", default=""),
                "Completion_Date": get(status, "completionDateStruct", "date", default=""),
                "First_Posted": get(status, "studyFirstPostDateStruct", "date", default=""),
                "Countries": "; ".join(countries),
                "URL": f"https://clinicaltrials.gov/study/{ident.get('nctId','')}",
            })
    with open(OUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows to {OUT_CSV}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "flatten":
        flatten()
    else:
        fetch_all()
        flatten()
