# ictv-mmseqs2-protein-database

This repository provides instructions and scripts for building an MMseqs2 database of virus proteins annotated with taxonomic data. The database can be used to assign sequences to virus taxa as defined by the International Committee on Taxonomy of Viruses (ICTV). A pre-built database is available for download from Zenodo: [doi:10.5281/zenodo.14740915](https://doi.org/10.5281/zenodo.14740915).

## Dependencies:

To generate the database on your own, ensure the following dependencies are installed on your system. This repository includes a `pixi.toml` file, which allows you to use [Pixi](https://pixi.sh/) to easily install all required software.

```bash
# Clone the repository
git clone git@github.com:apcamargo/ictv-mmseqs2-protein-database.git
cd ictv-mmseqs2-protein-database
# Install the dependencies and activate the environment
pixi shell
```

The following tools will be installed:

- [`csvtk`](https://github.com/shenwei356/csvtk)
- [`mmseqs2`](https://github.com/soedinglab/MMseqs2)
- [`seqkit`](https://github.com/shenwei356/seqkit)
- [`taxonkit`](https://github.com/shenwei356/taxonkit)
- [`taxopy`](https://github.com/apcamargo/taxopy)

## Building the database

### Step 1: Download and process ICTV taxonomy data

Download the ICTV's VMR MSL39 file and convert it to a tabular format:

```bash
# Download the data
curl -LJOs https://ictv.global/sites/default/files/VMR/VMR_MSL39.v4_20241106.xlsx
# Convert the xlsx file to a tsv file that contains taxonomic lineages, one per line
csvtk xlsx2csv VMR_MSL39.v4_20241106.xlsx \
    | csvtk csv2tab \
    | sed 's/\xc2\xa0/ /g' \
    | csvtk replace -t -F -f "*" -p "^\s+|\s+$" \
    | csvtk cut -t -f  "Realm,Subrealm,Kingdom,Subkingdom,Phylum,Subphylum,Class,Subclass,Order,Suborder,Family,Subfamily,Genus,Subgenus,Species" \
    | csvtk uniq -t -f "Realm,Subrealm,Kingdom,Subkingdom,Phylum,Subphylum,Class,Subclass,Order,Suborder,Family,Subfamily,Genus,Subgenus,Species" \
    | awk 'NR==1 {$0=tolower($0)} {print}' \
    > ictv_taxonomy.tsv
```

Create a file containing all unique ICTV taxon names:

```bash
csvtk cut -t -U -f 1,3,5,7,9,11,13,15 ictv_taxonomy.tsv \
    | sed 's/\t/\n/g' \
    | awk '!/^[[:blank:]]*$/' \
    | sort -u \
    > ictv_names.txt
```

### Step 2: Create a taxdump for the ICTV taxonomy

Generate a taxdump of the ICTV taxonomy using `taxonkit`, then run the `fix_taxdump.py` script to ensure taxids are sequential and compatible with MMseqs2:

```bash
taxonkit create-taxdump ictv_taxonomy.tsv --out-dir ictv_taxdump
python scripts/fix_taxdump.py
```

A pre-built ICTV taxdump is provided in this repository. Simply decompress the `ictv_taxdump.tar.gz` file.

### Step 3: Download and process NCBI NR data

Download the NCBI taxdump and filter the `prot.accession2taxid` file to retain only virus proteins:

```bash
# Download the NCBI taxdump
curl -LJOs ftp://ftp.ncbi.nih.gov/pub/taxonomy/taxdump.tar.gz
mkdir ncbi_taxdump
tar zxf taxdump.tar.gz -C ncbi_taxdump
rm taxdump.tar.gz
# Download the prot.accession2taxid file and filter only virus proteins
curl -LJs https://ftp.ncbi.nlm.nih.gov/pub/taxonomy/accession2taxid/prot.accession2taxid.FULL.gz \
    | gzip -dc \
    | taxonkit lineage -c -i 2 --data-dir ncbi_taxdump \
    | awk '$4 ~ /^Viruses/' \
    | awk -v OFS="\t" '{print $1, $3}' \
    > accession2taxid.tsv
```

### Step 4: Assign ICTV taxids to virus proteins

Run the `get_ictv_taxids.py `script to assign ICTV taxids to the NR virus proteins:

```bash
python scripts/get_ictv_taxids.py
```

Download and filter the NCBI NR database sequence, retaining only proteins that could be assigned to ICTV taxa:

```bash
# Download the NR database and retain only virus proteins
curl -LJs https://ftp.ncbi.nlm.nih.gov/blast/db/FASTA/nr.gz \
    | seqkit grep --quiet -j 4 -f <(cut -f 1 accession2taxid_ictv.tsv) \
    | seqkit seq -i -w 0 \
    | gzip \
    > ictv_nr.faa.gz
```

Remove proteins from `accession2taxid_ictv.tsv` that are not present in the filtered NR FASTA file:

```bash
# Create a tabular file associating the protein accessions with their taxids
awk 'NR==FNR {ids[$1]; next} $1 in ids' \
    <(seqkit fx2tab -ni ictv_nr.faa.gz) \
    accession2taxid_ictv.tsv \
    > accession2taxid_icvt_nr.tsv
```

### Step 5: Build the MMseqs2 database

Using the filtered NR FASTA, the ICTV taxdump, and the `accession2taxid_icvt_nr.tsv` file, build a MMseqs2 protein database containing ICTV taxonomy data:

```bash
mkdir ictv_nr_db
mmseqs createdb --dbtype 1 ictv_nr.faa.gz ictv_nr_db/ictv_nr_db
mmseqs createtaxdb ictv_nr_db/ictv_nr_db tmp --ncbi-tax-dump ictv_taxdump --tax-mapping-file accession2taxid_icvt_nr.tsv
rm -rf tmp
```

## Using the database for taxonomic assignment

The `ictv_nr_db` MMseqs2 database can be used to assign taxonomic information to virus genomes. For example, to assign taxonomy to a set of genomes stored in a `genomes.fna` FASTA file, use the following command:

```bash
mmseqs easy-taxonomy genomes.fna ictv_nr_db/ictv_nr_db result tmp --blacklist "" --tax-lineage 1
```
