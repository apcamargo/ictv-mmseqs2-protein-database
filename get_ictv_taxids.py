#!/usr/bin/env python

import taxopy

# Read the official ICTV names
with open("ictv.names.txt") as fin:
    ictv_name_set = {i.strip() for i in fin.readlines()}

# Create the Taxopy NCBI and ICTV databases
ncbi_taxdb = taxopy.TaxDb(
    nodes_dmp="ncbi-taxdump/nodes.dmp",
    names_dmp="ncbi-taxdump/names.dmp",
    merged_dmp="ncbi-taxdump/merged.dmp",
    keep_files=True,
)
ictv_taxdb = taxopy.TaxDb(
    nodes_dmp="ictv-taxdump/nodes.dmp",
    names_dmp="ictv-taxdump/names.dmp",
    keep_files=True,
)

# Replace non-ICTV taxids
with open("virus.accession2taxid") as fin, open(
    "virus.accession2taxid.ictv", "w"
) as fout:
    next(fin)
    for line in fin:
        acc, taxid = line.split("\t")
        ncbi_taxon = taxopy.Taxon(int(taxid), ncbi_taxdb)
        for j in ncbi_taxon.name_lineage:
            if j in ictv_name_set:
                ictv_taxid = taxopy.taxid_from_name(j, ictv_taxdb)
                ictv_taxon = taxopy.Taxon(ictv_taxid[0], ictv_taxdb)
                fout.write(f"{acc}\t{ictv_taxon.taxid}\n")
                break
