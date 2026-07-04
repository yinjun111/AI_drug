"""
Step 2 — Rule-based chronic-use and disease-category classifier.
No external API calls — uses INN stem/suffix patterns + keyword rules.
Input:  orangebook_merged_by_ingredient.csv
Output: orangebook_classified.csv (adds Disease_Category, Duration_Class)
"""

import csv
import re

IN  = "orangebook_merged_by_ingredient.csv"
OUT = "orangebook_classified.csv"

# Salt/form suffixes to strip before pattern matching
_SALT_RE = re.compile(
    r"\s+(hydrochloride|hcl|maleate|fumarate|tartrate|succinate|besylate|mesylate"
    r"|tosylate|sulfate|sodium|potassium|calcium|magnesium|zinc|acetate|citrate"
    r"|phosphate|stearate|bromide|iodide|chloride|nitrate|oxalate|gluconate"
    r"|glucuronate|benzoate|diacetate|dipropionate|propionate|valerate|butyrate"
    r"|laurate|palmitate|oleate|undecylenate|hexanoate|decanoate|cypionate|enanthate"
    r"|pamoate|embonate|tannate|glubionate|lactate|malonate|aspartate|glutamate"
    r"|dimesylate|saccharate|bitartrate|monohydrate|dihydrate|hemihydrate|anhydrous"
    r"|monosodium|disodium|trisodium|bisodium|bicalcium|hemicalcium"
    r"|trihydrate|tetrahydrate|sesquihydrate|hydrate|solvate|base|free acid"
    r"|hydroiodide|hydrobromide|sulfonate|bisulfate|bisulfite|nitrite"
    r"|olamine|meglumine|diethanolamine|lysinate|ethanolamine|piperazine"
    r"|dihcl|dihydrochloride|trihydrochloride|monohydrochloride"
    r"|micronized|micronised|nanoparticle|liposomal|pegylated|peg"
    r"|f-18|f 18|tc-99m|tc 99m"
    # pro-drug / ester forms
    r"|medoxomil|hyclate|acetonide|furoate|pivalate|pivaloate|cilexetil"
    r"|mofetil|axetil|doxil|dipivoxil|pivoxil|aceponate|ebuxil|darunavir"
    r"|etabonate|probutate|caproate|valproate"
    r")\b.*$",
    re.IGNORECASE,
)

def _normalize(name: str) -> str:
    """Lowercase, strip salt/form suffixes for pattern matching."""
    n = name.lower().strip()
    n = _SALT_RE.sub("", n).strip()
    return n

# ── INN suffix → (disease_category, duration_class) ─────────────────────────
# Longest suffix first to avoid spurious partial matches.
SUFFIX_RULES = [
    # Cardiovascular / hypertension
    (r"pril$",      "Cardiovascular",  "CHRONIC"),   # ACE inhibitors (lisinopril, enalapril)
    (r"sartan$",    "Cardiovascular",  "CHRONIC"),   # ARBs (losartan, valsartan)
    (r"olol$",      "Cardiovascular",  "CHRONIC"),   # beta-blockers (metoprolol, atenolol)
    (r"alol$",      "Cardiovascular",  "CHRONIC"),   # labetalol
    (r"ilol$",      "Cardiovascular",  "CHRONIC"),   # carvedilol
    (r"dipine$",    "Cardiovascular",  "CHRONIC"),   # CCBs (amlodipine, nifedipine)
    (r"verapamil$", "Cardiovascular",  "CHRONIC"),
    (r"diltiaz",    "Cardiovascular",  "CHRONIC"),
    (r"nitrate$",   "Cardiovascular",  "PERIODIC"),  # nitrates (PRN)
    (r"nitrite$",   "Cardiovascular",  "PERIODIC"),
    (r"digoxin",    "Cardiovascular",  "CHRONIC"),
    (r"amiodarone", "Cardiovascular",  "CHRONIC"),
    (r"dronedar",   "Cardiovascular",  "CHRONIC"),
    (r"flecainide", "Cardiovascular",  "CHRONIC"),
    (r"ivabradine", "Cardiovascular",  "CHRONIC"),
    (r"sacubatril",  "Cardiovascular",  "CHRONIC"),
    (r"ranolazine", "Cardiovascular",  "CHRONIC"),
    (r"hydralazine","Cardiovascular",  "CHRONIC"),
    (r"clonidine",  "Cardiovascular",  "CHRONIC"),
    (r"methyldopa", "Cardiovascular",  "CHRONIC"),
    (r"doxazosin",  "Cardiovascular",  "CHRONIC"),
    (r"prazosin",   "Cardiovascular",  "CHRONIC"),
    (r"terazosin",  "Cardiovascular",  "CHRONIC"),
    (r"spironolact", "Cardiovascular", "CHRONIC"),
    (r"eplerenone", "Cardiovascular",  "CHRONIC"),
    (r"finerenone", "Cardiovascular",  "CHRONIC"),
    (r"warfarin",   "Cardiovascular",  "CHRONIC"),
    (r"apixaban",   "Cardiovascular",  "CHRONIC"),
    (r"rivaroxaban","Cardiovascular",  "CHRONIC"),
    (r"dabigatran", "Cardiovascular",  "CHRONIC"),
    (r"edoxaban",   "Cardiovascular",  "CHRONIC"),
    (r"clopidogrel","Cardiovascular",  "CHRONIC"),
    (r"prasugrel",  "Cardiovascular",  "CHRONIC"),
    (r"ticagrelor", "Cardiovascular",  "CHRONIC"),
    (r"aspirin",    "Cardiovascular",  "CHRONIC"),
    (r"cilostazol", "Cardiovascular",  "CHRONIC"),
    (r"isosorbide", "Cardiovascular",  "PERIODIC"),
    (r"ivermectin", "Infectious",      "SHORT"),

    # Lipid / metabolic
    (r"statin$",    "Metabolic",       "CHRONIC"),   # statins
    (r"vastatin$",  "Metabolic",       "CHRONIC"),
    (r"fibrate$",   "Metabolic",       "CHRONIC"),   # fibrates
    (r"ezetimibe",  "Metabolic",       "CHRONIC"),
    (r"colesevelam","Metabolic",       "CHRONIC"),
    (r"cholestyramine","Metabolic",    "CHRONIC"),
    (r"colestipol", "Metabolic",       "CHRONIC"),
    (r"niacin",     "Metabolic",       "CHRONIC"),
    (r"icosapent",  "Metabolic",       "CHRONIC"),
    (r"omega.3",    "Metabolic",       "CHRONIC"),

    # Diabetes / metabolic
    (r"gliptin$",   "Metabolic",       "CHRONIC"),   # DPP-4 inhibitors (sitagliptin)
    (r"gliflozin$", "Metabolic",       "CHRONIC"),   # SGLT-2 (empagliflozin)
    (r"glutide$",   "Metabolic",       "CHRONIC"),   # GLP-1 (semaglutide, liraglutide)
    (r"tirzepatide","Metabolic",       "CHRONIC"),   # dual GIP/GLP-1 (Mounjaro/Zepbound)
    (r"retatrutide","Metabolic",       "CHRONIC"),   # triple agonist
    (r"survodutide","Metabolic",       "CHRONIC"),
    (r"exenatide",  "Metabolic",       "CHRONIC"),   # GLP-1 (Byetta/Bydureon)
    (r"lixisenatide","Metabolic",      "CHRONIC"),
    (r"setmelanotide","Metabolic",     "CHRONIC"),   # MC4R agonist — chronic obesity
    (r"vosoritide", "Metabolic",       "CHRONIC"),   # achondroplasia (CNP analog)
    (r"navepegritide","Metabolic",     "CHRONIC"),   # achondroplasia
    (r"etelcalcetide","Metabolic",     "CHRONIC"),   # 2° hyperparathyroidism (dialysis)
    (r"elamipretide","Metabolic",      "CHRONIC"),   # Barth syndrome (mitochondrial)
    (r"trofinetide","Neurology",       "CHRONIC"),   # Rett syndrome
    (r"ziconotide", "Pain",            "CHRONIC"),   # severe chronic pain (intrathecal)
    (r"glimepirid", "Metabolic",       "CHRONIC"),
    (r"glipizide",  "Metabolic",       "CHRONIC"),
    (r"glyburide",  "Metabolic",       "CHRONIC"),
    (r"glibenclamide","Metabolic",     "CHRONIC"),
    (r"metformin",  "Metabolic",       "CHRONIC"),
    (r"acarbose",   "Metabolic",       "CHRONIC"),
    (r"miglitol",   "Metabolic",       "CHRONIC"),
    (r"pioglitazone","Metabolic",      "CHRONIC"),
    (r"rosiglitazone","Metabolic",     "CHRONIC"),
    (r"repaglinide","Metabolic",       "CHRONIC"),
    (r"nateglinide","Metabolic",       "CHRONIC"),
    (r"insulin",    "Metabolic",       "CHRONIC"),
    (r"pramlintide","Metabolic",       "CHRONIC"),
    (r"dulaglutide","Metabolic",       "CHRONIC"),

    # Thyroid / hormonal metabolic
    (r"levothyroxine","Metabolic",     "CHRONIC"),
    (r"liothyronine","Metabolic",      "CHRONIC"),
    (r"methimazole","Metabolic",       "CHRONIC"),
    (r"propylthiouracil","Metabolic",  "CHRONIC"),

    # Bone / metabolic
    (r"dronate$",   "Metabolic",       "CHRONIC"),   # bisphosphonates
    (r"alendronate","Metabolic",       "CHRONIC"),
    (r"risedronate","Metabolic",       "CHRONIC"),
    (r"ibandronate","Metabolic",       "CHRONIC"),
    (r"zoledronic","Metabolic",        "CHRONIC"),
    (r"teriparatide","Metabolic",      "CHRONIC"),
    (r"abaloparatide","Metabolic",     "CHRONIC"),
    (r"raloxifene", "Metabolic",       "CHRONIC"),
    (r"calcitonin", "Metabolic",       "CHRONIC"),

    # Psychiatric / CNS
    (r"oxetine$",   "Psychiatric",     "CHRONIC"),   # SSRIs/SNRIs (fluoxetine, paroxetine)
    (r"citalopram$","Psychiatric",     "CHRONIC"),   # escitalopram, citalopram
    (r"venlafaxine","Psychiatric",     "CHRONIC"),
    (r"duloxetine", "Psychiatric",     "CHRONIC"),
    (r"desvenlafaxine","Psychiatric",  "CHRONIC"),
    (r"mirtazapine","Psychiatric",     "CHRONIC"),
    (r"bupropion",  "Psychiatric",     "CHRONIC"),
    (r"trazodone",  "Psychiatric",     "CHRONIC"),
    (r"amitriptyline","Psychiatric",   "CHRONIC"),
    (r"nortriptyline","Psychiatric",   "CHRONIC"),
    (r"clomipramine","Psychiatric",    "CHRONIC"),
    (r"imipramine", "Psychiatric",     "CHRONIC"),
    (r"doxepin",    "Psychiatric",     "CHRONIC"),
    (r"apine$",     "Psychiatric",     "CHRONIC"),   # antipsychotics (olanzapine, clozapine, quetiapine)
    (r"idone$",     "Psychiatric",     "CHRONIC"),   # risperidone, paliperidone, ziprasidone
    (r"aripip",     "Psychiatric",     "CHRONIC"),   # aripiprazole
    (r"haloperidol","Psychiatric",     "CHRONIC"),
    (r"lithium",    "Psychiatric",     "CHRONIC"),
    (r"valproic",   "Psychiatric",     "CHRONIC"),
    (r"lamotrigine","Psychiatric",     "CHRONIC"),
    (r"carbamazepine","Psychiatric",   "CHRONIC"),
    (r"oxcarbazepine","Psychiatric",   "CHRONIC"),
    (r"topiramate", "Psychiatric",     "CHRONIC"),
    (r"levetirac",  "Neurology",       "CHRONIC"),   # levetiracetam
    (r"pregabalin", "Neurology",       "CHRONIC"),
    (r"gabapentin", "Neurology",       "CHRONIC"),
    (r"phenytoin",  "Neurology",       "CHRONIC"),
    (r"phenobarb",  "Neurology",       "CHRONIC"),
    (r"zonisamide", "Neurology",       "CHRONIC"),
    (r"lacosamide", "Neurology",       "CHRONIC"),
    (r"perampanel", "Neurology",       "CHRONIC"),
    (r"vigabatrin", "Neurology",       "CHRONIC"),
    (r"rufinamide", "Neurology",       "CHRONIC"),
    (r"stiripentol","Neurology",       "CHRONIC"),
    (r"cannabidiol","Neurology",       "CHRONIC"),
    (r"alprazolam", "Psychiatric",     "PERIODIC"),  # benzodiazepines — often chronic but ideally short
    (r"diazepam",   "Psychiatric",     "PERIODIC"),
    (r"clonazepam", "Psychiatric",     "CHRONIC"),
    (r"lorazepam",  "Psychiatric",     "PERIODIC"),
    (r"buspirone",  "Psychiatric",     "CHRONIC"),
    (r"hydroxyzine","Psychiatric",     "PERIODIC"),
    (r"zolpidem",   "Psychiatric",     "PERIODIC"),
    (r"eszopiclone","Psychiatric",     "PERIODIC"),

    # Neurology — specific
    (r"triptan$",   "Neurology",       "PERIODIC"),  # triptans — acute migraine, not chronic
    (r"sumatriptan","Neurology",       "PERIODIC"),
    (r"rizatriptan","Neurology",       "PERIODIC"),
    (r"almotriptan","Neurology",       "PERIODIC"),
    (r"eletriptan", "Neurology",       "PERIODIC"),
    (r"frovatriptan","Neurology",      "PERIODIC"),
    (r"naratriptan","Neurology",       "PERIODIC"),
    (r"zolmitriptan","Neurology",      "PERIODIC"),
    (r"erenumab",   "Neurology",       "CHRONIC"),   # CGRP antagonists (biologic)
    (r"donepezil",  "Neurology",       "CHRONIC"),
    (r"rivastigmine","Neurology",      "CHRONIC"),
    (r"galantamine","Neurology",       "CHRONIC"),
    (r"memantine",  "Neurology",       "CHRONIC"),
    (r"rasagiline",  "Neurology",      "CHRONIC"),
    (r"selegiline", "Neurology",       "CHRONIC"),
    (r"carbidopa",  "Neurology",       "CHRONIC"),
    (r"levodopa",   "Neurology",       "CHRONIC"),
    (r"pramipexole","Neurology",       "CHRONIC"),
    (r"ropinirole", "Neurology",       "CHRONIC"),
    (r"rotigotine", "Neurology",       "CHRONIC"),
    (r"entacapone", "Neurology",       "CHRONIC"),
    (r"tolcapone",  "Neurology",       "CHRONIC"),
    (r"amantadine", "Neurology",       "CHRONIC"),
    (r"riluzole",   "Neurology",       "LONG-TERM"),
    (r"baclofen",   "Neurology",       "CHRONIC"),
    (r"tizanidine", "Neurology",       "CHRONIC"),
    (r"dantrolene", "Neurology",       "PERIODIC"),

    # Respiratory
    (r"terol$",     "Respiratory",     "CHRONIC"),   # beta-agonists (albuterol, formoterol, salmeterol)
    (r"buterol$",   "Respiratory",     "CHRONIC"),
    (r"prenaline$", "Respiratory",     "CHRONIC"),
    (r"tiotropium", "Respiratory",     "CHRONIC"),
    (r"umeclidinium","Respiratory",    "CHRONIC"),
    (r"aclidinium", "Respiratory",     "CHRONIC"),
    (r"glycopyrr",  "Respiratory",     "CHRONIC"),
    (r"ipratropium","Respiratory",     "CHRONIC"),
    (r"theophylline","Respiratory",    "CHRONIC"),
    (r"aminophylline","Respiratory",   "CHRONIC"),
    (r"budesonide", "Respiratory",     "CHRONIC"),
    (r"fluticasone","Respiratory",     "CHRONIC"),
    (r"beclomethasone","Respiratory",  "CHRONIC"),
    (r"ciclesonide","Respiratory",     "CHRONIC"),
    (r"mometasone", "Respiratory",     "CHRONIC"),
    (r"triamcinolone","Respiratory",   "CHRONIC"),
    (r"montelukast","Respiratory",     "CHRONIC"),
    (r"zafirlukast","Respiratory",     "CHRONIC"),
    (r"zileuton",   "Respiratory",     "CHRONIC"),
    (r"roflumilast","Respiratory",     "CHRONIC"),

    # GI
    (r"prazole$",   "GI",              "CHRONIC"),   # PPIs (omeprazole, lansoprazole, esomeprazole)
    (r"tidine$",    "GI",              "CHRONIC"),   # H2 blockers (ranitidine, famotidine)
    (r"famotidine", "GI",              "CHRONIC"),
    (r"cimetidine", "GI",              "CHRONIC"),
    (r"misoprostol","GI",              "PERIODIC"),
    (r"sucralfate",  "GI",             "PERIODIC"),
    (r"mesalamine", "GI",              "CHRONIC"),
    (r"sulfasalazine","GI",            "CHRONIC"),
    (r"balsalazide","GI",              "CHRONIC"),
    (r"olsalazine", "GI",             "CHRONIC"),
    (r"ursodiol",   "GI",              "CHRONIC"),
    (r"cholestyramine","GI",           "CHRONIC"),
    (r"lactulose",  "GI",              "PERIODIC"),
    (r"linaclotide","GI",              "CHRONIC"),
    (r"lubiprostone","GI",             "CHRONIC"),
    (r"plecanatide","GI",              "CHRONIC"),
    (r"metoclopramide","GI",           "PERIODIC"),
    (r"ondansetron","GI",              "PERIODIC"),
    (r"domperidone","GI",              "CHRONIC"),

    # Autoimmune / immunosuppressant
    (r"methotrexate","Autoimmune",     "CHRONIC"),
    (r"azathioprine","Autoimmune",     "CHRONIC"),
    (r"mercaptopurine","Autoimmune",   "CHRONIC"),
    (r"mycophenolate","Autoimmune",    "CHRONIC"),
    (r"tacrolimus",  "Autoimmune",     "CHRONIC"),
    (r"cyclosporine","Autoimmune",     "CHRONIC"),
    (r"sirolimus",   "Autoimmune",     "CHRONIC"),
    (r"everolimus",  "Autoimmune",     "LONG-TERM"),  # also oncology use
    (r"hydroxychloroquine","Autoimmune","CHRONIC"),
    (r"chloroquine", "Autoimmune",     "CHRONIC"),
    (r"leflunomide", "Autoimmune",     "CHRONIC"),
    (r"tofacitinib", "Autoimmune",     "CHRONIC"),
    (r"baricitinib", "Autoimmune",     "CHRONIC"),
    (r"upadacitinib","Autoimmune",     "CHRONIC"),
    (r"filgotinib",  "Autoimmune",     "CHRONIC"),
    (r"abatacept",   "Autoimmune",     "CHRONIC"),

    # Infectious disease — antiretrovirals (chronic HIV management)
    (r"navir$",     "Infectious",      "CHRONIC"),   # protease inhibitors (ritonavir, darunavir)
    (r"tegravir$",  "Infectious",      "CHRONIC"),   # integrase inhibitors (dolutegravir, bictegravir)
    (r"citabine$",  "Infectious",      "CHRONIC"),   # NRTIs (emtricitabine, lamivudine)
    (r"tenofovir",  "Infectious",      "CHRONIC"),
    (r"efavirenz",  "Infectious",      "CHRONIC"),
    (r"nevirapine", "Infectious",      "CHRONIC"),
    (r"rilpivirine","Infectious",      "CHRONIC"),
    (r"doravirine", "Infectious",      "CHRONIC"),
    (r"maraviroc",  "Infectious",      "CHRONIC"),
    (r"enfuvirtide","Infectious",      "CHRONIC"),
    (r"cabotegravir","Infectious",     "CHRONIC"),
    (r"lenacapavir","Infectious",      "CHRONIC"),

    # Antibiotics (generally short-course)
    (r"cillin$",    "Infectious",      "SHORT"),     # penicillins
    (r"mycin$",     "Infectious",      "SHORT"),     # macrolides/aminoglycosides
    (r"cycline$",   "Infectious",      "SHORT"),     # tetracyclines
    (r"floxacin$",  "Infectious",      "SHORT"),     # fluoroquinolones
    (r"oxacin$",    "Infectious",      "SHORT"),
    (r"cefadroxil", "Infectious",      "SHORT"),
    (r"cephalexin", "Infectious",      "SHORT"),
    (r"cefazolin",  "Infectious",      "SHORT"),
    (r"cefdinir",   "Infectious",      "SHORT"),
    (r"cefpodoxime","Infectious",      "SHORT"),
    (r"cefuroxime", "Infectious",      "SHORT"),
    (r"ceftriaxone","Infectious",      "SHORT"),
    (r"ceftaroline","Infectious",      "SHORT"),
    (r"cefepime",   "Infectious",      "SHORT"),
    (r"cefixime",   "Infectious",      "SHORT"),
    (r"azithromycin","Infectious",     "SHORT"),
    (r"clarithromycin","Infectious",   "SHORT"),
    (r"erythromycin","Infectious",     "SHORT"),
    (r"clindamycin","Infectious",      "SHORT"),
    (r"vancomycin", "Infectious",      "SHORT"),
    (r"linezolid",  "Infectious",      "SHORT"),
    (r"tedizolid",  "Infectious",      "SHORT"),
    (r"daptomycin", "Infectious",      "SHORT"),
    (r"metronidazole","Infectious",    "SHORT"),
    (r"tinidazole", "Infectious",      "SHORT"),
    (r"trimethoprim","Infectious",     "SHORT"),
    (r"sulfamethoxazole","Infectious", "SHORT"),
    (r"nitrofurantoin","Infectious",   "SHORT"),
    (r"fosfomycin", "Infectious",      "SHORT"),
    (r"rifampin",   "Infectious",      "SHORT"),
    (r"rifabutin",  "Infectious",      "SHORT"),
    (r"isoniazid",  "Infectious",      "LONG-TERM"), # TB prophylaxis
    (r"pyrazinamide","Infectious",     "SHORT"),
    (r"ethambutol", "Infectious",      "SHORT"),

    # Antifungals
    (r"conazole$",  "Infectious",      "SHORT"),     # azole antifungals
    (r"fluconazole","Infectious",      "SHORT"),
    (r"nystatin",   "Infectious",      "SHORT"),
    (r"terbinafine","Infectious",      "SHORT"),
    (r"griseofulvin","Infectious",     "SHORT"),
    (r"amphotericin","Infectious",     "SHORT"),
    (r"caspofungin","Infectious",      "SHORT"),
    (r"micafungin", "Infectious",      "SHORT"),
    (r"anidulafungin","Infectious",    "SHORT"),

    # Antiviral (non-HIV, generally short-course or episodic)
    (r"acyclovir",  "Infectious",      "PERIODIC"),  # HSV suppression — can be long-term
    (r"valacyclovir","Infectious",     "PERIODIC"),
    (r"famciclovir","Infectious",      "PERIODIC"),
    (r"ganciclovir","Infectious",      "SHORT"),
    (r"valganciclovir","Infectious",   "CHRONIC"),   # CMV prophylaxis in transplant
    (r"oseltamivir","Infectious",      "SHORT"),
    (r"zanamivir",  "Infectious",      "SHORT"),
    (r"baloxavir",  "Infectious",      "SHORT"),
    (r"letermovir", "Infectious",      "CHRONIC"),   # CMV prophylaxis
    (r"sofosbuvir", "Infectious",      "SHORT"),
    (r"ledipasvir", "Infectious",      "SHORT"),
    (r"velpatasvir","Infectious",      "SHORT"),
    (r"daclatasvir","Infectious",      "SHORT"),
    (r"glecaprevir","Infectious",      "SHORT"),
    (r"pibrentasvir","Infectious",     "SHORT"),
    (r"elbasvir",   "Infectious",      "SHORT"),
    (r"grazoprevir","Infectious",      "SHORT"),

    # Oncology — kinase inhibitors
    (r"tinib$",     "Oncology",        "LONG-TERM"),  # TKIs (imatinib, erlotinib, dasatinib)
    (r"rafenib$",   "Oncology",        "LONG-TERM"),  # RAF inhibitors (vemurafenib, dabrafenib)
    (r"ciclib$",    "Oncology",        "LONG-TERM"),  # CDK inhibitors (palbociclib)
    (r"afenib$",    "Oncology",        "LONG-TERM"),  # EGFR inhibitors
    (r"cetinib$",   "Oncology",        "LONG-TERM"),  # ALK inhibitors
    (r"metinib$",   "Oncology",        "LONG-TERM"),  # MEK inhibitors
    (r"lisib$",     "Oncology",        "LONG-TERM"),  # PI3K inhibitors
    (r"sirolimus$", "Autoimmune",      "CHRONIC"),   # (overwritten by above if needed)
    (r"parib$",     "Oncology",        "LONG-TERM"),  # PARP inhibitors (olaparib, niraparib)
    (r"capecitabine","Oncology",       "LONG-TERM"),
    (r"temozolomide","Oncology",       "LONG-TERM"),
    (r"hydroxyurea","Oncology",        "LONG-TERM"),
    (r"thalidomide","Oncology",        "LONG-TERM"),
    (r"lenalidomide","Oncology",       "LONG-TERM"),
    (r"pomalidomide","Oncology",       "LONG-TERM"),
    (r"bexarotene", "Oncology",        "LONG-TERM"),
    (r"vorinostat",  "Oncology",       "LONG-TERM"),
    (r"romidepsin",  "Oncology",       "LONG-TERM"),
    (r"belinostat",  "Oncology",       "LONG-TERM"),
    (r"panobinostat","Oncology",       "LONG-TERM"),
    (r"venetoclax",  "Oncology",       "LONG-TERM"),
    (r"idelalisib",  "Oncology",       "LONG-TERM"),
    (r"copanlisib",  "Oncology",       "LONG-TERM"),
    (r"duvelisib",   "Oncology",       "LONG-TERM"),
    (r"vismodegib",  "Oncology",       "LONG-TERM"),
    (r"sonidegib",   "Oncology",       "LONG-TERM"),
    (r"glasdegib",   "Oncology",       "LONG-TERM"),
    (r"midostaurin", "Oncology",       "LONG-TERM"),
    (r"gilteritinib","Oncology",       "LONG-TERM"),
    (r"quizartinib", "Oncology",       "LONG-TERM"),
    (r"enasidenib",  "Oncology",       "LONG-TERM"),
    (r"ivosidenib",  "Oncology",       "LONG-TERM"),
    (r"olutasidenib","Oncology",       "LONG-TERM"),

    # Hormone therapies for cancer
    (r"fulvestrant", "Oncology",       "LONG-TERM"),
    (r"tamoxifen",   "Oncology",       "LONG-TERM"),
    (r"anastrozole", "Oncology",       "LONG-TERM"),
    (r"letrozole",   "Oncology",       "LONG-TERM"),
    (r"exemestane",  "Oncology",       "LONG-TERM"),
    (r"enzalutamide","Oncology",       "LONG-TERM"),
    (r"apalutamide", "Oncology",       "LONG-TERM"),
    (r"darolutamide","Oncology",       "LONG-TERM"),
    (r"abiraterone", "Oncology",       "LONG-TERM"),
    (r"flutamide",   "Oncology",       "LONG-TERM"),
    (r"bicalutamide","Oncology",       "LONG-TERM"),
    (r"nilutamide",  "Oncology",       "LONG-TERM"),
    (r"leuprolide",  "Oncology",       "LONG-TERM"),
    (r"goserelin",   "Oncology",       "LONG-TERM"),
    (r"triptorelin", "Oncology",       "LONG-TERM"),
    (r"degarelix",   "Oncology",       "LONG-TERM"),
    (r"relugolix",   "Oncology",       "LONG-TERM"),
    (r"elagolix",    "GI",             "CHRONIC"),  # endometriosis

    # Ophthalmology
    (r"latanoprost", "Ophthalmology",  "CHRONIC"),
    (r"bimatoprost", "Ophthalmology",  "CHRONIC"),
    (r"travoprost",  "Ophthalmology",  "CHRONIC"),
    (r"tafluprost",  "Ophthalmology",  "CHRONIC"),
    (r"timolol",     "Ophthalmology",  "CHRONIC"),  # ophthalmic beta-blocker
    (r"brimonidine", "Ophthalmology",  "CHRONIC"),
    (r"dorzolamide", "Ophthalmology",  "CHRONIC"),
    (r"brinzolamide","Ophthalmology",  "CHRONIC"),
    (r"pilocarpine", "Ophthalmology",  "CHRONIC"),
    (r"netarsudil",  "Ophthalmology",  "CHRONIC"),
    (r"omidenepag",  "Ophthalmology",  "CHRONIC"),

    # Dermatology
    (r"tretinoin",   "Dermatology",    "CHRONIC"),
    (r"isotretinoin","Dermatology",    "SHORT"),    # finite course
    (r"acitretin",   "Dermatology",    "CHRONIC"),
    (r"tazarotene",  "Dermatology",    "CHRONIC"),
    (r"calcipotriene","Dermatology",   "CHRONIC"),
    (r"crisaborole", "Dermatology",    "CHRONIC"),
    (r"ruxolitinib", "Dermatology",    "CHRONIC"),  # cream — also oncology JAK
    (r"tapinarof",   "Dermatology",    "CHRONIC"),
    (r"difamilast",  "Dermatology",    "CHRONIC"),

    # Pain / analgesics
    (r"morphine",    "Pain",           "CHRONIC"),
    (r"oxycodone",   "Pain",           "CHRONIC"),
    (r"hydrocodone", "Pain",           "CHRONIC"),
    (r"oxymorphone", "Pain",           "CHRONIC"),
    (r"hydromorphone","Pain",          "CHRONIC"),
    (r"fentanyl",    "Pain",           "CHRONIC"),
    (r"methadone",   "Pain",           "CHRONIC"),
    (r"buprenorphine","Pain",          "CHRONIC"),
    (r"naloxone",    "Pain",           "PERIODIC"),
    (r"naltrexone",  "Pain",           "CHRONIC"),
    (r"tramadol",    "Pain",           "PERIODIC"),
    (r"tapentadol",  "Pain",           "PERIODIC"),
    (r"ibuprofen",   "Pain",           "PERIODIC"),
    (r"naproxen",    "Pain",           "PERIODIC"),
    (r"diclofenac",  "Pain",           "PERIODIC"),
    (r"meloxicam",   "Pain",           "PERIODIC"),
    (r"celecoxib",   "Pain",           "PERIODIC"),
    (r"indomethacin","Pain",           "PERIODIC"),
    (r"ketorolac",   "Pain",           "SHORT"),
    (r"acetaminophen","Pain",          "PERIODIC"),
    (r"acetylsalicylic","Pain",        "PERIODIC"),
    (r"pregabalin",  "Pain",           "CHRONIC"),
    (r"duloxetine",  "Pain",           "CHRONIC"),
    (r"gabapentin",  "Pain",           "CHRONIC"),

    # Hormones / endocrine (not thyroid/diabetes above)
    (r"estradiol",   "Metabolic",      "CHRONIC"),
    (r"estrogen",    "Metabolic",      "CHRONIC"),
    (r"progesterone","Metabolic",      "CHRONIC"),
    (r"testosterone","Metabolic",      "CHRONIC"),
    (r"cortisone",   "Autoimmune",     "PERIODIC"),
    (r"prednisone",  "Autoimmune",     "PERIODIC"),
    (r"prednisolone","Autoimmune",     "PERIODIC"),
    (r"dexamethasone","Autoimmune",    "PERIODIC"),
    (r"hydrocortisone","Autoimmune",   "PERIODIC"),
    (r"fludrocortisone","Metabolic",   "CHRONIC"),
    (r"growth hormone","Metabolic",    "CHRONIC"),
    (r"somatropin",  "Metabolic",      "CHRONIC"),

    # Urology / genitourinary
    (r"finasteride", "Metabolic",      "CHRONIC"),
    (r"dutasteride", "Metabolic",      "CHRONIC"),
    (r"sildenafil",  "Cardiovascular", "CHRONIC"),
    (r"tadalafil",   "Cardiovascular", "CHRONIC"),
    (r"vardenafil",  "Cardiovascular", "CHRONIC"),
    (r"oxybutynin",  "Neurology",      "CHRONIC"),
    (r"tolterodine", "Neurology",      "CHRONIC"),
    (r"solifenacin", "Neurology",      "CHRONIC"),
    (r"darifenacin", "Neurology",      "CHRONIC"),
    (r"fesoterodine","Neurology",      "CHRONIC"),
    (r"mirabegron",  "Neurology",      "CHRONIC"),
    (r"vibegron",    "Neurology",      "CHRONIC"),
    (r"desmopressin","Metabolic",      "CHRONIC"),

    # Misc known combo ingredients (placeholder patterns)
    (r"caffeine",    "Pain",           "PERIODIC"),
    (r"ergotamine",  "Neurology",      "PERIODIC"),
    (r"dihydroergotamine","Neurology","PERIODIC"),
    (r"sumatriptan", "Neurology",      "PERIODIC"),
]

# ── Keyword rules on full ingredient string ──────────────────────────────────
KEYWORD_RULES = [
    # Cardiovascular
    (r"\bdiuretic\b",       "Cardiovascular",  "CHRONIC"),
    (r"\bfurosemide\b",     "Cardiovascular",  "CHRONIC"),
    (r"\btorasemide\b",     "Cardiovascular",  "CHRONIC"),
    (r"\btorsemide\b",      "Cardiovascular",  "CHRONIC"),
    (r"\bbumetanide\b",     "Cardiovascular",  "CHRONIC"),
    (r"\bethacrynic\b",     "Cardiovascular",  "CHRONIC"),
    (r"\bmetolazone\b",     "Cardiovascular",  "CHRONIC"),
    (r"\bchlorothiazide\b", "Cardiovascular",  "CHRONIC"),
    (r"\bhydrochlorothiazide\b","Cardiovascular","CHRONIC"),
    (r"\bchlorthalidone\b", "Cardiovascular",  "CHRONIC"),
    (r"\bindapamide\b",     "Cardiovascular",  "CHRONIC"),
    (r"\bdigoxin\b",        "Cardiovascular",  "CHRONIC"),
    (r"\bisosorbide\b",     "Cardiovascular",  "PERIODIC"),
    (r"\bnitroglycerin\b",  "Cardiovascular",  "PERIODIC"),
    (r"\baliskiren\b",      "Cardiovascular",  "CHRONIC"),
    (r"\bheparin\b",        "Cardiovascular",  "SHORT"),
    (r"\bfondaparinux\b",   "Cardiovascular",  "SHORT"),
    (r"\benoxaparin\b",     "Cardiovascular",  "SHORT"),
    (r"\bdalteparin\b",     "Cardiovascular",  "SHORT"),
    (r"\btinzaparin\b",     "Cardiovascular",  "SHORT"),

    # Metabolic
    (r"\bomega.3\b",        "Metabolic",       "CHRONIC"),
    (r"\bvitamin d\b",      "Metabolic",       "CHRONIC"),
    (r"\bcalcitriol\b",     "Metabolic",       "CHRONIC"),
    (r"\bdoxercalciferol\b","Metabolic",       "CHRONIC"),
    (r"\bparicalcitol\b",   "Metabolic",       "CHRONIC"),
    (r"\biron\b",           "Metabolic",       "CHRONIC"),
    (r"\bferrous\b",        "Metabolic",       "CHRONIC"),
    (r"\bferric\b",         "Metabolic",       "CHRONIC"),
    (r"\bfolic acid\b",     "Metabolic",       "CHRONIC"),
    (r"\bcyanocobalamin\b", "Metabolic",       "CHRONIC"),
    (r"\bhydroxocobalamin\b","Metabolic",      "CHRONIC"),
    (r"\buric acid\b",      "Metabolic",       "CHRONIC"),
    (r"\ballopurinol\b",    "Metabolic",       "CHRONIC"),
    (r"\bfebuxostat\b",     "Metabolic",       "CHRONIC"),
    (r"\bcolchicine\b",     "Metabolic",       "PERIODIC"),
    (r"\bprobenecid\b",     "Metabolic",       "CHRONIC"),
    (r"\bpegloticase\b",    "Metabolic",       "PERIODIC"),

    # GI
    (r"\bantacid\b",        "GI",              "PERIODIC"),
    (r"\bmagnesium hydroxide\b","GI",          "PERIODIC"),
    (r"\bcalcium carbonate\b","GI",            "PERIODIC"),
    (r"\bpsyllium\b",       "GI",              "CHRONIC"),
    (r"\bmethylcellulose\b","GI",              "CHRONIC"),
    (r"\bbismuth\b",        "GI",              "SHORT"),
    (r"\baluminum hydroxide\b","GI",           "PERIODIC"),
    (r"\bpancrelipase\b",   "GI",              "CHRONIC"),
    (r"\bpancreatin\b",     "GI",              "CHRONIC"),

    # Infectious — antiparasitics
    (r"\bmebendazole\b",    "Infectious",      "SHORT"),
    (r"\balbendazole\b",    "Infectious",      "SHORT"),
    (r"\bpraziquantel\b",   "Infectious",      "SHORT"),
    (r"\bpyrantel\b",       "Infectious",      "SHORT"),
    (r"\bpyrimethamine\b",  "Infectious",      "SHORT"),
    (r"\batovaquone\b",     "Infectious",      "SHORT"),
    (r"\bchloroquine\b",    "Infectious",      "SHORT"),
    (r"\bartemether\b",     "Infectious",      "SHORT"),
    (r"\blumefantrine\b",   "Infectious",      "SHORT"),
    (r"\bquinine\b",        "Infectious",      "SHORT"),
    (r"\bpentamidine\b",    "Infectious",      "SHORT"),

    # Oncology cytotoxics
    (r"\bcisplatin\b",      "Oncology",        "SHORT"),
    (r"\bcarboplatin\b",    "Oncology",        "SHORT"),
    (r"\boxaliplatin\b",    "Oncology",        "SHORT"),
    (r"\bdocetaxel\b",      "Oncology",        "LONG-TERM"),
    (r"\bpaclitaxel\b",     "Oncology",        "LONG-TERM"),
    (r"\bdoxorubicin\b",    "Oncology",        "SHORT"),
    (r"\bepirubicin\b",     "Oncology",        "SHORT"),
    (r"\bcyclophosphamide\b","Oncology",       "SHORT"),
    (r"\bifosfamide\b",     "Oncology",        "SHORT"),
    (r"\bgemcitabine\b",    "Oncology",        "LONG-TERM"),
    (r"\bfluorouracil\b",   "Oncology",        "LONG-TERM"),
    (r"\bmethotrexate\b",   "Oncology",        "LONG-TERM"),  # also autoimmune
    (r"\bpemetrexed\b",     "Oncology",        "LONG-TERM"),
    (r"\betoposide\b",      "Oncology",        "SHORT"),
    (r"\birino",            "Oncology",        "LONG-TERM"),  # irinotecan
    (r"\btopotecan\b",      "Oncology",        "LONG-TERM"),
    (r"\bvincristine\b",    "Oncology",        "SHORT"),
    (r"\bvinblastine\b",    "Oncology",        "SHORT"),
    (r"\bvinorelbine\b",    "Oncology",        "LONG-TERM"),
    (r"\beribulin\b",       "Oncology",        "LONG-TERM"),
    (r"\bcabazitaxel\b",    "Oncology",        "LONG-TERM"),
    (r"\bbleomycin\b",      "Oncology",        "SHORT"),
    (r"\bmitomycin\b",      "Oncology",        "SHORT"),

    # Anesthetics / short-acting (always SHORT)
    (r"\bpropofol\b",       "Other",           "SHORT"),
    (r"\bketamine\b",       "Other",           "SHORT"),
    (r"\betomidate\b",      "Other",           "SHORT"),
    (r"\blidocaine\b",      "Pain",            "SHORT"),
    (r"\bbupivacaine\b",    "Pain",            "SHORT"),
    (r"\brovivacaine\b",    "Pain",            "SHORT"),
    (r"\bropivacaine\b",    "Pain",            "SHORT"),
    (r"\bmepivacaine\b",    "Pain",            "SHORT"),
    (r"\bprilocaine\b",     "Pain",            "SHORT"),
    (r"\bmidazolam\b",      "Psychiatric",     "SHORT"),
    (r"\bphenobarbital\b",  "Neurology",       "CHRONIC"),

    # Vaccines
    (r"\bvaccine\b",        "Infectious",      "SHORT"),
    (r"\btoxoid\b",         "Infectious",      "SHORT"),
    (r"\bimmunoglobulin\b", "Autoimmune",      "PERIODIC"),
    (r"\bglobulin\b",       "Autoimmune",      "PERIODIC"),

    # Radioactive / contrast / diagnostic
    (r"\bradioactive\b",    "Other",           "SHORT"),
    (r"\bradiolabeled\b",   "Other",           "SHORT"),
    (r"\bcontrast\b",       "Other",           "SHORT"),
    (r"\btechnetium\b",     "Other",           "SHORT"),
    (r"\bgadolinium\b",     "Other",           "SHORT"),
    (r"\biodine.?\d",       "Other",           "SHORT"),

    # Blood products / hemostatics
    (r"\bfactor viii\b",    "Autoimmune",      "CHRONIC"),
    (r"\bfactor ix\b",      "Autoimmune",      "CHRONIC"),
    (r"\bfactor vii\b",     "Autoimmune",      "PERIODIC"),
    (r"\bfactor xiii\b",    "Autoimmune",      "PERIODIC"),
    (r"\bfibrinogen\b",     "Autoimmune",      "PERIODIC"),
    (r"\bprotamine\b",      "Cardiovascular",  "SHORT"),
    (r"\baminocaproic\b",   "Autoimmune",      "SHORT"),
    (r"\btranexamic\b",     "Autoimmune",      "SHORT"),

    # Muscle relaxants (short/periodic)
    (r"\bcyclobenzaprine\b","Pain",            "SHORT"),
    (r"\bmetaxalone\b",     "Pain",            "SHORT"),
    (r"\bmethocarbamol\b",  "Pain",            "SHORT"),
    (r"\bcaprofen\b",       "Pain",            "SHORT"),

    # Smoking cessation
    (r"\bnicotine\b",       "Psychiatric",     "SHORT"),
    (r"\bvarenicline\b",    "Psychiatric",     "SHORT"),

    # Ophthalmology — glaucoma generics
    (r"\bglaucoma\b",       "Ophthalmology",   "CHRONIC"),
    (r"\bophthalmic\b",     "Ophthalmology",   "CHRONIC"),
    (r"\bcarteolol\b",      "Ophthalmology",   "CHRONIC"),
    (r"\bmetipranolol\b",   "Ophthalmology",   "CHRONIC"),
    (r"\bbetaxolol\b",      "Ophthalmology",   "CHRONIC"),
    (r"\blevobunolol\b",    "Ophthalmology",   "CHRONIC"),

    # Dermatology
    (r"\bpermethrin\b",     "Dermatology",     "SHORT"),
    (r"\blindane\b",        "Dermatology",     "SHORT"),
    (r"\bbenzoyl peroxide\b","Dermatology",    "CHRONIC"),
    (r"\bsalicylic acid\b", "Dermatology",     "CHRONIC"),
    (r"\btacrolimus\b",     "Dermatology",     "CHRONIC"),  # ointment
    (r"\bpimecrolimus\b",   "Dermatology",     "CHRONIC"),
    (r"\bselamectin\b",     "Dermatology",     "SHORT"),

    # Immunology / allergy
    (r"\bcromolyn\b",       "Respiratory",     "CHRONIC"),
    (r"\bnedocromil\b",     "Respiratory",     "CHRONIC"),
    (r"\bcetirizine\b",     "Respiratory",     "PERIODIC"),
    (r"\bloratadine\b",     "Respiratory",     "PERIODIC"),
    (r"\bfexofenadine\b",   "Respiratory",     "PERIODIC"),
    (r"\blevocetirizine\b", "Respiratory",     "PERIODIC"),
    (r"\bdesloratadine\b",  "Respiratory",     "PERIODIC"),
    (r"\bdiphenhydramine\b","Respiratory",     "PERIODIC"),
    (r"\bclemastine\b",     "Respiratory",     "PERIODIC"),
    (r"\bpromethazine\b",   "Respiratory",     "PERIODIC"),
    (r"\bchlorpheniramine\b","Respiratory",    "PERIODIC"),

    # Renal
    (r"\bcalcium acetate\b","Metabolic",       "CHRONIC"),
    (r"\bsevelamer\b",      "Metabolic",       "CHRONIC"),
    (r"\blanthanum\b",      "Metabolic",       "CHRONIC"),
    (r"\bcincalcet\b",      "Metabolic",       "CHRONIC"),
    (r"\bcinacalcet\b",     "Metabolic",       "CHRONIC"),
    (r"\bpatiromer\b",      "Metabolic",       "CHRONIC"),
    (r"\bsodium zirconium\b","Metabolic",      "CHRONIC"),

    # Other specific ingredients
    (r"\bsucimer\b",        "Other",           "SHORT"),
    (r"\bdeferoxamine\b",   "Other",           "CHRONIC"),
    (r"\bdesferri",         "Other",           "CHRONIC"),
    (r"\bdeferasirox\b",    "Other",           "CHRONIC"),
    (r"\bpenicillamine\b",  "Autoimmune",      "CHRONIC"),
    (r"\btrientine\b",      "Other",           "CHRONIC"),   # Wilson's disease
    (r"\bzinc acetate\b",   "Other",           "CHRONIC"),   # Wilson's
    (r"\bglatiramer\b",     "Neurology",       "CHRONIC"),
    (r"\bmitoxantrone\b",   "Neurology",       "LONG-TERM"),
    (r"\bnatalizumab\b",    "Neurology",       "CHRONIC"),
    (r"\bocrelizumab\b",    "Neurology",       "CHRONIC"),
    (r"\bofatumumab\b",     "Neurology",       "CHRONIC"),

    # Laxatives / bowel prep (generally SHORT/PERIODIC)
    (r"\bpolyethylene glycol\b","GI",          "PERIODIC"),
    (r"\bsodium phosphate\b","GI",             "SHORT"),
    (r"\bsenna\b",          "GI",              "PERIODIC"),
    (r"\bbisacodyl\b",      "GI",              "PERIODIC"),
    (r"\bcastor oil\b",     "GI",              "SHORT"),
    (r"\bocritide\b",       "GI",              "CHRONIC"),  # octreotide

    # Antidotes / emergency (SHORT by nature)
    (r"\bflumazenil\b",     "Other",           "SHORT"),
    (r"\bnaloxone\b",       "Other",           "SHORT"),
    (r"\bprotamine\b",      "Other",           "SHORT"),
    (r"\bdigoxin immune\b", "Other",           "SHORT"),
    (r"\bdeferoxamine\b",   "Other",           "SHORT"),

    # Fertility / obstetric
    (r"\bclomiphene\b",     "Metabolic",       "SHORT"),
    (r"\bletrozole.*fertil","Metabolic",       "SHORT"),
    (r"\bganirelix\b",      "Metabolic",       "SHORT"),
    (r"\bcetrorelix\b",     "Metabolic",       "SHORT"),
    (r"\bmisoprostol\b",    "GI",              "SHORT"),
    (r"\boxytocin\b",       "Metabolic",       "SHORT"),
    (r"\bcarboprost\b",     "Metabolic",       "SHORT"),
    (r"\bdinoprostone\b",   "Metabolic",       "SHORT"),

    # ── ADHD / stimulants ───────────────────────────────────────────────
    (r"\bamphetamine\b",      "Psychiatric",   "CHRONIC"),
    (r"\blisdexamfetamine\b", "Psychiatric",   "CHRONIC"),
    (r"\bmethylphenidate\b",  "Psychiatric",   "CHRONIC"),
    (r"\bdexmethylphenidate\b","Psychiatric",  "CHRONIC"),
    (r"\bdextroamphetamine\b","Psychiatric",   "CHRONIC"),
    (r"\batomoxetine\b",      "Psychiatric",   "CHRONIC"),
    (r"\bguanfacine\b",       "Psychiatric",   "CHRONIC"),
    (r"\bclonidine\b",        "Psychiatric",   "CHRONIC"),  # also CV
    (r"\bviloxazine\b",       "Psychiatric",   "CHRONIC"),
    (r"\bmodafinil\b",        "Psychiatric",   "CHRONIC"),
    (r"\barmodafinil\b",      "Psychiatric",   "CHRONIC"),
    (r"\bsolriamfetol\b",     "Psychiatric",   "CHRONIC"),
    (r"\bpitolisant\b",       "Psychiatric",   "CHRONIC"),

    # ── Phenothiazine / conventional antipsychotics ──────────────────
    (r"\bchlorpromazine\b",   "Psychiatric",   "CHRONIC"),
    (r"\bfluphenazine\b",     "Psychiatric",   "CHRONIC"),
    (r"\bperphenazine\b",     "Psychiatric",   "CHRONIC"),
    (r"\bprochlorperazine\b", "GI",            "PERIODIC"),  # mostly antiemetic
    (r"\bthioridazine\b",     "Psychiatric",   "CHRONIC"),
    (r"\bthiothixene\b",      "Psychiatric",   "CHRONIC"),
    (r"\btrifluoperazine\b",  "Psychiatric",   "CHRONIC"),
    (r"\bloxapine\b",         "Psychiatric",   "CHRONIC"),
    (r"\bmolindone\b",        "Psychiatric",   "CHRONIC"),

    # ── Anticonvulsants not caught above ─────────────────────────────
    (r"\bdivalproex\b",       "Neurology",     "CHRONIC"),
    (r"\bbrivaracetam\b",     "Neurology",     "CHRONIC"),
    (r"\beslicarbazepine\b",  "Neurology",     "CHRONIC"),
    (r"\bclobazam\b",         "Neurology",     "CHRONIC"),
    (r"\bclobazam\b",         "Neurology",     "CHRONIC"),
    (r"\bfelbamate\b",        "Neurology",     "CHRONIC"),
    (r"\btiagabine\b",        "Neurology",     "CHRONIC"),
    (r"\bethosuximide\b",     "Neurology",     "CHRONIC"),
    (r"\bmethsuximide\b",     "Neurology",     "CHRONIC"),
    (r"\bprimidone\b",        "Neurology",     "CHRONIC"),
    (r"\bacetoazol\b",        "Neurology",     "CHRONIC"),  # acetazolamide (seizure)

    # ── Antidepressants not caught above ─────────────────────────────
    (r"\bsertraline\b",       "Psychiatric",   "CHRONIC"),
    (r"\bfluvoxamine\b",      "Psychiatric",   "CHRONIC"),
    (r"\bdesipramine\b",      "Psychiatric",   "CHRONIC"),
    (r"\bprotriptyline\b",    "Psychiatric",   "CHRONIC"),
    (r"\btrimipramine\b",     "Psychiatric",   "CHRONIC"),
    (r"\bmaprotiline\b",      "Psychiatric",   "CHRONIC"),
    (r"\bnefazodone\b",       "Psychiatric",   "CHRONIC"),
    (r"\bvilazodone\b",       "Psychiatric",   "CHRONIC"),
    (r"\bvortioxetine\b",     "Psychiatric",   "CHRONIC"),
    (r"\blevomilnacipran\b",  "Psychiatric",   "CHRONIC"),
    (r"\bmilnacipran\b",      "Psychiatric",   "CHRONIC"),

    # ── Antiarrhythmics not caught above ─────────────────────────────
    (r"\bpropafenone\b",      "Cardiovascular","CHRONIC"),
    (r"\bmexiletine\b",       "Cardiovascular","CHRONIC"),
    (r"\bdofetilide\b",       "Cardiovascular","CHRONIC"),
    (r"\bsotalol\b",          "Cardiovascular","CHRONIC"),
    (r"\bdisopyramide\b",     "Cardiovascular","CHRONIC"),
    (r"\bquinidine\b",        "Cardiovascular","CHRONIC"),
    (r"\bibutilide\b",        "Cardiovascular","SHORT"),
    (r"\badenosi",            "Cardiovascular","SHORT"),
    (r"\bmilrinone\b",        "Cardiovascular","SHORT"),
    (r"\bdopamine\b",         "Cardiovascular","SHORT"),
    (r"\bnorepinephrine\b",   "Cardiovascular","SHORT"),
    (r"\bdipyridamole\b",     "Cardiovascular","CHRONIC"),
    (r"\bmidodrine\b",        "Cardiovascular","CHRONIC"),
    (r"\bdroxidopa\b",        "Neurology",     "CHRONIC"),  # neurogenic OH
    (r"\bminoxidil\b",        "Cardiovascular","CHRONIC"),
    (r"\btolvaptan\b",        "Cardiovascular","CHRONIC"),  # vasopressin antagonist
    (r"\bconivaptan\b",       "Cardiovascular","SHORT"),
    (r"\bisradipine\b",       "Cardiovascular","CHRONIC"),
    (r"\bfelodipine\b",       "Cardiovascular","CHRONIC"),
    (r"\bnisoldipine\b",      "Cardiovascular","CHRONIC"),
    (r"\bnicardipine\b",      "Cardiovascular","CHRONIC"),
    (r"\bclevidipine\b",      "Cardiovascular","SHORT"),
    (r"\bnebivolol\b",        "Cardiovascular","CHRONIC"),
    (r"\bbisoprolol\b",       "Cardiovascular","CHRONIC"),
    (r"\bnadolol\b",          "Cardiovascular","CHRONIC"),
    (r"\bpindolol\b",         "Cardiovascular","CHRONIC"),
    (r"\bpenbutolol\b",       "Cardiovascular","CHRONIC"),
    (r"\btimolol\b",          "Cardiovascular","CHRONIC"),  # systemic
    (r"\bacebutolol\b",       "Cardiovascular","CHRONIC"),
    (r"\bocular",             "Ophthalmology", "CHRONIC"),

    # ── Carbonic anhydrase inhibitor (multiple uses) ────────────────
    (r"\bacetazolamide\b",    "Neurology",     "CHRONIC"),
    (r"\bmethazolamide\b",    "Ophthalmology", "CHRONIC"),

    # ── Octreotide / GI neuroendocrine ──────────────────────────────
    (r"\boctreotide\b",       "GI",            "CHRONIC"),
    (r"\blanreotide\b",       "GI",            "CHRONIC"),
    (r"\bpasireotide\b",      "Metabolic",     "CHRONIC"),  # Cushing's

    # ── GI motility / IBS ────────────────────────────────────────────
    (r"\bdicyclomine\b",      "GI",            "CHRONIC"),
    (r"\bprucalopride\b",     "GI",            "CHRONIC"),
    (r"\bgranisetron\b",      "GI",            "SHORT"),    # oncology antiemetic
    (r"\bpalonosetron\b",     "GI",            "SHORT"),
    (r"\bdolasetron\b",       "GI",            "SHORT"),

    # ── Dermatology steroids ─────────────────────────────────────────
    (r"\bclobetasol\b",       "Dermatology",   "CHRONIC"),
    (r"\bfluocinonide\b",     "Dermatology",   "CHRONIC"),
    (r"\bdesoximetasone\b",   "Dermatology",   "CHRONIC"),
    (r"\bfluocinolone\b",     "Dermatology",   "CHRONIC"),
    (r"\bbetamethasone\b",    "Dermatology",   "CHRONIC"),
    (r"\bbeclomethasone\b",   "Dermatology",   "CHRONIC"),  # also resp
    (r"\bhalcinonide\b",      "Dermatology",   "CHRONIC"),
    (r"\bhalobetasol\b",      "Dermatology",   "CHRONIC"),
    (r"\bamcinonide\b",       "Dermatology",   "CHRONIC"),
    (r"\bflurandrenolide\b",  "Dermatology",   "CHRONIC"),
    (r"\bfludroxycortide\b",  "Dermatology",   "CHRONIC"),
    (r"\bmometasone\b",       "Dermatology",   "CHRONIC"),  # also resp

    # ── Autoimmune / rare disease not caught above ────────────────────
    (r"\bdeflazacort\b",      "Autoimmune",    "CHRONIC"),  # systemic corticosteroid
    (r"\beltrombopag\b",      "Autoimmune",    "CHRONIC"),  # ITP
    (r"\bhetrombopag\b",      "Autoimmune",    "CHRONIC"),
    (r"\bromiplostim\b",      "Autoimmune",    "CHRONIC"),
    (r"\bavapritinib\b",      "Oncology",      "LONG-TERM"),
    (r"\bdapsone\b",          "Infectious",    "LONG-TERM"),  # leprosy/PCP
    (r"\bpentamidine\b",      "Infectious",    "SHORT"),
    (r"\bteriflunomide\b",    "Neurology",     "CHRONIC"),  # MS
    (r"\bdimethyl fumarate\b","Neurology",     "CHRONIC"),  # MS
    (r"\bsiponimod\b",        "Neurology",     "CHRONIC"),
    (r"\bozanimod\b",         "Neurology",     "CHRONIC"),
    (r"\bponesimod\b",        "Neurology",     "CHRONIC"),
    (r"\bfingolimod\b",       "Neurology",     "CHRONIC"),
    (r"\bcladribine\b",       "Neurology",     "LONG-TERM"), # MS

    # ── Oncology not caught above ─────────────────────────────────────
    (r"\bsunitinib\b",        "Oncology",      "LONG-TERM"),
    (r"\bsorafenib\b",        "Oncology",      "LONG-TERM"),
    (r"\bbortezomib\b",       "Oncology",      "LONG-TERM"),
    (r"\bcarfilzomib\b",      "Oncology",      "LONG-TERM"),
    (r"\bixazomib\b",         "Oncology",      "LONG-TERM"),
    (r"\bimatinib\b",         "Oncology",      "LONG-TERM"),
    (r"\bnilotinib\b",        "Oncology",      "LONG-TERM"),
    (r"\bponatinib\b",        "Oncology",      "LONG-TERM"),
    (r"\bbosutinib\b",        "Oncology",      "LONG-TERM"),
    (r"\basciminib\b",        "Oncology",      "LONG-TERM"),
    (r"\bselumetinib\b",      "Oncology",      "LONG-TERM"),
    (r"\btrametinib\b",       "Oncology",      "LONG-TERM"),
    (r"\bcobimetinib\b",      "Oncology",      "LONG-TERM"),
    (r"\bbinimetinib\b",      "Oncology",      "LONG-TERM"),
    (r"\bdabrafenib\b",       "Oncology",      "LONG-TERM"),
    (r"\bvemurafenib\b",      "Oncology",      "LONG-TERM"),
    (r"\bencorafenib\b",      "Oncology",      "LONG-TERM"),
    (r"\bpalbociclib\b",      "Oncology",      "LONG-TERM"),
    (r"\bribociclib\b",       "Oncology",      "LONG-TERM"),
    (r"\babemaciclib\b",      "Oncology",      "LONG-TERM"),
    (r"\berlotinib\b",        "Oncology",      "LONG-TERM"),
    (r"\bafatinib\b",         "Oncology",      "LONG-TERM"),
    (r"\bosimertinib\b",      "Oncology",      "LONG-TERM"),
    (r"\bdacomitinib\b",      "Oncology",      "LONG-TERM"),
    (r"\blapatinib\b",        "Oncology",      "LONG-TERM"),
    (r"\bneratinib\b",        "Oncology",      "LONG-TERM"),
    (r"\btucatinib\b",        "Oncology",      "LONG-TERM"),
    (r"\bcrizotinib\b",       "Oncology",      "LONG-TERM"),
    (r"\bceritinib\b",        "Oncology",      "LONG-TERM"),
    (r"\balectinib\b",        "Oncology",      "LONG-TERM"),
    (r"\blorlatinib\b",       "Oncology",      "LONG-TERM"),
    (r"\bbrigatinib\b",       "Oncology",      "LONG-TERM"),
    (r"\bcabozantinib\b",     "Oncology",      "LONG-TERM"),
    (r"\bvandetanib\b",       "Oncology",      "LONG-TERM"),
    (r"\blenvatinib\b",       "Oncology",      "LONG-TERM"),
    (r"\bazacitidine\b",      "Oncology",      "LONG-TERM"),
    (r"\bdecitabine\b",       "Oncology",      "LONG-TERM"),
    (r"\bcytarabine\b",       "Oncology",      "SHORT"),
    (r"\bnilutamide\b",       "Oncology",      "LONG-TERM"),
    (r"\bpomalidomide\b",     "Oncology",      "LONG-TERM"),
    (r"\bleucovorin\b",       "Oncology",      "SHORT"),    # rescue/adjunct
    (r"\blevoleucovorin\b",   "Oncology",      "SHORT"),

    # ── Pain / NSAIDs not caught above ───────────────────────────────
    (r"\betodolac\b",         "Pain",          "PERIODIC"),
    (r"\bnabumetone\b",       "Pain",          "PERIODIC"),
    (r"\boxaprozin\b",        "Pain",          "PERIODIC"),
    (r"\bpiroxicam\b",        "Pain",          "PERIODIC"),
    (r"\bflurbiprofen\b",     "Pain",          "PERIODIC"),
    (r"\bketoprofen\b",       "Pain",          "PERIODIC"),
    (r"\bsulindac\b",         "Pain",          "PERIODIC"),
    (r"\bdiflunisal\b",       "Pain",          "PERIODIC"),
    (r"\bmefenamic acid\b",   "Pain",          "SHORT"),
    (r"\bchlorzoxazone\b",    "Pain",          "SHORT"),

    # ── Ophthalmology — antihistamine eye drops ──────────────────────
    (r"\bolopatadine\b",      "Ophthalmology", "PERIODIC"),
    (r"\bketotifen\b",        "Ophthalmology", "PERIODIC"),
    (r"\bepinastine\b",       "Ophthalmology", "PERIODIC"),
    (r"\bbepotastine\b",      "Ophthalmology", "PERIODIC"),
    (r"\balecastekin\b",      "Ophthalmology", "PERIODIC"),

    # ── Urology / BPH ────────────────────────────────────────────────
    (r"\bsilodosin\b",        "Metabolic",     "CHRONIC"),
    (r"\balfuzosin\b",        "Metabolic",     "CHRONIC"),
    (r"\btamsulosin\b",       "Metabolic",     "CHRONIC"),
    (r"\bmirabegron\b",       "Neurology",     "CHRONIC"),

    # ── Respiratory ── antihistamines ────────────────────────────────
    (r"\bbenzonatate\b",      "Respiratory",   "SHORT"),
    (r"\bacetylcysteine\b",   "Respiratory",   "PERIODIC"),
    (r"\bguaifenesin\b",      "Respiratory",   "SHORT"),
    (r"\bdextromethorphan\b", "Respiratory",   "SHORT"),
    (r"\bcodeine\b",          "Respiratory",   "SHORT"),

    # ── Neuromuscular / anesthesia adjacents ────────────────────────
    (r"\brocuronium\b",       "Other",         "SHORT"),
    (r"\bcisatracurium\b",    "Other",         "SHORT"),
    (r"\batracurium\b",       "Other",         "SHORT"),
    (r"\bvecuronium\b",       "Other",         "SHORT"),
    (r"\bpancuronium\b",      "Other",         "SHORT"),
    (r"\bsuccinylcholine\b",  "Other",         "SHORT"),
    (r"\bmivacurium\b",       "Other",         "SHORT"),
    (r"\bdexmedetomidine\b",  "Other",         "SHORT"),
    (r"\bneostigmine\b",      "Other",         "SHORT"),
    (r"\bpyridostigmine\b",   "Neurology",     "CHRONIC"),  # MG
    (r"\bedrophonium\b",      "Neurology",     "SHORT"),
    (r"\bbenztropine\b",      "Neurology",     "CHRONIC"),  # EPS

    # ── Renal / electrolyte ──────────────────────────────────────────
    (r"\bpotassium citrate\b","Metabolic",     "CHRONIC"),
    (r"\bsodium bicarbonate\b","Metabolic",    "CHRONIC"),
    (r"\bammonium chloride\b","Metabolic",     "SHORT"),
    (r"\bcalcium citrate\b",  "Metabolic",     "CHRONIC"),
    (r"\bcalcium glubionate\b","Metabolic",    "CHRONIC"),
    (r"\bphosphate\b",        "Metabolic",     "CHRONIC"),

    # ── Smoking / addiction ──────────────────────────────────────────
    (r"\bphentermine\b",      "Metabolic",     "SHORT"),   # weight loss
    (r"\btopiramate.*weight\b","Metabolic",    "CHRONIC"),
    (r"\borlistat\b",         "Metabolic",     "CHRONIC"),
    (r"\bnaltrexone.*buprop\b","Metabolic",    "CHRONIC"),
    (r"\blorcaserin\b",       "Metabolic",     "CHRONIC"),

    # ── Miscellaneous identified ─────────────────────────────────────
    (r"\bdimethyl fumarate\b","Neurology",     "CHRONIC"),  # MS
    (r"\bcandesartan\b",      "Cardiovascular","CHRONIC"),
    (r"\beprosartan\b",       "Cardiovascular","CHRONIC"),
    (r"\birbesartan\b",       "Cardiovascular","CHRONIC"),
    (r"\btelmisartan\b",      "Cardiovascular","CHRONIC"),
    (r"\bazilsartan\b",       "Cardiovascular","CHRONIC"),
    (r"\bphenylephr",         "Cardiovascular","SHORT"),
    (r"\batropine\b",         "Cardiovascular","SHORT"),
    (r"\bamiodarone\b",       "Cardiovascular","CHRONIC"),
    (r"\bphenylephrine\b",    "Cardiovascular","SHORT"),

    # ── Pulmonary arterial hypertension (PAH) ───────────────────────
    (r"\btreprostinil\b",     "Cardiovascular","CHRONIC"),
    (r"\bambrisentan\b",      "Cardiovascular","CHRONIC"),
    (r"\bmacitentan\b",       "Cardiovascular","CHRONIC"),
    (r"\bbosentan\b",         "Cardiovascular","CHRONIC"),
    (r"\bselexipag\b",        "Cardiovascular","CHRONIC"),
    (r"\briociguat\b",        "Cardiovascular","CHRONIC"),
    (r"\bepoprostenol\b",     "Cardiovascular","CHRONIC"),
    (r"\biloprost\b",         "Cardiovascular","CHRONIC"),
    (r"\bberaprost\b",        "Cardiovascular","CHRONIC"),

    # ── Diagnostic / imaging (always SHORT) ──────────────────────────
    (r"\bfludeoxyglucose\b",  "Other",         "SHORT"),
    (r"\bgadobutrol\b",       "Other",         "SHORT"),
    (r"\bgadoterate\b",       "Other",         "SHORT"),
    (r"\bgadolinium\b",       "Other",         "SHORT"),
    (r"\bgadopentetate\b",    "Other",         "SHORT"),
    (r"\bgadofosveset\b",     "Other",         "SHORT"),
    (r"\bgadoxetate\b",       "Other",         "SHORT"),
    (r"\bgadobenate\b",       "Other",         "SHORT"),
    (r"\biodixanol\b",        "Other",         "SHORT"),
    (r"\biohexol\b",          "Other",         "SHORT"),
    (r"\biopamidol\b",        "Other",         "SHORT"),
    (r"\bregadenoson\b",      "Other",         "SHORT"),
    (r"\bamm?onia n.?13\b",   "Other",         "SHORT"),
    (r"\bsodium fluoride f\b","Other",         "SHORT"),
    (r"\bstrontium\b",        "Other",         "SHORT"),
    (r"\barsenic trioxide\b", "Oncology",      "LONG-TERM"),  # APL treatment
    (r"\bmethylene blue\b",   "Other",         "SHORT"),
    (r"\bindocyanine green\b","Other",         "SHORT"),

    # ── Hormonal contraceptives ──────────────────────────────────────
    (r"\blevonorgestrel\b",   "Metabolic",     "CHRONIC"),
    (r"\bnorethindrone\b",    "Metabolic",     "CHRONIC"),
    (r"\bnorgestimate\b",     "Metabolic",     "CHRONIC"),
    (r"\bdesogestrel\b",      "Metabolic",     "CHRONIC"),
    (r"\bdrospirenone\b",     "Metabolic",     "CHRONIC"),
    (r"\bgestodene\b",        "Metabolic",     "CHRONIC"),
    (r"\bnorgestrel\b",       "Metabolic",     "CHRONIC"),
    (r"\bmedroxyprogesterone\b","Metabolic",   "CHRONIC"),
    (r"\bnorgestimate\b",     "Metabolic",     "CHRONIC"),
    (r"\bethinyl estradiol\b","Metabolic",     "CHRONIC"),

    # ── Antifungal / antiparasitic not caught above ──────────────────
    (r"\bciclopirox\b",       "Infectious",    "SHORT"),
    (r"\bclotrimazole\b",     "Infectious",    "SHORT"),
    (r"\bmiconazole\b",       "Infectious",    "SHORT"),
    (r"\bketoconazole\b",     "Infectious",    "SHORT"),
    (r"\bvoriconazole\b",     "Infectious",    "SHORT"),
    (r"\bposaconazole\b",     "Infectious",    "SHORT"),
    (r"\bflucytosine\b",      "Infectious",    "SHORT"),
    (r"\bisavuconazole\b",    "Infectious",    "SHORT"),
    (r"\bitraconazole\b",     "Infectious",    "SHORT"),

    # ── Specific antivirals ──────────────────────────────────────────
    (r"\blamivudine\b",       "Infectious",    "CHRONIC"),   # HBV/HIV
    (r"\bentecavir\b",        "Infectious",    "CHRONIC"),   # HBV
    (r"\badefovir\b",         "Infectious",    "CHRONIC"),
    (r"\btelbivudine\b",      "Infectious",    "CHRONIC"),
    (r"\bganciclovir\b",      "Infectious",    "SHORT"),
    (r"\bfoscarnet\b",        "Infectious",    "SHORT"),
    (r"\bcidofovir\b",        "Infectious",    "SHORT"),
    (r"\bbrincidofovir\b",    "Infectious",    "SHORT"),
    (r"\brimantadine\b",      "Infectious",    "SHORT"),
    (r"\bamantadine\b",       "Infectious",    "SHORT"),

    # ── Antibiotics not caught above ─────────────────────────────────
    (r"\bgentamicin\b",       "Infectious",    "SHORT"),
    (r"\btobramycin\b",       "Infectious",    "SHORT"),
    (r"\bamikacin\b",         "Infectious",    "SHORT"),
    (r"\bneomycin\b",         "Infectious",    "SHORT"),
    (r"\bstreptomycin\b",     "Infectious",    "SHORT"),
    (r"\bspectinomycin\b",    "Infectious",    "SHORT"),
    (r"\bmeropenem\b",        "Infectious",    "SHORT"),
    (r"\bimipenem\b",         "Infectious",    "SHORT"),
    (r"\beropenem\b",         "Infectious",    "SHORT"),  # ertapenem, meropenem
    (r"\bdoripenem\b",        "Infectious",    "SHORT"),
    (r"\bcolistin\b",         "Infectious",    "SHORT"),
    (r"\bpolymyxin\b",        "Infectious",    "SHORT"),
    (r"\btigecycline\b",      "Infectious",    "SHORT"),
    (r"\boxymycin\b",         "Infectious",    "SHORT"),
    (r"\bdoxycycline\b",      "Infectious",    "SHORT"),
    (r"\bminocycline\b",      "Dermatology",   "CHRONIC"),  # acne uses are chronic
    (r"\bchloramphenicol\b",  "Infectious",    "SHORT"),
    (r"\bpenicillin\b",       "Infectious",    "SHORT"),
    (r"\bamoxicillin\b",      "Infectious",    "SHORT"),
    (r"\bampicillin\b",       "Infectious",    "SHORT"),
    (r"\bpiperacillin\b",     "Infectious",    "SHORT"),
    (r"\boxacillin\b",        "Infectious",    "SHORT"),
    (r"\bdicloxacillin\b",    "Infectious",    "SHORT"),
    (r"\bnafcillin\b",        "Infectious",    "SHORT"),
    (r"\bcloxacillin\b",      "Infectious",    "SHORT"),
    (r"\bbacampicillin\b",    "Infectious",    "SHORT"),
    (r"\btazobactam\b",       "Infectious",    "SHORT"),
    (r"\bclavulanate\b",      "Infectious",    "SHORT"),
    (r"\bsulbactam\b",        "Infectious",    "SHORT"),
    (r"\bavibactam\b",        "Infectious",    "SHORT"),
    (r"\brelebactam\b",       "Infectious",    "SHORT"),
    (r"\bvaborbactam\b",      "Infectious",    "SHORT"),
    (r"\bceftazidime\b",      "Infectious",    "SHORT"),
    (r"\bceftolozane\b",      "Infectious",    "SHORT"),

    # ── GI / antiemetics / motility ─────────────────────────────────
    (r"\bloperamide\b",       "GI",            "PERIODIC"),
    (r"\bbethanechol\b",      "GI",            "CHRONIC"),
    (r"\bpancrelipase\b",     "GI",            "CHRONIC"),  # duplicate OK
    (r"\bneomycin.*oral\b",   "GI",            "SHORT"),

    # ── Neurology ── vertigo / antiemetics ───────────────────────────
    (r"\bmeclizine\b",        "Neurology",     "PERIODIC"),
    (r"\bscopolamine\b",      "Neurology",     "PERIODIC"),
    (r"\bprochlorperazine\b", "GI",            "PERIODIC"),

    # ── CNS / rare neurology ─────────────────────────────────────────
    (r"\btetrabenazine\b",    "Neurology",     "CHRONIC"),  # Huntington's
    (r"\bvalbenazine\b",      "Neurology",     "CHRONIC"),
    (r"\bdeutetrabenazine\b", "Neurology",     "CHRONIC"),
    (r"\bnitisinone\b",       "Metabolic",     "CHRONIC"),  # HT1
    (r"\btrospium\b",         "Neurology",     "CHRONIC"),  # OAB
    (r"\bpyridostigmine\b",   "Neurology",     "CHRONIC"),  # MG

    # ── Dermatology not caught above ─────────────────────────────────
    (r"\bdesonide\b",         "Dermatology",   "CHRONIC"),
    (r"\badapalene\b",        "Dermatology",   "CHRONIC"),
    (r"\bbenzoy.*perox",      "Dermatology",   "CHRONIC"),
    (r"\bloteprednol\b",      "Ophthalmology", "SHORT"),    # ophthalmic steroid
    (r"\bbromfenac\b",        "Ophthalmology", "SHORT"),
    (r"\bazelastine\b",       "Respiratory",   "PERIODIC"),  # nasal antihistamine

    # ── Metabolic / nutritional ──────────────────────────────────────
    (r"\bphytonadione\b",     "Metabolic",     "SHORT"),   # Vitamin K1
    (r"\bvitamin k\b",        "Metabolic",     "SHORT"),
    (r"\bthiamine\b",         "Metabolic",     "CHRONIC"),  # B1 deficiency
    (r"\bribofl",             "Metabolic",     "CHRONIC"),  # riboflavin
    (r"\bniacinamide\b",      "Metabolic",     "CHRONIC"),
    (r"\bpyridoxine\b",       "Metabolic",     "CHRONIC"),  # B6
    (r"\bcyanocobalamin\b",   "Metabolic",     "CHRONIC"),  # B12 duplicate
    (r"\bsapropterin\b",      "Metabolic",     "CHRONIC"),  # PKU
    (r"\bnitisinone\b",       "Metabolic",     "CHRONIC"),  # HT1 duplicate
    (r"\bcalcium gluconate\b","Metabolic",     "CHRONIC"),
    (r"\bsodium polystyrene\b","Metabolic",    "CHRONIC"),  # hyperK
    (r"\bzinc\b",             "Metabolic",     "CHRONIC"),   # Wilson's / nutritional

    # ── Autoimmune / rheumatology ─────────────────────────────────────
    (r"\bapremilast\b",       "Autoimmune",    "CHRONIC"),  # PDE4 for psoriasis/PsA
    (r"\bdimethyl fumarate\b","Neurology",     "CHRONIC"),  # also in KEYWORD above

    # ── Cardiovascular urgent/emergency ─────────────────────────────
    (r"\beptifibatide\b",     "Cardiovascular","SHORT"),
    (r"\btirofiban\b",        "Cardiovascular","SHORT"),
    (r"\babciximab\b",        "Cardiovascular","SHORT"),
    (r"\bsodium nitroprus",   "Cardiovascular","SHORT"),
    (r"\bisoproterenol\b",    "Cardiovascular","SHORT"),
    (r"\bepinephrine\b",      "Cardiovascular","SHORT"),
    (r"\bneosynephrine\b",    "Cardiovascular","SHORT"),
    (r"\bvasopressin\b",      "Cardiovascular","SHORT"),
    (r"\bphenylephrine\b",    "Cardiovascular","SHORT"),  # decongestant/vasopressor

    # ── Sedation / hypnotics not caught above ─────────────────────────
    (r"\btemazepam\b",        "Psychiatric",   "PERIODIC"),
    (r"\boxazepam\b",         "Psychiatric",   "PERIODIC"),
    (r"\bclorazepate\b",      "Psychiatric",   "PERIODIC"),
    (r"\bchlordiazepoxide\b", "Psychiatric",   "PERIODIC"),
    (r"\bquazepam\b",         "Psychiatric",   "PERIODIC"),
    (r"\bflurazepam\b",       "Psychiatric",   "PERIODIC"),
    (r"\bnitrazepam\b",       "Psychiatric",   "PERIODIC"),
    (r"\bphenobarbital\b",    "Neurology",     "CHRONIC"),  # duplicate
    (r"\bbutabarbital\b",     "Psychiatric",   "PERIODIC"),
    (r"\bsecobarbital\b",     "Psychiatric",   "SHORT"),

    # ── Oncology cytotoxics/rare ─────────────────────────────────────
    (r"\bmelphalan\b",        "Oncology",      "SHORT"),
    (r"\bthiotepa\b",         "Oncology",      "SHORT"),
    (r"\bnelarabine\b",       "Oncology",      "LONG-TERM"),
    (r"\bclofarabine\b",      "Oncology",      "LONG-TERM"),
    (r"\bbendamustine\b",     "Oncology",      "LONG-TERM"),
    (r"\bfludarabine\b",      "Oncology",      "LONG-TERM"),
    (r"\bcladribine\b",       "Oncology",      "LONG-TERM"),  # also MS
    (r"\bpentostatin\b",      "Oncology",      "LONG-TERM"),
    (r"\bcytarabine\b",       "Oncology",      "SHORT"),
    (r"\bdecitabine\b",       "Oncology",      "LONG-TERM"),
    (r"\bazacitidine\b",      "Oncology",      "LONG-TERM"),
    (r"\bactinomycin\b",      "Oncology",      "SHORT"),
    (r"\bmitoxantrone\b",     "Oncology",      "LONG-TERM"),
    (r"\bdaunorubicin\b",     "Oncology",      "SHORT"),
    (r"\bidarubicin\b",       "Oncology",      "SHORT"),
    (r"\bpixantrone\b",       "Oncology",      "LONG-TERM"),
    (r"\bstreptozocin\b",     "Oncology",      "LONG-TERM"),
    (r"\bdacarbazine\b",      "Oncology",      "SHORT"),
    (r"\bprocarbazine\b",     "Oncology",      "LONG-TERM"),
    (r"\blomustine\b",        "Oncology",      "LONG-TERM"),
    (r"\bcarmustine\b",       "Oncology",      "SHORT"),
    (r"\bbusulfan\b",         "Oncology",      "SHORT"),
    (r"\bchlorambucil\b",     "Oncology",      "LONG-TERM"),
    (r"\bmechlorethamine\b",  "Oncology",      "SHORT"),
    (r"\bmitomycin\b",        "Oncology",      "SHORT"),

    # ── Pain / muscle relaxants ───────────────────────────────────────
    (r"\bmeperidine\b",       "Pain",          "SHORT"),
    (r"\bhydromorphone\b",    "Pain",          "CHRONIC"),  # duplicate
    (r"\bcaprofen\b",         "Pain",          "SHORT"),
    (r"\bcarisoprodol\b",     "Pain",          "SHORT"),
    (r"\borphenadrine\b",     "Pain",          "PERIODIC"),

    # ── Ephedrine / sympathomimetics ─────────────────────────────────
    (r"\bephedrine\b",        "Respiratory",   "SHORT"),
    (r"\bpseudoephedrine\b",  "Respiratory",   "SHORT"),
    (r"\bxylometazoline\b",   "Respiratory",   "SHORT"),
    (r"\boxymethazoline\b",   "Respiratory",   "SHORT"),

    # ── Vitamins / electrolytes ───────────────────────────────────────
    (r"\bsodium acetate\b",   "Other",         "SHORT"),
    (r"\bsterile water\b",    "Other",         "SHORT"),
    (r"\bdextrose\b",         "Other",         "SHORT"),
    (r"\bcyproheptadine\b",   "Psychiatric",   "PERIODIC"),  # antihistamine / appetite

    # ── Minerals as drugs ────────────────────────────────────────────
    (r"\bpotassium chloride\b","Metabolic",    "CHRONIC"),
    (r"\bmagnesium sulfate\b","Metabolic",     "SHORT"),
    (r"\bsodium chloride\b","Other",           "SHORT"),
    (r"\bdextrose\b",       "Other",           "SHORT"),
]


def classify(ingredient: str):
    raw  = ingredient.lower()
    name = _normalize(ingredient)   # salt-stripped version

    # Handle combination products first (semicolon-delimited)
    if ";" in raw:
        parts = [p.strip() for p in raw.split(";")]
        for part in parts:
            cat, dur = classify(part)
            if cat != "Other/Unclassified":
                return cat, dur
        return "Other/Unclassified", "OTHER"

    # Try suffix rules on normalized name (longest match wins — list is ordered)
    for pattern, cat, dur in SUFFIX_RULES:
        if re.search(pattern, name):
            return cat, dur

    # Fall back to keyword rules on the full raw lowercase name
    for pattern, cat, dur in KEYWORD_RULES:
        if re.search(pattern, raw):
            return cat, dur

    return "Other/Unclassified", "OTHER"


# ── Read input, classify, write output ──────────────────────────────────────
rows = []
with open(IN, encoding="utf-8") as fh:
    reader = csv.DictReader(fh)
    fieldnames = reader.fieldnames + ["Disease_Category", "Duration_Class"]
    for row in reader:
        cat, dur = classify(row["Ingredient"])
        row["Disease_Category"] = cat
        row["Duration_Class"]   = dur
        rows.append(row)

with open(OUT, "w", newline="", encoding="utf-8") as fh:
    writer = csv.DictWriter(fh, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

# ── Summary ──────────────────────────────────────────────────────────────────
from collections import Counter
dur_counts = Counter(r["Duration_Class"] for r in rows)
cat_counts = Counter(r["Disease_Category"] for r in rows)

print(f"\nTotal ingredients classified: {len(rows)}")
print("\nDuration class breakdown:")
for k in ["CHRONIC", "LONG-TERM", "PERIODIC", "SHORT", "OTHER"]:
    print(f"  {k:<15} {dur_counts[k]:>5}")

print("\nTop disease categories:")
for cat, n in cat_counts.most_common(20):
    print(f"  {cat:<30} {n:>5}")

unclass_pct = 100 * dur_counts["OTHER"] / len(rows)
print(f"\nUnclassified: {dur_counts['OTHER']} ({unclass_pct:.1f}%)")
print(f"Output → {OUT}")
