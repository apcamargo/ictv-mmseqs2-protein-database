#!/usr/bin/env python

from pathlib import Path

taxid_mapping_dict = {}
count = 1
with open(Path("ictv_taxdump").joinpath("names.dmp")) as fin:
    for line in fin:
        taxid = line.split("\t")[0]
        taxid_mapping_dict[taxid] = str(count)
        count += 1

with (
    open(Path("ictv_taxdump").joinpath("names.dmp")) as fin,
    open(Path("ictv_taxdump").joinpath("names.dmp.new"), "w") as fout,
):
    for line in fin:
        line = line.strip().split("\t")
        line[0] = taxid_mapping_dict[line[0]]
        line = "\t".join(line)
        fout.write(f"{line}\n")

with (
    open(Path("ictv_taxdump").joinpath("nodes.dmp")) as fin,
    open(Path("ictv_taxdump").joinpath("nodes.dmp.new"), "w") as fout,
):
    for line in fin:
        line = line.strip().split("\t")
        line[0] = taxid_mapping_dict[line[0]]
        line[2] = taxid_mapping_dict[line[2]]
        line = "\t".join(line)
        fout.write(f"{line}\n")

Path("ictv_taxdump").joinpath("names.dmp").unlink()
Path("ictv_taxdump").joinpath("nodes.dmp").unlink()
Path("ictv_taxdump").joinpath("nodes.dmp.new").rename("ictv_taxdump/nodes.dmp")
Path("ictv_taxdump").joinpath("names.dmp.new").rename("ictv_taxdump/names.dmp")
