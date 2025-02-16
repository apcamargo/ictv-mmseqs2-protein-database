#!/usr/bin/env python

import taxopy

# Read the official ICTV names
ictv_name_set = {
    name
    for line in open("ictv_taxonomy.tsv").readlines()[1:]
    for name in line.strip().split("\t")
    if name
}

# Create the Taxopy NCBI and ICTV databases
ncbi_taxdb = taxopy.TaxDb(
    nodes_dmp="ncbi_taxdump/nodes.dmp",
    names_dmp="ncbi_taxdump/names.dmp",
    merged_dmp="ncbi_taxdump/merged.dmp",
    keep_files=True,
)
ictv_taxdb = taxopy.TaxDb(
    nodes_dmp="ictv_taxdump/nodes.dmp",
    names_dmp="ictv_taxdump/names.dmp",
    keep_files=True,
)

# Replace non-ICTV taxids
ncbi_to_ictv = {}
with (
    open("accession2taxid.tsv") as fi,
    open("accession2taxid_ictv.tsv", "w") as fo,
):
    for line in fi:
        ictv_taxid = None
        acc, ncbi_taxid = line.split("\t")
        ncbi_taxid = int(ncbi_taxid)
        if ncbi_taxid in ncbi_to_ictv:
            ictv_taxid = ncbi_to_ictv[ncbi_taxid]
        else:
            ncbi_taxon = taxopy.Taxon(ncbi_taxid, ncbi_taxdb)
            for j in ncbi_taxon.name_lineage:
                if j in ictv_name_set:
                    ictv_taxid = taxopy.taxid_from_name(j, ictv_taxdb)[0]
                    ncbi_to_ictv[ncbi_taxid] = ictv_taxid
                    break
        if ictv_taxid:
            ictv_taxon = taxopy.Taxon(ictv_taxid, ictv_taxdb)
            fo.write(f"{acc}\t{ictv_taxon.taxid}\n")
