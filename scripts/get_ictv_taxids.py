#!/usr/bin/env python

import taxopy
from unidecode import unidecode


def normalize_str(s):
    return unidecode(s).strip().casefold()


# Read the ICTV taxa names
ictv_name_set = {
    name
    for line in open("ictv_taxonomy.tsv").readlines()[1:]
    for name in line.strip().split("\t")
    if name
}

# Create a dictionary associating virus names to ICTV species
virus_name_to_ictv_species = {}
ambiguous_names = {"uncultured caudovirales phage", "uncultured virus"}
with open("ictv_species_names.tsv") as fi:
    for line in fi:
        ictv_species, virus_names = line.strip().split("\t")
        for name in virus_names.split(";"):
            name = normalize_str(name)
            if name in virus_name_to_ictv_species:
                ambiguous_names.add(name)
            virus_name_to_ictv_species[name] = ictv_species
for name in ambiguous_names:
    virus_name_to_ictv_species.pop(name)

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
                elif normalize_str(j) in virus_name_to_ictv_species:
                    ictv_taxid = taxopy.taxid_from_name(
                        virus_name_to_ictv_species[normalize_str(j)], ictv_taxdb
                    )[0]
                    ncbi_to_ictv[ncbi_taxid] = ictv_taxid
                    break
        if ictv_taxid:
            ictv_taxon = taxopy.Taxon(ictv_taxid, ictv_taxdb)
            fo.write(f"{acc}\t{ictv_taxon.taxid}\n")
