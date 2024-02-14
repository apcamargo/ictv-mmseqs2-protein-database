# ictv-mmseqs2-protein-database

This repository contains instructions to generate a MMSeqs2 protein database with ICTV taxonomy. This database was not benchmarked. For taxonomic assignment of viral genomes you can try [geNomad](https://github.com/apcamargo/genomad).

## Dependencies:

- [`aria2`](https://github.com/aria2/aria2)
- [`ripgrep`](https://github.com/BurntSushi/ripgrep)
- [`csvtk`](https://github.com/shenwei356/csvtk)
- [`seqkit`](https://github.com/shenwei356/seqkit)
- [`taxonkit` (version 0.11.1)](https://github.com/shenwei356/taxonkit/releases/tag/v0.11.1)
- [`taxopy`](https://github.com/apcamargo/taxopy)
- [`mmseqs2`](https://github.com/soedinglab/MMseqs2)

## Instructions

First, download the latest VMR release from ICTV and convert it to a tabular file:

```bash
aria2c -x 4 -o ictv.xlsx "https://ictv.global/filebrowser/download/585"

# convert xlsx to tsv
csvtk xlsx2csv ictv.xlsx \
    | csvtk csv2tab \
    | sed 's/\xc2\xa0/ /g' \
    | csvtk replace -t -F -f "*" -p "^\s+|\s+$" \
    > ictv.tsv

# choose columns, and remove duplicates
csvtk cut -t -f "Realm,Subrealm,Kingdom,Subkingdom,Phylum,Subphylum,Class,Subclass,Order,Suborder,Family,Subfamily,Genus,Subgenus,Species" ictv.tsv \
    | csvtk uniq -t -f "Realm,Subrealm,Kingdom,Subkingdom,Phylum,Subphylum,Class,Subclass,Order,Suborder,Family,Subfamily,Genus,Subgenus,Species" \
    | csvtk del-header -t \
    > ictv.taxonomy.tsv
```

Create a file that will store all the ICTV taxa names:

```bash
csvtk cut -t -H -f 1,3,5,7,9,11,13,15 ictv.taxonomy.tsv \
    | sed 's/\t/\n/g' \
    | awk '!/^[[:blank:]]*$/' \
    | sort -u \
    > ictv.names.txt
```

Use `taxonkit create-taxdump` to create a custom taxdump for ICTV. Next, execute the `fix_taxdump.py` script, which will make the taxids sequential to make them compatible with MMSeqs2:

```bash
taxonkit create-taxdump -K 1 -P 3 -C 5 -O 7 -F 9 -G 11 -S 13 -T 15 \
    --rank-names "realm","kingdom","phylum","class","order","family","genus","species" \
    ictv.taxonomy.tsv --out-dir ictv-taxdump

./fix_taxdump.py
```

Download the NCBI taxdump and the `prot.accession2taxid` file. Then, filter `prot.accession2taxid` to keep only viral proteins:

```bash
# Download the NCBI taxdump
aria2c -x 4 "ftp://ftp.ncbi.nih.gov/pub/taxonomy/taxdump.tar.gz"
mkdir ncbi-taxdump
tar zxfv taxdump.tar.gz -C ncbi-taxdump
rm taxdump.tar.gz

# Download the protein → taxid association and filter for viruses
aria2c -x 4 "https://ftp.ncbi.nlm.nih.gov/pub/taxonomy/accession2taxid/prot.accession2taxid.FULL.gz"

gunzip prot.accession2taxid.FULL.gz

awk '{print $2}' prot.accession2taxid.FULL \
    | sort -u \
    | taxonkit --data-dir ncbi-taxdump lineage \
    | rg "\tViruses;" \
    | awk '{print $1}' \
    > virus_taxid.list

csvtk grep -t -f 2 -P virus_taxid.list prot.accession2taxid.FULL > virus.accession2taxid

rm prot.accession2taxid.FULL
```

Execute the `get_ictv_taxids.py` script to create a `accession2taxid` file with ICTV taxids.

```bash
# Find the ICTV-compliant proteins and write a new table with the ICTV taxids
./get_ictv_taxids.py
```

Download the proteins from NCBI and filter the FASTA file to keep only the proteins associated with ICTV viruses:

```bash
# Download and filter NR proteins
aria2c -x 4 "https://ftp.ncbi.nlm.nih.gov/blast/db/FASTA/nr.gz"

# Create a list containing the accessions of the proteins of ICTV viruses
cut -f 1 virus.accession2taxid.ictv > virus.accession.txt

# Filter the NR proteins to keep the proteins encoded by ICTV viruses
seqkit grep -j 4 -f virus.accession.txt nr.gz | seqkit seq -i -w 0 -o nr.virus.faa.gz

rm nr.gz
```

There will be proteins in `virus.accession2taxid.ictv` that are not in NR. So we will keep only the proteins that are present in the filtered NR FASTA file:

```bash
# Filter the NR virus taxid table
seqkit fx2tab -n -i nr.virus.faa.gz > nr.virus.list.txt
csvtk grep -t -H -f 1 -P nr.virus.list.txt virus.accession2taxid.ictv > nr.virus.accession2taxid.ictv
```

Using the filtered NR FASTA, the ICTV taxdump, and the `virus.accession2taxid.ictv` tabular file, we will create a MMSeqs2 protein database with taxonomy information:

```bash
# Create the MMSeqs2 database
mkdir virus_tax_db
mmseqs createdb --dbtype 1 nr.virus.faa.gz virus_tax_db/virus_tax_db
mmseqs createtaxdb virus_tax_db/virus_tax_db tmp --ncbi-tax-dump ictv-taxdump --tax-mapping-file nr.virus.accession2taxid.ictv
rm -rf tmp
```

Finally, to assign taxonomy to viral sequences in an input file (`input.fna`):

```bash
mmseqs easy-taxonomy input.fna virus_tax_db/virus_tax_db taxonomy_results tmp -e 1e-5 -s 6 --blacklist "" --tax-lineage 1
```
